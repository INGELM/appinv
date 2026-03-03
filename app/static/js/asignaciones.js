let tabla;
$(document).ready(function() {
    // Añadir token CSRF a todas las peticiones AJAX
    (function() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) {
            const csrfToken = meta.getAttribute('content');
            $.ajaxSetup({
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-CSRF-Token': csrfToken
                }
            });
        }
    })();
    // Manejar redirecciones a login u respuestas HTML en llamadas AJAX
    $(document).ajaxError(function(event, jqxhr, settings, thrownError) {
        try {
            const ct = jqxhr.getResponseHeader('Content-Type') || '';
            const body = jqxhr.responseText || '';
            if (ct.indexOf('text/html') !== -1 || (typeof body === 'string' && body.toLowerCase().includes('<!doctype html'))) {
                // Probablemente sesión expirada o redirect a login
                Swal.fire({
                    title: 'Sesión inválida',
                    text: 'La sesión ha expirado o no está autenticado. Será redirigido al login.',
                    icon: 'warning'
                }).then(() => { window.location = '/auth/login?next=' + encodeURIComponent(window.location.pathname); });
            }
        } catch (e) {
            console.error('ajaxError handler falló', e);
        }
    });
    // Cargar materiales disponibles
    // Inicializar Select2 para materiales con búsqueda dinámica
    function initSelectMaterial() {
        const el = $('#id_material');
        if (el.hasClass('select2-hidden-accessible')) {
            el.select2('destroy');
        }

        // Intentar detectar qué endpoint usar: autenticado primero, si falla usar public
        const attemptAuthUrl = '/inventario/api/materiales';
        const fallbackUrl = '/inventario/api/materiales_public';

        $.ajax({ url: attemptAuthUrl, method: 'GET', dataType: 'json' }).done(function(resp) {
            // si responde correctamente, inicializar select2 con endpoint autenticado
            const useUrl = (resp && resp.success) ? attemptAuthUrl : fallbackUrl;
            el.select2({
            theme: 'bootstrap4',
            placeholder: 'Seleccione un material',
            allowClear: true,
            width: '100%',
            dropdownParent: $('#modalSolicitar'),
            ajax: {
                url: useUrl,
                dataType: 'json',
                delay: 250,
                data: function(params) {
                    return { q: params.term };
                },
                processResults: function(resp) {
                    const results = (resp.data || []).map(function(m) {
                        return { id: m.id, text: m.material + ' (Disponible: ' + m.cantidad_disponible + ')', disponible: m.cantidad_disponible };
                    });
                    return { results: results };
                }
            },
            templateResult: function(item) { return item.loading ? item.text : item.text; },
            templateSelection: function(item) { return item.text || item.id; }
        });
            // limpiar selección
            el.val(null).trigger('change');
            if (useUrl === fallbackUrl) {
                console.warn('Se está utilizando el endpoint público de materiales (posible problema de sesión).');
            }
        }).fail(function() {
            // Si la llamada al autenticado falla, inicializar con fallback público
            el.select2({
                theme: 'bootstrap4',
                placeholder: 'Seleccione un material',
                allowClear: true,
                width: '100%',
                dropdownParent: $('#modalSolicitar'),
                ajax: {
                    url: fallbackUrl,
                    dataType: 'json',
                    delay: 250,
                    data: function(params) { return { q: params.term }; },
                    processResults: function(resp) {
                        const results = (resp.data || []).map(function(m) {
                            return { id: m.id, text: m.material + ' (Disponible: ' + m.cantidad_disponible + ')', disponible: m.cantidad_disponible };
                        });
                        return { results: results };
                    }
                },
                templateResult: function(item) { return item.loading ? item.text : item.text; },
                templateSelection: function(item) { return item.text || item.id; }
            });
            el.val(null).trigger('change');
            console.warn('Fallo al acceder a endpoint autenticado. Usando endpoint público para materiales.');
        });
    }

    // Cargar usuarios (para asignar a)
    function initSelectUsuarios() {
        if (!window.puedeAsignar) return;
        const el = $('#id_receptor');
        if (el.hasClass('select2-hidden-accessible')) {
            el.select2('destroy');
        }

        el.select2({
            theme: 'bootstrap4',
            placeholder: 'Seleccione un usuario',
            allowClear: true,
            width: '100%',
            dropdownParent: $('#modalSolicitar'),
            ajax: {
                url: '/auth/api/usuarios',
                dataType: 'json',
                delay: 250,
                data: function(params) {
                    return { q: params.term };
                },
                processResults: function(resp) {
                    const results = (resp.data || []).filter(u => u.activo).map(function(u) {
                        return { id: u.id, text: u.nombres + ' (' + u.rol + ')', nombres: u.nombres, usuario: u.usuario };
                    });
                    return { results: results };
                }
            },
            templateResult: function(item) { return item.loading ? item.text : item.text; },
            templateSelection: function(item) { return item.text || item.id; }
        });
        el.val(null).trigger('change');
        // verificar permisos y existencia de usuarios
        $.ajax({
            url: '/auth/api/usuarios',
            method: 'GET',
            dataType: 'json'
        }).done(function(resp) {
            if (!resp.success) {
                console.warn('No autorizado para listar usuarios o error:', resp.message || resp);
                // si no está autorizado, mostrar mensaje y desactivar select
                $('#id_receptor').prop('disabled', true);
            } else if (resp.data && resp.data.length === 0) {
                console.info('No hay usuarios para asignar');
            }
        }).fail(function(xhr) {
            console.error('Error al solicitar /auth/api/usuarios', xhr);
            Swal.fire('Error', 'No se pudieron cargar los usuarios. Compruebe permisos.', 'error');
            $('#id_receptor').prop('disabled', true);
        });
    }
    
    // Actualizar info de disponibilidad
    $('#id_material').on('change', function() {
        // obtener dato desde select2
        const d = $('#id_material').select2('data')[0];
        const disponible = d ? d.disponible : undefined;
        if (disponible !== undefined) {
            $('#disponible-info').text(`Cantidad disponible: ${disponible}`);
            $('#cantidad').attr('max', disponible);
        } else {
            $('#disponible-info').text('');
        }
    });
    
    // Inicializar DataTable
    tabla = $('#tabla-asignaciones').DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: '/asignaciones/api/listar',
            type: 'GET',
            data: function(d) {
                d.estatus = $('#filtro-estatus').val();
            }
        },
        columns: [
            { data: 'id' },
            { data: 'material' },
            { data: 'cantidad' },
            { data: 'receptor' },
            { data: 'asignador' },
            { 
                data: 'estatus',
                render: function(data) {
                    let clase = data === 'Pendiente' ? 'warning' : (data === 'Aprobado' ? 'success' : 'danger');
                    return `<span class="badge bg-${clase}">${data}</span>`;
                }
            },
            { data: 'fecha_solicitud' },
            { data: 'fecha_devolucion' },
            {
                data: null,
                render: function(data, type, row) {
                    let botones = '';
                    
                    if (row.estatus === 'Pendiente' && window.puedeAprobar) {
                        botones += `<button class="btn btn-sm btn-success btn-aprobar" data-id="${row.id}" title="Aprobar">
                            <i class="bi bi-check-circle"></i></button> `;
                    }
                    
                    
                    
                    if (row.estatus === 'Pendiente' && row.receptor === window.usuarioActual) {
                        botones += `<button class="btn btn-sm btn-danger btn-cancelar" data-id="${row.id}" title="Cancelar">
                            <i class="bi bi-x-circle"></i></button>`;
                    }

                    // Mostrar botón Devolver cuando esté aprobado y usuario tenga permiso
                    if (row.estatus === 'Aprobado' && window.puedeDevolver) {
                        botones += ` <button class="btn btn-sm btn-secondary btn-devolver" data-id="${row.id}" title="Devolver">
                            <i class="bi bi-arrow-counterclockwise"></i></button>`;
                    }
                    // Botón recibo / imprimir
                    botones += ` <button class="btn btn-sm btn-outline-primary btn-print" data-id="${row.id}" title="Recibo">
                        <i class="bi bi-printer"></i></button>`;
                    
                    return botones;
                }
            }
        ],
        language: {
            url: '/static/js/vendor/es-ES.json'
        }
    });
    // No inicializar Select2 fuera del modal para evitar problemas de z-index/render
    
    // Filtro por estatus
    $('#filtro-estatus').on('change', function() {
        tabla.ajax.reload();
    });
    
    // Abrir modal de solicitud
    $('#modalSolicitar').on('show.bs.modal', function() {
        initSelectMaterial();
        initSelectUsuarios();
    });
    
    // Enviar solicitud
    $('#form-solicitar').on('submit', function(e) {
        e.preventDefault();
        const data = {
            id_material: $('#id_material').val(),
            cantidad: $('#cantidad').val(),
            observaciones: $('#observaciones').val()
        };

        if (window.puedeAsignar) {
            const receptor = $('#id_receptor').val();
            if (!receptor) {
                Swal.fire('Error', 'Seleccione el usuario a quien asignar', 'error');
                return;
            }
            data.id_usuario_receptor = receptor;
        }
        
        $.ajax({
            url: '/asignaciones/api/solicitar',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function(response) {
                if (response.success) {
                    Swal.fire({
                        title: 'Éxito',
                        text: response.message,
                        icon: 'success',
                        timer: 2000,
                        showConfirmButton: false
                    });
                    $('#modalSolicitar').modal('hide');
                    $('#form-solicitar')[0].reset();
                    tabla.ajax.reload();
                } else {
                    Swal.fire('Error', response.message, 'error');
                }
            },
            error: function(xhr) {
                Swal.fire('Error', xhr.responseJSON?.message || 'Error al enviar solicitud', 'error');
            }
        });
    });
    
    // Aprobar/Rechazar
    $(document).on('click', '.btn-aprobar', function() {
        const id = $(this).data('id');
        $('#asignacion-id').val(id);
        $('#modalAprobar').modal('show');
    });
    
    $('#form-aprobar').on('submit', function(e) {
        e.preventDefault();
        
        const id = $('#asignacion-id').val();
        const data = {
            estatus: $('#estatus').val(),
            observaciones: $('#observaciones-aprobar').val()
        };
        
        $.ajax({
            url: `/asignaciones/api/aprobar/${id}`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function(response) {
                if (response.success) {
                    Swal.fire('Éxito', response.message, 'success');
                    $('#modalAprobar').modal('hide');
                    $('#form-aprobar')[0].reset();
                    tabla.ajax.reload();
                } else {
                    Swal.fire('Error', response.message, 'error');
                }
            },
            error: function(xhr) {
                Swal.fire('Error', xhr.responseJSON?.message || 'Error al procesar', 'error');
            }
        });
    });
    
    // Devolver material (reintegra al inventario)
    $(document).on('click', '.btn-devolver', function() {
        const id = $(this).data('id');

        Swal.fire({
            title: '¿Confirmar devolución?',
            text: 'La cantidad será reintegrada al inventario',
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'Sí, devolver',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                $.ajax({
                    url: `/asignaciones/api/devolver/${id}`,
                    type: 'POST',
                    success: function(response) {
                        if (response.success) {
                            Swal.fire('Éxito', response.message, 'success');
                            tabla.ajax.reload();
                        } else {
                            Swal.fire('Error', response.message, 'error');
                        }
                    }
                }).fail(function(xhr) {
                    let msg = xhr.responseJSON?.message || xhr.responseText || `HTTP ${xhr.status}`;
                    if (xhr.responseJSON) msg += '\n' + JSON.stringify(xhr.responseJSON);
                    console.error('devolver error', xhr);
                    Swal.fire('Error', msg, 'error');
                });
            }
        });
    });

    // Abrir recibo en nueva pestaña para imprimir/descargar
    $(document).on('click', '.btn-print', function() {
        const id = $(this).data('id');
        window.open(`/asignaciones/recibo/${id}`, '_blank');
    });
    
    // Cancelar solicitud
    $(document).on('click', '.btn-cancelar', function() {
        const id = $(this).data('id');
        
        Swal.fire({
            title: '¿Cancelar solicitud?',
            text: 'Esta acción no se puede deshacer',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Sí, cancelar',
            cancelButtonText: 'No'
        }).then((result) => {
            if (result.isConfirmed) {
                $.ajax({
                    url: `/asignaciones/api/cancelar/${id}`,
                    type: 'POST',
                    success: function(response) {
                        if (response.success) {
                            Swal.fire('Éxito', response.message, 'success');
                            tabla.ajax.reload();
                        } else {
                            Swal.fire('Error', response.message, 'error');
                        }
                    }
                });
            }
        });
    });
});
