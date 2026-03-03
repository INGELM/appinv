let tabla_mis_asignaciones;
const seleccionMisAsignaciones = new Set();

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

    function actualizarBoton() {
        $('#btn-print-mias').prop('disabled', seleccionMisAsignaciones.size === 0);
    }

    function sincronizarChecks() {
        $('#tabla-mis-asignaciones input.select-asignacion').each(function() {
            const id = $(this).data('id');
            $(this).prop('checked', seleccionMisAsignaciones.has(id));
        });
    }

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
            {
                data: null,
                orderable: false,
                searchable: false,
                render: function(data, type, row) {
                    return `<input type="checkbox" class="form-check-input select-asignacion" data-id="${row.id}">`;
                }
            },
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
    tabla_mis_asignaciones.on('draw', sincronizarChecks);

    $(document).on('change', '#tabla-mis-asignaciones .select-asignacion', function() {
        const id = $(this).data('id');
        if (this.checked) {
            seleccionMisAsignaciones.add(id);
        } else {
            seleccionMisAsignaciones.delete(id);
        }
        actualizarBoton();
    });

    $('#btn-print-mias').on('click', function() {
        if (seleccionMisAsignaciones.size === 0) return;
        const ids = Array.from(seleccionMisAsignaciones).join(',');
        window.open(`/asignaciones/recibo/lote?ids=${ids}`, '_blank');
    });
});
