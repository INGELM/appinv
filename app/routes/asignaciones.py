from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask import Response
from flask_login import login_required, current_user
from app import db
from app import csrf
from app.models import Inventario, Asignacion, Usuario
from app.forms import AsignacionForm, AprobacionForm
from datetime import datetime

asignaciones_bp = Blueprint('asignaciones', __name__, url_prefix='/asignaciones')


@asignaciones_bp.route('/')
@login_required
def index():
    """Página principal de asignaciones/solicitudes"""
    return render_template('asignaciones/index.html')


@asignaciones_bp.route('/mis-solicitudes')
@login_required
def mis_solicitudes():
    """Página de solicitudes del usuario actual"""
    return render_template('asignaciones/mis_solicitudes.html')


@asignaciones_bp.route('/mis-asignaciones')
@login_required
def mis_asignaciones():
    """Página que muestra las asignaciones aprobadas al usuario actual"""
    return render_template('asignaciones/mis_asignaciones.html')


# API Routes

@asignaciones_bp.route('/api/listar', methods=['GET'])
@login_required
def listar():
    """API para listar solicitudes de asignación"""
    draw = int(request.args.get('draw', 1))
    start = int(request.args.get('start', 0))
    length = int(request.args.get('length', 10))
    search_value = request.args.get('search[value]', '')
    filtro_estatus = request.args.get('estatus', '')
    
    # Query base
    query = Asignacion.query
    
    # Filtrar según rol y permisos
    if current_user.rol == 'Analista':
        query = query.filter_by(id_usuario_receptor=current_user.id)
    elif current_user.rol == 'Supervisor':
        # Supervisores ven todas las solicitudes pendientes de aprobación
        query = query.filter(Asignacion.estatus == 'Pendiente')
    
    # Filtrar por búsqueda
    if search_value:
        query = query.join(Inventario).filter(
            db.or_(
                Inventario.material.ilike(f'%{search_value}%'),
                Usuario.nombres.ilike(f'%{search_value}%')
            )
        )
    
    # Filtrar por estatus
    if filtro_estatus:
        query = query.filter_by(estatus=filtro_estatus)
    
    # Contar total
    total_records = query.count()
    
    # Obtener datos
    asignaciones = query.order_by(Asignacion.fecha_solicitud.desc()).offset(start).limit(length).all()
    
    data = []
    for a in asignaciones:
        data.append({
            'id': a.id,
            'material': a.material.material,
            'cantidad': a.cantidad,
            'receptor': a.receptor.nombres if a.receptor else 'N/A',
            'asignador': a.asignador.nombres if a.asignador else 'N/A',
            'estatus': a.estatus,
            'fecha_solicitud': a.fecha_solicitud.strftime('%d-%m-%Y %H:%M'),
            'fecha_aprobacion': a.fecha_aprobacion.strftime('%d-%m-%Y %H:%M') if a.fecha_aprobacion else '',
            'fecha_devolucion': a.fecha_devolucion.strftime('%d-%m-%Y %H:%M') if a.fecha_devolucion else '',
            'observaciones': a.observaciones or ''
        })
    
    return jsonify({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': total_records,
        'data': data
    })


@asignaciones_bp.route('/api/mis-solicitudes', methods=['GET'])
@login_required
def mis_solicitudes_api():
    """API para listar las solicitudes del usuario actual"""
    draw = int(request.args.get('draw', 1))
    start = int(request.args.get('start', 0))
    length = int(request.args.get('length', 10))
    
    query = Asignacion.query.filter_by(id_usuario_receptor=current_user.id)
    total_records = query.count()
    
    asignaciones = query.order_by(Asignacion.fecha_solicitud.desc()).offset(start).limit(length).all()
    
    data = []
    for a in asignaciones:
        data.append({
            'id': a.id,
            'material': a.material.material,
            'cantidad': a.cantidad,
            'estatus': a.estatus,
            'fecha_solicitud': a.fecha_solicitud.strftime('%d-%m-%Y %H:%M'),
            'fecha_aprobacion': a.fecha_aprobacion.strftime('%d-%m-%Y %H:%M') if a.fecha_aprobacion else '',
            'fecha_devolucion': a.fecha_devolucion.strftime('%d-%m-%Y %H:%M') if a.fecha_devolucion else '',
            'observaciones': a.observaciones or ''
        })
    
    return jsonify({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': total_records,
        'data': data
    })


@asignaciones_bp.route('/api/mis-asignaciones', methods=['GET'])
@login_required
def mis_asignaciones_api():
    """API para listar asignaciones aprobadas del usuario actual"""
    draw = int(request.args.get('draw', 1))
    start = int(request.args.get('start', 0))
    length = int(request.args.get('length', 10))

    # Solo asignaciones donde el usuario es receptor y estén aprobadas
    query = Asignacion.query.filter_by(id_usuario_receptor=current_user.id, estatus='Aprobado')

    total_records = query.count()

    asignaciones = query.order_by(Asignacion.fecha_aprobacion.desc()).offset(start).limit(length).all()

    data = []
    for a in asignaciones:
        data.append({
            'id': a.id,
            'material': a.material.material,
            'cantidad': a.cantidad,
            'asignador': a.asignador.nombres if a.asignador else 'N/A',
            'fecha_aprobacion': a.fecha_aprobacion.strftime('%d-%m-%Y %H:%M') if a.fecha_aprobacion else '',
            'observaciones': a.observaciones or ''
        })

    return jsonify({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': total_records,
        'data': data
    })


@asignaciones_bp.route('/api/solicitar', methods=['POST'])
@csrf.exempt
@login_required
def solicitar():
    """API para crear una nueva solicitud de asignación"""
    try:
        # debug prints
        try:
            print('solicitar: Content-Type=', request.content_type)
            print('solicitar: Raw body=', request.get_data(as_text=True))
        except Exception as _:
            pass

        data = request.get_json() or {}
        
        # Validar datos
        if not data.get('id_material') or not data.get('cantidad'):
            return jsonify({'success': False, 'message': 'Datos incompletos', 'received': data}), 400

        # Verificar disponibilidad
        inventario = Inventario.query.get(data['id_material'])
        if not inventario:
            return jsonify({'success': False, 'message': 'Material no encontrado'}), 404

        cantidad_solicitada = int(data['cantidad'])
        if inventario.cantidad_disponible < cantidad_solicitada:
            return jsonify({
                'success': False,
                'message': f'Cantidad no disponible. Máximo: {inventario.cantidad_disponible}'
            }), 400

        # Determinar receptor: si el usuario puede asignar, puede indicar otro receptor
        if current_user.tiene_permiso('asignar') and data.get('id_usuario_receptor'):
            receptor_id = int(data['id_usuario_receptor'])
        else:
            receptor_id = current_user.id

        # Crear asignación
        asignacion = Asignacion(
            id_material=data['id_material'],
            id_usuario_receptor=receptor_id,
            cantidad=cantidad_solicitada,
            estatus='Pendiente' if not current_user.tiene_permiso('asignar') else 'Aprobado',
            observaciones=data.get('observaciones')
        )

            # Si el usuario asigna directamente, registrar asignador y fecha.
        if current_user.tiene_permiso('asignar'):
            asignacion.id_usuario_asignador = current_user.id
            from datetime import datetime
            asignacion.fecha_aprobacion = datetime.utcnow()
            # NOTA: no modificar `inventario.cantidad` aquí; la disponibilidad
            # se calcula como `cantidad - sum(asignaciones aprobadas)`.

        db.session.add(asignacion)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Solicitud enviada correctamente' if not current_user.tiene_permiso('asignar') else 'Asignación creada y aprobada'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@asignaciones_bp.route('/api/aprobar/<int:id>', methods=['POST'])
@login_required
@csrf.exempt
def aprobar(id):
    """API para aprobar/rechazar una solicitud (Superintendente)"""
    if current_user.rol != 'Superintendente':
        return jsonify({'success': False, 'message': 'No autorizado'}), 403
    
    try:
        asignacion = Asignacion.query.get_or_404(id)
        data = request.get_json()
        
        if asignacion.estatus != 'Pendiente':
            return jsonify({'success': False, 'message': 'La solicitud ya fue procesada'}), 400
        
        estatus = data.get('estatus')
        
        if estatus == 'Aprobado':
            # Verificar disponibilidad antes de aprobar
            inventario = asignacion.material
            if inventario.cantidad_disponible < asignacion.cantidad:
                return jsonify({
                    'success': False, 
                    'message': 'No hay suficiente stock disponible'
                }), 400
            
            # Actualizar estatus (la disponibilidad ya se comprueba arriba)
            asignacion.estatus = 'Aprobado'
            asignacion.fecha_aprobacion = datetime.utcnow()
            # La disponibilidad se calcula como `cantidad - asignadas`; no modificar `cantidad`.
            
        elif estatus == 'Rechazar':
            asignacion.estatus = 'Rechazado'
            asignacion.fecha_aprobacion = datetime.utcnow()
        
        if 'observaciones' in data:
            asignacion.observaciones = data['observaciones']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Solicitud {"aprobada" if estatus == "Aprobado" else "rechazada"} correctamente'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@asignaciones_bp.route('/api/entregar/<int:id>', methods=['POST'])
@csrf.exempt
@login_required
def entregar(id):
    """API para ejecutar la entrega de una solicitud aprobada (Supervisor)"""
    if current_user.rol not in ['Supervisor', 'Superintendente']:
        return jsonify({'success': False, 'message': 'No autorizado'}), 403
    
    try:
        asignacion = Asignacion.query.get_or_404(id)

        # Debug info
        try:
            print(f"entregar: id={id}, asignacion.estatus={asignacion.estatus}, asignacion.id_usuario_receptor={asignacion.id_usuario_receptor}, current_user.id={current_user.id}, current_user.rol={current_user.rol}")
            inventario = asignacion.material
            print(f"entregar: inventario.id={inventario.id}, inventario.cantidad={inventario.cantidad}, inventario.cantidad_disponible={inventario.cantidad_disponible}")
        except Exception:
            pass

        if asignacion.estatus != 'Aprobado':
            return jsonify({'success': False, 'message': 'La solicitud debe estar aprobada primero', 'estatus_actual': asignacion.estatus}), 400
        
        # Registrar quién entregó (no modificar `inventario.cantidad`; la política
        # es mantener `cantidad` como total y calcular disponibilidad via asignaciones).
        asignacion.id_usuario_asignador = current_user.id
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Material entregado correctamente'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@asignaciones_bp.route('/api/devolver/<int:id>', methods=['POST'])
@csrf.exempt
@login_required
def devolver(id):
    """API para devolver material al inventario (reintegrar)"""
    if current_user.rol not in ['Supervisor', 'Superintendente']:
        return jsonify({'success': False, 'message': 'No autorizado'}), 403

    try:
        asignacion = Asignacion.query.get_or_404(id)

        # Solo se puede devolver una asignación aprobada
        if asignacion.estatus != 'Aprobado':
            return jsonify({'success': False, 'message': 'Solo se puede devolver una asignación aprobada', 'estatus_actual': asignacion.estatus}), 400

        # Reintegración: no cambiar `inventario.cantidad` cuando la política
        # es mantener el total; simplemente marcar como reintegrado y timestamp.
        from datetime import datetime
        asignacion.estatus = 'Reintegrado'
        asignacion.fecha_devolucion = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True, 'message': 'Material reintegrado al inventario correctamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@asignaciones_bp.route('/api/cancelar/<int:id>', methods=['POST'])
@csrf.exempt
@login_required
def cancelar(id):
    """API para cancelar una solicitud"""
    try:
        asignacion = Asignacion.query.get_or_404(id)
        
        # Solo el solicitante puede cancelar si está pendiente
        if asignacion.id_usuario_receptor != current_user.id:
            return jsonify({'success': False, 'message': 'No autorizado'}), 403
        
        if asignacion.estatus != 'Pendiente':
            return jsonify({'success': False, 'message': 'No se puede cancelar una solicitud ya procesada'}), 400
        
        db.session.delete(asignacion)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Solicitud cancelada correctamente'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@asignaciones_bp.route('/recibo/<int:id>')
@login_required
def recibo(id):
    """Genera un formato imprimible/descargable de la asignación"""
    asignacion = Asignacion.query.get_or_404(id)

    # Permitir ver a quien corresponda: receptor, asignador, supervisores
    if not (current_user.id == asignacion.id_usuario_receptor or
            current_user.id == asignacion.id_usuario_asignador or
            current_user.tiene_permiso('ver_inventario')):
        flash('No autorizado para ver este recibo', 'danger')
        return redirect(url_for('asignaciones.index'))

    html = render_template('asignaciones/recibo.html', a=asignacion)

    # Si ?download=1 -> forzar descarga como .html para imprimir localmente
    if request.args.get('download') == '1':
        headers = {
            'Content-Disposition': f'attachment; filename=recibo_asignacion_{asignacion.id}.html'
        }
        return Response(html, mimetype='text/html', headers=headers)

    return html
