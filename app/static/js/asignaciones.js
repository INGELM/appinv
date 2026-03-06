let tabla;
const seleccion = new Set();
let receptorSeleccionado = null;

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

    function limpiarSeleccion() {
        seleccion.clear();
        receptorSeleccionado = null;
        actualizarBotonSeleccion();
    }

    function actualizarBotonSeleccion() {
        const btn = $('#btn-print-seleccion');
        if (!btn.length) return;
        btn.prop('disabled', seleccion.size === 0);
    }

    function sincronizarCheckboxes() {
        $('#tabla-asignaciones input.select-asignacion').each(function() {
            const id = $(this).data('id');
            $(this).prop('checked', seleccion.has(id));
        });
    }

    // Manejar redirecciones a login u respuestas HTML en llamadas AJAX
    $(document).ajaxError(function(event, jqxhr) {
        try {
            const ct = jqxhr.getResponseHeader('Content-Type') || '';
            const body = jqxhr.responseText || '';
            if (ct.indexOf('text/html') !== -1 || (typeof body === 'string' && body.toLowerCase().includes('<!doctype html'))) {
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
    function initSelectMaterial() {
        const el = $('#id_material');
        if (el.hasClass('select2-hidden-accessible')) {
            el.select2('destroy');
        }

        const attemptAuthUrl = '/inventario/api/materiales';
        const fallbackUrl = '/inventario/api/materiales_public';

        $.ajax({ url: attemptAuthUrl, method: 'GET', dataType: 'json' }).done(function(resp) {
            const useUrl = (resp && resp.success) ? attemptAuthUrl : fallbackUrl;
            el.select2({
                // theme: 'bootstrap4',
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
            el.val(null).trigger('change');
            if (useUrl === fallbackUrl) {
                console.warn('Se está utilizando el endpoint público de materiales (posible problema de sesión).');
            }
        }).fail(function() {
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
            // theme: 'bootstrap5',
            placeholder: 'Seleccione uno o más usuarios',
            allowClear: true,
            multiple: true,
            tags: true,
            tokenSeparators: [','],
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
                        return { id: u.id, text: u.nombres + ' (' + u.rol + ')' };
                    });
                    return { results: results };
                }
            }
        });
    }
    
    // Actualizar info de disponibilidad
    $('#id_material').on('change', function() {
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
            {
                data: null,
                orderable: false,
                searchable: false,
                render: function(data, type, row) {
                    return `<input type="checkbox" class="form-check-input select-asignacion" data-id="${row.id}" data-receptor-id="${row.receptor_id}" data-estatus="${row.estatus}">`;
                }
            },
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

                    if (row.estatus === 'Aprobado' && window.puedeDevolver) {
                        botones += ` <button class="btn btn-sm btn-secondary btn-devolver" data-id="${row.id}" title="Devolver">
                            <i class="bi bi-arrow-counterclockwise"></i></button>`;
                    }
                    botones += ` <button class="btn btn-sm btn-outline-primary btn-print" data-id="${row.id}" data-estatus="${row.estatus}" title="Recibo">
                        <i class="bi bi-printer"></i></button>`;
                    
                    return botones;
                }
            }
        ],
        language: {
            url: '/static/js/vendor/es-ES.json'
        }
    });
    tabla.on('draw', sincronizarCheckboxes);
    
    // Filtro por estatus
    $('#filtro-estatus').on('change', function() {
        limpiarSeleccion();
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
            const receptores = $('#id_receptor').val() || [];
            if (receptores.length === 0) {
                Swal.fire('Error', 'Seleccione al menos un usuario o ingrese un nombre externo', 'error');
                return;
            }
            // Separar ids numéricos de nombres externos (tags)
            const ids = receptores.filter(r => /^\d+$/.test(r)).map(Number);
            const externos = receptores.filter(r => !/^\d+$/.test(r)).map(s => s.trim()).filter(Boolean);
            data.id_usuarios_receptores = ids;
            if (externos.length) data.receptores_externos = externos;
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
                    });
                    $('#modalSolicitar').modal('hide');
                } else {
                    Swal.fire('Error', response.message, 'error');
                }
            },
            error: function() {
                Swal.fire('Error', 'Ocurrió un error al enviar la solicitud', 'error');
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
                    limpiarSeleccion();
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
                            limpiarSeleccion();
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

    // Abrir recibo/devolución en nueva pestaña para imprimir/descargar
    $(document).on('click', '.btn-print', function() {
        const id = $(this).data('id');
        const estatus = $(this).data('estatus');
        if (estatus === 'Reintegrado') {
            window.open(`/asignaciones/devolucion/${id}`, '_blank');
        } else {
            window.open(`/asignaciones/recibo/${id}`, '_blank');
        }
    });
    
    // Selección de filas para recibo múltiple
    $(document).on('change', '.select-asignacion', function() {
        const id = $(this).data('id');
        const receptorIdRaw = String($(this).data('receptor-id'));
        const estatus = $(this).data('estatus');

        if (this.checked) {
            if (estatus !== 'Aprobado') {
                this.checked = false;
                Swal.fire('No permitido', 'Solo se pueden imprimir asignaciones aprobadas.', 'info');
                return;
            }
            if (receptorSeleccionado !== null && receptorSeleccionado !== receptorIdRaw) {
                this.checked = false;
                Swal.fire('Seleccione mismo usuario', 'Solo se pueden agrupar asignaciones del mismo receptor.', 'warning');
                return;
            }
            seleccion.add(id);
            receptorSeleccionado = receptorSeleccionado !== null ? receptorSeleccionado : receptorIdRaw;
        } else {
            seleccion.delete(id);
            if (seleccion.size === 0) {
                receptorSeleccionado = null;
            }
        }
        actualizarBotonSeleccion();
    });

    // Imprimir recibo múltiple
    $('#btn-print-seleccion').on('click', function() {
        if (seleccion.size === 0) return;
        const ids = Array.from(seleccion).join(',');
        window.open(`/asignaciones/recibo/lote?ids=${ids}`, '_blank');
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
                            limpiarSeleccion();
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
