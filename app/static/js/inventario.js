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
        responsive: true,
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
                data: 'foto1',
                render: function(data) {
                    return data ? `<img src="/static/files/${data}" alt="Foto 1" class="img-thumbnail img-open img-clickable table-avatar" data-filename="${data}">` : '-';
                }
            },
            { 
                data: 'foto2',
                render: function(data) {
                    return data ? `<img src="/static/files/${data}" alt="Foto 2" class="img-thumbnail img-open img-clickable table-avatar" data-filename="${data}">` : '-';
                }
            },
            { data: 'asignado_a' }
        ],
        columnDefs: [
            { targets: [0,6,7,9,10,11], className: 'text-center' },
            { targets: [1], width: '110px', responsivePriority: 2 },
            { targets: [11], width: '180px', responsivePriority: 4 },
            { targets: [0], responsivePriority: 1 },
            { targets: [4], responsivePriority: 3 },
            { targets: [6], responsivePriority: 5 },
            { targets: [7], responsivePriority: 6 },
            { targets: [9], responsivePriority: 7 },
            { targets: [10], responsivePriority: 8 }
        ],
        language: {
            url: '/static/js/vendor/es-ES.json'
        }
    });
    
    // Nuevo material
    $('#form-material').on('submit', function(e) {
        e.preventDefault();
        
        const id = $('#material-id').val();
        const formData = new FormData(this);

        let url = '/inventario/api/crear';
        let method = 'POST';
        
        if (id) {
            url = `/inventario/api/editar/${id}`;
            formData.append('id', id);
        }
        
        $.ajax({
            url: url,
            type: method,
            processData: false,
            contentType: false,
            data: formData,
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
    
    // Función para abrir modal de edición por id
    function openEditModal(id) {
        if (!id) return;
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
                // Mostrar vistas previas de fotos si existen
                if (data.foto1) {
                    $('#img-foto1').attr('src', `/static/files/${data.foto1}`);
                    $('#preview-foto1-container').show();
                    $('#delete-foto1').val('');
                } else {
                    $('#img-foto1').attr('src', '');
                    $('#preview-foto1-container').hide();
                    $('#delete-foto1').val('');
                }
                if (data.foto2) {
                    $('#img-foto2').attr('src', `/static/files/${data.foto2}`);
                    $('#preview-foto2-container').show();
                    $('#delete-foto2').val('');
                } else {
                    $('#img-foto2').attr('src', '');
                    $('#preview-foto2-container').hide();
                    $('#delete-foto2').val('');
                }

                $('#modalMaterialLabel').text('Editar Material');
                $('#modalMaterial').modal('show');
            }
        });
    }

    // Manejar clic en botón eliminar foto dentro del modal (delegación)
    $(document).on('click', '.btn-eliminar-foto', function() {
        const foto = $(this).data('foto');
        if (foto === 'foto1') {
            $('#img-foto1').attr('src', '');
            $('#preview-foto1-container').hide();
            $('#delete-foto1').val('1');
            // También limpiar input file si el usuario cargó uno
            $('#foto1').val('');
        } else if (foto === 'foto2') {
            $('#img-foto2').attr('src', '');
            $('#preview-foto2-container').hide();
            $('#delete-foto2').val('1');
            $('#foto2').val('');
        }
    });
    
    // Función para eliminar material con confirmación
    function deleteMaterial(id) {
        if (!id) return;
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
    }

    // Función para redirigir a asignaciones
    function assignMaterial(id) {
        if (!id) return;
        window.location = `/asignaciones/?material_id=${id}`;
    }
    
    // Limpiar modal al cerrar
    $('#modalMaterial').on('hidden.bs.modal', function() {
        $('#form-material')[0].reset();
        $('#material-id').val('');
        $('#modalMaterialLabel').text('Nuevo Material');
        // Reset previews y flags de eliminación
        $('#img-foto1').attr('src', '');
        $('#img-foto2').attr('src', '');
        $('#preview-foto1-container').hide();
        $('#preview-foto2-container').hide();
        $('#delete-foto1').val('');
        $('#delete-foto2').val('');
    });

    // Selección de filas (única): click selecciona y deselecciona otras
    let selectedRowId = null;
    $('#tabla-inventario tbody').on('click', 'tr', function(e) {
        const row = tabla.row(this).data();
        if (!row) return;
        // Si ya está seleccionada, deseleccionar
        if ($(this).hasClass('table-active')) {
            $(this).removeClass('table-active');
            selectedRowId = null;
        } else {
            $('#tabla-inventario tbody tr.table-active').removeClass('table-active');
            $(this).addClass('table-active');
            selectedRowId = row.id;
        }
    });

    // Menú contextual: click derecho en fila
    $('#tabla-inventario tbody').on('contextmenu', 'tr', function(e) {
        e.preventDefault();
        const row = tabla.row(this).data();
        if (!row) return;
        // seleccionar la fila
        $('#tabla-inventario tbody tr.table-active').removeClass('table-active');
        $(this).addClass('table-active');
        selectedRowId = row.id;

        // posicionar y mostrar menú
        const menu = $('#context-menu');
        menu.data('id', selectedRowId);
        menu.css({ top: e.pageY + 'px', left: e.pageX + 'px' }).show();
        return false;
    });

    // Ocultar menú al hacer click en cualquier parte
    $(document).on('click', function(e) {
        $('#context-menu').hide();
    });

    // Acciones del menú contextual
    $('#context-menu').on('click', '.cm-item', function(e) {
        e.stopPropagation();
        const action = $(this).data('action');
        const id = $('#context-menu').data('id');
        $('#context-menu').hide();
        if (!id) return;
        if (action === 'editar') {
            openEditModal(id);
        } else if (action === 'eliminar') {
            deleteMaterial(id);
        } else if (action === 'asignar') {
            assignMaterial(id);
        }
    });

    function openImageModal(src, filename) {
        if (!src) return;
        // Evitar abrir si ya está abierto
        if ($('#imageModal').hasClass('show')) return;
        $('#imageModalImg').attr('src', src);
        if (filename) {
            $('#imageModalLabel').text(filename);
        } else {
            $('#imageModalLabel').text('Imagen');
        }
        $('#imageModal').modal('show');
    }

    // Doble clic en tabla para abrir modal
    $(document).on('dblclick', '#tabla-inventario tbody img.img-open', function(e) {
        const src = $(this).attr('src');
        const filename = $(this).data('filename') || '';
        openImageModal(src, filename);
    });

    // Click simple en tabla también abre modal (por accesibilidad)
    $(document).on('click', '#tabla-inventario tbody img.img-open', function(e) {
        const src = $(this).attr('src');
        const filename = $(this).data('filename') || '';
        openImageModal(src, filename);
    });

    // Abrir imagen en modal al hacer clic en vistas previas del modal de edición
    $(document).on('click', '#img-foto1, #img-foto2', function(e) {
        const src = $(this).attr('src');
        const filename = '';
        openImageModal(src, filename);
    });
});
