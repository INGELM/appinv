from flask import Blueprint, current_app, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import Inventario, Asignacion
from app.forms import InventarioForm
from datetime import datetime
import json
import os

inventario_bp = Blueprint('inventario', __name__, url_prefix='/inventario')


@inventario_bp.route('/')
@login_required
def index():
    """Página principal del inventario"""
    return render_template('inventario/index.html')


@inventario_bp.route('/api/listar', methods=['GET'])
@login_required
def listar():
    """API para listar inventario con DataTables"""
    # Obtener parámetros de DataTables
    draw = int(request.args.get('draw', 1))
    start = int(request.args.get('start', 0))
    length = int(request.args.get('length', 10))
    search_value = request.args.get('search[value]', '')

    # Query base (activos)
    base_query = Inventario.query.filter_by(activo=True)

    # Contar total registros sin filtrar (para DataTables)
    total_records = base_query.count()

    # Aplicar filtros de búsqueda: tokenizar y requerir que cada token aparezca
    # en al menos uno de los campos (AND entre tokens, OR entre campos)
    query = base_query
    if search_value:
        # Normalizar espacios y dividir en tokens
        tokens = [t.strip() for t in search_value.split() if t.strip()]
        for tok in tokens:
            like_tok = f"%{tok}%"
            query = query.filter(
                db.or_(
                    Inventario.material.ilike(like_tok),
                    Inventario.descripcion.ilike(like_tok),
                    Inventario.proveedor.ilike(like_tok),
                    Inventario.num_proceso.ilike(like_tok),
                    Inventario.tipo.ilike(like_tok)
                )
            )

    # Contar registros filtrados
    filtered_records = query.count()

    # Ordenamiento (DataTables serverSide)
    order_col_idx = request.args.get('order[0][column]')
    order_dir = request.args.get('order[0][dir]', 'asc')
    # Mapeo de índices de columna a atributos del modelo
    col_map = {
        '0': Inventario.id,
        '1': Inventario.fecha_ingreso,
        '2': Inventario.num_proceso,
        '3': Inventario.proveedor,
        '4': Inventario.material,
        '5': Inventario.descripcion,
        '6': Inventario.cantidad,
        '7': Inventario.cantidad_disponible,
        '8': Inventario.tipo,
        '9': Inventario.foto1,
        '10': Inventario.foto2,
        # '11' corresponde a 'asignado_a' calculado; usamos material como fallback
        '11': Inventario.material
    }

    if order_col_idx and order_col_idx in col_map:
        col = col_map[order_col_idx]
        if order_dir == 'desc':
            query = query.order_by(col.desc())
        else:
            query = query.order_by(col.asc())
    else:
        # Orden por defecto
        query = query.order_by(Inventario.fecha_ingreso.desc())

    # Obtener datos con paginación
    inventarios = query.offset(start).limit(length).all()

    # Preparar datos para DataTables
    data = []
    for inv in inventarios:
        # Obtener lista de usuarios asignados (estatus 'Aprobado'), soportando receptores externos
        asignados = [ (a.receptor.nombres if a.receptor else (a.receptor_nombre or '')) for a in inv.asignaciones.filter_by(estatus='Aprobado').all() ]
        asignado_a = ', '.join([s for s in asignados if s]) if asignados else ''
        data.append({
            'id': inv.id,
            'fecha_ingreso': inv.fecha_ingreso.strftime('%d-%m-%Y'),
            'num_proceso': inv.num_proceso or '',
            'proveedor': inv.proveedor or '',
            'material': inv.material,
            'descripcion': inv.descripcion or '',
            'asignado_a': asignado_a,
            'cantidad': inv.cantidad,
            'cantidad_disponible': inv.cantidad_disponible,
            'cantidad_asignada': inv.cantidad_asignada,
            'tipo': inv.tipo,
            'observaciones': inv.observaciones or '',
            'foto1': inv.foto1 or '',
            'foto2': inv.foto2 or ''
        })

    return jsonify({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': filtered_records,
        'data': data
    })


@inventario_bp.route('/api/crear', methods=['POST'])
@login_required
def crear():
    """API para crear nuevo material en el inventario"""
    try:
        # Manejo de JSON o multipart/form-data
        data = {}
        if request.content_type and request.content_type.startswith('application/json'):
            data = request.get_json() or {}
        elif request.content_type and request.content_type.startswith('multipart/form-data'):
            data = request.form.to_dict() or {}

        # Validar datos requeridos
        if not data.get('material') or not data.get('cantidad') or not data.get('tipo'):
            return jsonify({'success': False, 'message': 'Datos incompletos'}), 400

        inventario = Inventario(
            fecha_ingreso=datetime.utcnow(),
            num_proceso=data.get('num_proceso'),
            proveedor=data.get('proveedor'),
            material=data['material'],
            descripcion=data.get('descripcion'),
            cantidad=int(data['cantidad']),
            tipo=data['tipo'],
            observaciones=data.get('observaciones')
        )

        db.session.add(inventario)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Material registrado correctamente',
            'data': {
                'id': inventario.id,
                'material': inventario.material
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@inventario_bp.route('/api/editar/<int:id>', methods=['POST'])
@login_required
def editar(id):
    """API para editar material del inventario"""
    try:
        inventario = Inventario.query.get_or_404(id)
        # Manejo de datos JSON o multipart/form-data
        data = {}  # Inicialización predeterminada para evitar errores
        if request.content_type.startswith('application/json'):
            data = request.get_json() or {}
        elif request.content_type.startswith('multipart/form-data'):
            data = request.form.to_dict() or {}

        # Actualizar campos
        if 'material' in data:
            inventario.material = data['material']
        if 'descripcion' in data:
            inventario.descripcion = data['descripcion']
        if 'cantidad' in data:
            inventario.cantidad = int(data['cantidad'])
        if 'tipo' in data:
            inventario.tipo = data['tipo']
        if 'num_proceso' in data:
            inventario.num_proceso = data['num_proceso']
        if 'proveedor' in data:
            inventario.proveedor = data['proveedor']
        if 'observaciones' in data:
            inventario.observaciones = data['observaciones']

        # Manejo de archivos subidos
        if 'foto1' in request.files:
            foto1 = request.files['foto1']
            if foto1:
                print(f"Received file foto1: {foto1.filename}")
                filename = f"material_{id}_foto1_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{foto1.filename.split('.')[-1]}"
                filepath = os.path.join(
                    current_app.config['UPLOAD_FOLDER'], filename)
                print(f"Saving foto1 to: {filepath}")
                foto1.save(filepath)
                inventario.foto1 = filename

        # Permitir marcar eliminación de foto1
        if data.get('delete_foto1') in ('1', 'true', 'True'):
            if inventario.foto1:
                try:
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], inventario.foto1)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"Removed file foto1: {file_path}")
                except Exception as e:
                    print(f"Error removing foto1 file: {e}")
            inventario.foto1 = None

        if 'foto2' in request.files:
            foto2 = request.files['foto2']
            if foto2:
                print(f"Received file foto2: {foto2.filename}")
                filename = f"material_{id}_foto2_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{foto2.filename.split('.')[-1]}"
                filepath = os.path.join(
                    current_app.config['UPLOAD_FOLDER'], filename)
                print(f"Saving foto2 to: {filepath}")
                foto2.save(filepath)
                inventario.foto2 = filename

        # Permitir marcar eliminación de foto2
        if data.get('delete_foto2') in ('1', 'true', 'True'):
            if inventario.foto2:
                try:
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], inventario.foto2)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"Removed file foto2: {file_path}")
                except Exception as e:
                    print(f"Error removing foto2 file: {e}")
            inventario.foto2 = None

        # Depuración: Confirmar contenido de 'data'
        print(f"Datos procesados: {data}")

        # Depuración: Verificar archivo foto1
        if 'foto1' in request.files:
            foto1 = request.files['foto1']
            print(f"Archivo foto1 recibido: {foto1.filename}")
        else:
            print("Archivo foto1 no recibido")

        # Depuración: Verificar archivo foto2
        if 'foto2' in request.files:
            foto2 = request.files['foto2']
            print(f"Archivo foto2 recibido: {foto2.filename}")
        else:
            print("Archivo foto2 no recibido")

        # Depuración: Verificar antes de commit
        print(f"Datos antes de commit: {inventario}")

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Material actualizado correctamente'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@inventario_bp.route('/api/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar(id):
    """API para eliminar (desactivar) material del inventario"""
    try:
        inventario = Inventario.query.get_or_404(id)
        # Depuración: contar asignaciones activas y mostrar info
        active_count = inventario.asignaciones.filter(
            db.or_(Asignacion.estatus == 'Pendiente',
                   Asignacion.estatus == 'Aprobado')
        ).count()
        print(
            f"eliminar: id={id}, inventario.activo={inventario.activo}, active_assignments={active_count}")

        # Verificar si hay asignaciones vinculadas
        if not inventario.puede_eliminarse():
            return jsonify({
                'success': False,
                'message': 'No se puede eliminar el material porque tiene asignaciones activas',
                'active_assignments': active_count
            }), 400

        # Desactivar en lugar de eliminar (soft delete)
        inventario.activo = False
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Material eliminado correctamente'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@inventario_bp.route('/api/obtener/<int:id>', methods=['GET'])
@login_required
def obtener(id):
    """API para obtener un material específico"""
    inventario = Inventario.query.get_or_404(id)

    return jsonify({
        'success': True,
        'data': {
            'id': inventario.id,
            'num_proceso': inventario.num_proceso,
            'proveedor': inventario.proveedor,
            'material': inventario.material,
            'descripcion': inventario.descripcion,
            'cantidad': inventario.cantidad,
            'cantidad_disponible': inventario.cantidad_disponible,
            'cantidad_asignada': inventario.cantidad_asignada,
            'tipo': inventario.tipo,
            'observaciones': inventario.observaciones,
            'foto1': inventario.foto1 or '',
            'foto2': inventario.foto2 or '',
            'asignado_a': ', '.join([ (a.receptor.nombres if a.receptor else (a.receptor_nombre or '')) for a in inventario.asignaciones.filter_by(estatus='Aprobado').all() ])
        }
    })


@inventario_bp.route('/api/materiales', methods=['GET'])
@login_required
def listar_materiales():
    """API para listar materiales disponibles (para selects)"""
    q = request.args.get('q', '').strip()
    query = Inventario.query.filter_by(activo=True)
    if q:
        query = query.filter(Inventario.material.ilike(f'%{q}%'))

    materiales = query.all()

    data = []
    for m in materiales:
        if m.cantidad_disponible > 0:
            data.append({
                'id': m.id,
                'material': m.material,
                'descripcion': m.descripcion or '',
                'cantidad_disponible': m.cantidad_disponible,
                'tipo': m.tipo
            })

    return jsonify({'success': True, 'data': data})


@inventario_bp.route('/api/materiales_public', methods=['GET'])
def listar_materiales_public():
    """Endpoint público (sin login) para listar materiales con cantidad disponible.
    Uso temporal para diagnosticar problemas de carga en selects del frontend.
    """
    q = request.args.get('q', '').strip()
    query = Inventario.query.filter_by(activo=True)
    if q:
        query = query.filter(Inventario.material.ilike(f'%{q}%'))

    materiales = query.all()

    data = []
    for m in materiales:
        if m.cantidad_disponible > 0:
            data.append({
                'id': m.id,
                'material': m.material,
                'descripcion': m.descripcion or '',
                'cantidad_disponible': m.cantidad_disponible,
                'tipo': m.tipo
            })

    return jsonify({'success': True, 'data': data})


@inventario_bp.route('/api/subir_fotos/<int:id>', methods=['POST'])
@login_required
def subir_fotos(id):
    """API para subir fotos de un material"""
    try:
        inventario = Inventario.query.get_or_404(id)

        # Asegurar que 'data' esté definido y registrar su contenido
        data = {}
        if request.content_type and request.content_type.startswith('application/json'):
            data = request.get_json() or {}
        elif request.content_type and request.content_type.startswith('multipart/form-data'):
            data = request.form.to_dict() or {}
        print(f"Datos procesados (subir_fotos): {data}")

        # Manejo de archivos subidos
        if 'foto1' in request.files:
            foto1 = request.files['foto1']
            if foto1:
                print(f"Received file foto1: {foto1.filename}")
                filename = f"material_{id}_foto1_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{foto1.filename.split('.')[-1]}"
                filepath = os.path.join(
                    current_app.config['UPLOAD_FOLDER'], filename)
                print(f"Saving foto1 to: {filepath}")
                foto1.save(filepath)
                inventario.foto1 = filename

        if 'foto2' in request.files:
            foto2 = request.files['foto2']
            if foto2:
                print(f"Received file foto2: {foto2.filename}")
                filename = f"material_{id}_foto2_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{foto2.filename.split('.')[-1]}"
                filepath = os.path.join(
                    current_app.config['UPLOAD_FOLDER'], filename)
                print(f"Saving foto2 to: {filepath}")
                foto2.save(filepath)
                inventario.foto2 = filename

        # Depuración: Verificar datos recibidos
        print(f"Editar inventario: ID={id}")
        print(f"Content-Type: {request.content_type}")
        print(f"Datos recibidos: {data}")

        # Depuración: Verificar archivo foto1
        if 'foto1' in request.files:
            foto1 = request.files['foto1']
            print(f"Archivo foto1 recibido: {foto1.filename}")
        else:
            print("Archivo foto1 no recibido")

        # Depuración: Verificar archivo foto2
        if 'foto2' in request.files:
            foto2 = request.files['foto2']
            print(f"Archivo foto2 recibido: {foto2.filename}")
        else:
            print("Archivo foto2 no recibido")

        # Depuración: Verificar antes de commit
        print(f"Datos antes de commit: {inventario}")

        db.session.commit()

        return jsonify({'success': True, 'message': 'Fotos subidas correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
