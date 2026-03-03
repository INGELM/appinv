from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import Inventario, Asignacion
from app.forms import InventarioForm
from datetime import datetime
import json

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
    
    # Query base
    query = Inventario.query.filter_by(activo=True)
    
    # Filtrar por búsqueda
    if search_value:
        query = query.filter(
            db.or_(
                Inventario.material.ilike(f'%{search_value}%'),
                Inventario.descripcion.ilike(f'%{search_value}%'),
                Inventario.proveedor.ilike(f'%{search_value}%'),
                Inventario.num_proceso.ilike(f'%{search_value}%'),
                Inventario.tipo.ilike(f'%{search_value}%')
            )
        )
    
    # Contar total registros
    total_records = query.count()
    
    # Obtener datos con paginación
    inventarios = query.order_by(Inventario.fecha_ingreso.desc()).offset(start).limit(length).all()
    
    # Preparar datos para DataTables
    data = []
    for inv in inventarios:
        data.append({
            'id': inv.id,
            'fecha_ingreso': inv.fecha_ingreso.strftime('%d-%m-%Y'),
            'num_proceso': inv.num_proceso or '',
            'proveedor': inv.proveedor or '',
            'material': inv.material,
            'descripcion': inv.descripcion or '',
            'cantidad': inv.cantidad,
            'cantidad_disponible': inv.cantidad_disponible,
            'cantidad_asignada': inv.cantidad_asignada,
            'tipo': inv.tipo,
            'observaciones': inv.observaciones or ''
        })
    
    return jsonify({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': total_records,
        'data': data
    })


@inventario_bp.route('/api/crear', methods=['POST'])
@login_required
def crear():
    """API para crear nuevo material en el inventario"""
    try:
        data = request.get_json()
        
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
        data = request.get_json()
        
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
            db.or_(Asignacion.estatus == 'Pendiente', Asignacion.estatus == 'Aprobado')
        ).count()
        print(f"eliminar: id={id}, inventario.activo={inventario.activo}, active_assignments={active_count}")

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
            'observaciones': inventario.observaciones
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
