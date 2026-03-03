from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import Inventario, Asignacion, Usuario

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@dashboard_bp.route('/')
@login_required
def index():
    """Dashboard principal con estadísticas"""
    # Obtener estadísticas según rol
    stats = obtener_estadisticas()
    
    return render_template('dashboard.html', stats=stats)


def obtener_estadisticas():
    """Obtener estadísticas según el rol del usuario"""
    stats = {}
    
    if current_user.rol == 'Superintendente':
        # Estadísticas completas
        stats['total_materiales'] = Inventario.query.filter_by(activo=True).count()
        stats['total_stock'] = db.session.query(db.func.sum(Inventario.cantidad)).filter_by(activo=True).scalar() or 0
        stats['solicitudes_pendientes'] = Asignacion.query.filter_by(estatus='Pendiente').count()
        stats['usuarios_activos'] = Usuario.query.filter_by(activo=True).count()
        
    elif current_user.rol == 'Supervisor':
        stats['total_materiales'] = Inventario.query.filter_by(activo=True).count()
        stats['total_stock'] = db.session.query(db.func.sum(Inventario.cantidad)).filter_by(activo=True).scalar() or 0
        stats['solicitudes_pendientes'] = Asignacion.query.filter_by(estatus='Pendiente').count()
        stats['usuarios_activos'] = Usuario.query.filter_by(activo=True).count()
        
    else:  # Analista
        stats['mis_solicitudes'] = Asignacion.query.filter_by(id_usuario_receptor=current_user.id).count()
        stats['mis_asignaciones'] = Asignacion.query.filter_by(
            id_usuario_receptor=current_user.id, 
            estatus='Aprobado'
        ).count()
    
    return stats


@dashboard_bp.route('/api/mis-materiales')
@login_required
def mis_materiales():
    """API para obtener los materiales asignados al usuario actual"""
    draw = int(request.args.get('draw', 1))
    start = int(request.args.get('start', 0))
    length = int(request.args.get('length', 10))
    
    # Obtener asignaciones aprobadas del usuario
    query = Asignacion.query.filter_by(
        id_usuario_receptor=current_user.id,
        estatus='Aprobado'
    )
    
    total_records = query.count()
    
    asignaciones = query.order_by(Asignacion.fecha_aprobacion.desc()).offset(start).limit(length).all()
    
    data = []
    for a in asignaciones:
        data.append({
            'id': a.id,
            'material': a.material.material,
            'tipo': a.material.tipo,
            'cantidad': a.cantidad,
            'fecha_asignacion': a.fecha_aprobacion.strftime('%Y-%m-%d %H:%M') if a.fecha_aprobacion else '',
            'asignado_por': a.asignador.nombres if a.asignador else 'N/A'
        })
    
    return jsonify({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': total_records,
        'data': data
    })


@dashboard_bp.route('/api/estadisticas')
@login_required
def api_estadisticas():
    """API para obtener estadísticas en JSON"""
    return jsonify({
        'success': True,
        'data': obtener_estadisticas()
    })
