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
    const tabla = $('#tabla-usuarios').DataTable({
        ajax: {
            url: '/auth/api/usuarios',
            type: 'GET',
            dataSrc: function(json) {
                if (!json.success) {
                    Swal.fire('Error', json.message || 'No autorizado', 'error');
                    return [];
                }
                return json.data;
            },
            error: function(xhr) {
                Swal.fire('Error', `HTTP ${xhr.status}: ${xhr.statusText}`, 'error');
            }
        },
        columns: [
            { data: 'id' },
            { data: 'nombres' },
            { data: 'usuario' },
            { data: 'rol' },
            { data: 'activo', render: function(data) { return data ? '<span class="badge bg-success">Activo</span>' : '<span class="badge bg-secondary">Inactivo</span>'; } },
            { data: 'fecha_creacion' },
            { data: null, render: function(data, type, row) {
                const btn = row.activo ?
                    `<button class="btn btn-sm btn-warning btn-toggle" data-id="${row.id}" data-activo="0">Desactivar</button>` :
                    `<button class="btn btn-sm btn-success btn-toggle" data-id="${row.id}" data-activo="1">Activar</button>`;
                return btn;
            } }
        ],
        language: { url: '/static/js/vendor/es-ES.json' }
    });

    // Manejar activar/desactivar
    $('#tabla-usuarios').on('click', '.btn-toggle', function() {
        const id = $(this).data('id');
        const activo = $(this).data('activo');
        $.ajax({
            url: `/auth/api/usuarios/${id}/activar`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ activo: activo }),
            success: function(response) {
                if (response.success) {
                    Swal.fire('Éxito', response.message, 'success');
                    tabla.ajax.reload();
                } else {
                    Swal.fire('Error', response.message, 'error');
                }
            },
            error: function(xhr) {
                Swal.fire('Error', xhr.responseJSON?.message || `HTTP ${xhr.status}`, 'error');
            }
        });
    });

    // Crear nuevo usuario desde modal
    $('#form-nuevo-usuario').on('submit', function(e) {
        e.preventDefault();

        const payload = {
            nombres: $('#nu_nombres').val(),
            usuario: $('#nu_usuario').val(),
            password: $('#nu_password').val(),
            rol: $('#nu_rol').val(),
            activo: $('#nu_activo').is(':checked')
        };

        $.ajax({
            url: '/auth/api/usuarios/crear',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(payload),
            success: function(response) {
                if (response.success) {
                    Swal.fire('Éxito', response.message, 'success');
                    $('#modalNuevoUsuario').modal('hide');
                    $('#form-nuevo-usuario')[0].reset();
                    tabla.ajax.reload();
                } else {
                    Swal.fire('Error', response.message, 'error');
                }
            },
            error: function(xhr) {
                Swal.fire('Error', xhr.responseJSON?.message || `HTTP ${xhr.status}`, 'error');
            }
        });
    });
});
