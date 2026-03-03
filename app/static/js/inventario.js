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
    tabla = $('#tabla-inventario').DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: '/inventario/api/listar',
            type: 'GET'
        },
        columns: [
            { data: 'id' },
            { data: 'fecha_ingreso' },
            { data: 'num_proceso' },
            { data: 'proveedor' },
            { data: 'material' },
            { data: 'descripcion' },
            { data: 'cantidad' },
            { data: 'cantidad_disponible' },
            { data: 'tipo' },
            { 
                data: null,
                render: function(data, type, row) {
                    let botones = `<button class="btn btn-sm btn-warning btn-editar" data-id="${row.id}" title="Editar">
                        <i class="bi bi-pencil"></i></button> `;
                    
                    // Botón para asignar desde la tabla (redirige a la página de asignaciones
                    // y abre el modal con el material preseleccionado)
                    if (window.puedeAsignar || window.puedeSolicitar) {
                        botones += `<button class="btn btn-sm btn-success btn-asignar" data-id="${row.id}" data-material="${(row.material||'').replace(/"/g,'&quot;')}" title="Asignar">
                            <i class="bi bi-box-arrow-in-right"></i></button> `;
                    }

                    if (row.cantidad_asignada === 0) {
                        botones += `<button class="btn btn-sm btn-danger btn-eliminar" data-id="${row.id}" title="Eliminar">
                        <i class="bi bi-trash"></i></button>`;
                    }
                    return botones;
                }
            }
        ],
        language: {
            url: '/static/js/vendor/es-ES.json'
        }
    });
    
    // Nuevo material
    $('#form-material').on('submit', function(e) {
        e.preventDefault();
        
        const id = $('#material-id').val();
        const data = {
            material: $('#material').val(),
            descripcion: $('#descripcion').val(),
            cantidad: $('#cantidad').val(),
            tipo: $('#tipo').val(),
            num_proceso: $('#num_proceso').val(),
            proveedor: $('#proveedor').val(),
            observaciones: $('#observaciones').val()
        };
        
        let url = '/inventario/api/crear';
        let method = 'POST';
        
        if (id) {
            url = `/inventario/api/editar/${id}`;
            data.id = id;
        }
        
        $.ajax({
            url: url,
            type: method,
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function(response) {
                if (response.success) {
                    Swal.fire('Éxito', response.message, 'success');
                    $('#modalMaterial').modal('hide');
                    $('#form-material')[0].reset();
                    $('#material-id').val('');
                    tabla.ajax.reload();
                } else {
                    Swal.fire('Error', response.message, 'error');
                }
            },
            error: function(xhr) {
                Swal.fire('Error', xhr.responseJSON?.message || 'Error al guardar', 'error');
            }
        });
    });
    
    // Editar material
    $(document).on('click', '.btn-editar', function() {
        const id = $(this).data('id');
        
        $.get(`/inventario/api/obtener/${id}`, function(response) {
            if (response.success) {
                const data = response.data;
                $('#material-id').val(data.id);
                $('#material').val(data.material);
                $('#descripcion').val(data.descripcion || '');
                $('#cantidad').val(data.cantidad);
                $('#tipo').val(data.tipo);
                $('#num_proceso').val(data.num_proceso);
                $('#proveedor').val(data.proveedor);
                $('#observaciones').val(data.observaciones);
                
                $('#modalMaterialLabel').text('Editar Material');
                $('#modalMaterial').modal('show');
            }
        });
    });
    
    // Eliminar material
    $(document).on('click', '.btn-eliminar', function() {
        const id = $(this).data('id');
        
        Swal.fire({
            title: '¿Está seguro?',
            text: 'Esta acción no se puede deshacer',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Sí, eliminar',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                $.ajax({
                    url: `/inventario/api/eliminar/${id}`,
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

    // Click en botón "Asignar" dentro de la tabla -> redirigir a /asignaciones con parámetro
    $(document).on('click', '.btn-asignar', function() {
        const id = $(this).data('id');
        // Abrir la página de asignaciones y pasar material_id para preseleccionar
        window.location = `/asignaciones/?material_id=${id}`;
    });
    
    // Limpiar modal al cerrar
    $('#modalMaterial').on('hidden.bs.modal', function() {
        $('#form-material')[0].reset();
        $('#material-id').val('');
        $('#modalMaterialLabel').text('Nuevo Material');
    });
});
