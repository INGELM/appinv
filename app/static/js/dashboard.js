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
    $('#tabla-mis-materiales').DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: '/dashboard/api/mis-materiales',
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
            { data: 'tipo' },
            { data: 'cantidad' },
            { data: 'fecha_asignacion' },
            { data: 'asignado_por' }
        ],
        language: {
            url: '/static/js/vendor/es-ES.json'
        }
    });
});
