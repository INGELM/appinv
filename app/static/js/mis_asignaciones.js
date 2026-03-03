let tabla_mis_asignaciones;

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

    tabla_mis_asignaciones = $('#tabla-mis-asignaciones').DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: '/asignaciones/api/mis-asignaciones',
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
            { data: 'asignador' },
            { data: 'fecha_aprobacion' },
            { data: 'observaciones' }
        ],
        language: {
            url: '/static/js/vendor/es-ES.json'
        }
    });
});
