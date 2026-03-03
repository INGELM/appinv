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
    // Cargar materiales disponibles
    function cargarMateriales() {
        $.get('/inventario/api/materiales', function(response) {
            if (response.success) {
                const select = $('#id_material');
                select.empty();
                select.append('<option value="">Seleccione un material</option>');
                response.data.forEach(function(m) {
                    select.append(`<option value="${m.id}" data-disponible="${m.cantidad_disponible}">${m.material} (Disponible: ${m.cantidad_disponible})</option>`);
                });
            }
        });
    }

    // Cargar usuarios (para asignar a)
    function cargarUsuarios() {
        if (!window.puedeAsignar) return;
        $.get('/auth/api/usuarios', function(response) {
            if (response.success) {
                const select = $('#id_receptor');
                select.empty();
                select.append('<option value="">Seleccione un usuario</option>');
                response.data.forEach(function(u) {
                    if (u.activo) {
                        select.append(`<option value="${u.id}">${u.nombres} (${u.rol})</option>`);
                    }
                });
            }
        });
    }
    
    // Actualizar info de disponibilidad
    $('#id_material').on('change', function() {
        const option = $(this).find('option:selected');
        const disponible = option.data('disponible');
        if (disponible !== undefined) {
            $('#disponible-info').text(`Cantidad disponible: ${disponible}`);
            $('#cantidad').attr('max', disponible);
        } else {
            $('#disponible-info').text('');
        }
    });
    
    // Inicializar DataTable
    tabla = $('#tabla-mis-solicitudes').DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: '/asignaciones/api/mis-solicitudes',
            type: 'GET',
            error: function(xhr, textStatus, errorThrown) {
                const msg = `HTTP ${xhr.status}: ${xhr.responseJSON?.message || xhr.statusText || errorThrown || textStatus}`;
                console.error('DataTables AJAX error:', xhr, textStatus, errorThrown);
                Swal.fire('Error Ajax', msg, 'error');
            }
        },
        columns: [
            { data: 'id' },
            { data: 'material' },
            { data: 'cantidad' },
            { 
                data: 'estatus',
                render: function(data) {
                    let clase = data === 'Pendiente' ? 'warning' : (data === 'Aprobado' ? 'success' : 'danger');
                    return `<span class="badge bg-${clase}">${data}</span>`;
                }
            },
            { data: 'fecha_solicitud' },
            { data: 'fecha_aprobacion' },
            { data: 'fecha_devolucion' },
            { data: 'observaciones' }
        ],
        language: {
            url: '/static/js/vendor/es-ES.json'
        }
    });
    
    // Abrir modal de solicitud
    $('#modalSolicitar').on('show.bs.modal', function() {
        cargarMateriales();
        cargarUsuarios();
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
                    Swal.fire('Éxito', response.message, 'success');
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
});
