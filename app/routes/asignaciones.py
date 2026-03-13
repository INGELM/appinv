from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask import Response
from flask_login import login_required, current_user
from app import db
from app import csrf
from app.models import Inventario, Asignacion, Usuario
from app.forms import AsignacionForm, AprobacionForm
from datetime import datetime

asignaciones_bp = Blueprint('asignaciones', __name__, url_prefix='/asignaciones')


def _puede_ver_asignacion(asignacion, usuario):
    """Valida si un usuario puede visualizar una asignación."""
    return (
        usuario.id == asignacion.id_usuario_receptor
        or usuario.id == asignacion.id_usuario_asignador
        or usuario.tiene_permiso('ver_inventario')
    )


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
        receptor_display = a.receptor.nombres if a.receptor else (a.receptor_nombre or 'N/A')
        if a.id_usuario_receptor:
            receptor_id_out = f'u:{a.id_usuario_receptor}'
        else:
            receptor_id_out = 'e:' + (a.receptor_nombre or '').strip().lower()
        data.append({
            'id': a.id,
            'material': a.material.material,
            'cantidad': a.cantidad,
            'receptor': receptor_display,
            'receptor_id': receptor_id_out,
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

        # Determinar receptores: si el usuario puede asignar, puede indicar otros receptores
        receptores_ids = data.get('id_usuarios_receptores', [])
        if not isinstance(receptores_ids, list):
            receptores_ids = [receptores_ids]

        receptores_externos = data.get('receptores_externos', [])
        if not isinstance(receptores_externos, list):
            receptores_externos = [receptores_externos]

        asignaciones = []
        # Receptores registrados
        for receptor_id in receptores_ids:
            try:
                rid = int(receptor_id)
            except Exception:
                continue
            asignacion = Asignacion(
                id_material=data['id_material'],
                id_usuario_receptor=rid,
                cantidad=cantidad_solicitada,
                estatus='Pendiente' if not current_user.tiene_permiso('asignar') else 'Aprobado',
                observaciones=data.get('observaciones')
            )

            if current_user.tiene_permiso('asignar'):
                asignacion.id_usuario_asignador = current_user.id
                from datetime import datetime
                asignacion.fecha_aprobacion = datetime.utcnow()

            asignaciones.append(asignacion)
            db.session.add(asignacion)

        # Receptores externos (no registrados)
        for nombre_ext in receptores_externos:
            nombre_ext = (nombre_ext or '').strip()
            if not nombre_ext:
                continue
            asignacion = Asignacion(
                id_material=data['id_material'],
                id_usuario_receptor=None,
                receptor_nombre=nombre_ext,
                cantidad=cantidad_solicitada,
                estatus='Pendiente' if not current_user.tiene_permiso('asignar') else 'Aprobado',
                observaciones=data.get('observaciones')
            )
            if current_user.tiene_permiso('asignar'):
                asignacion.id_usuario_asignador = current_user.id
                from datetime import datetime
                asignacion.fecha_aprobacion = datetime.utcnow()

            asignaciones.append(asignacion)
            db.session.add(asignacion)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Se crearon {len(asignaciones)} asignaciones correctamente.'
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
    if not _puede_ver_asignacion(asignacion, current_user):
        flash('No autorizado para ver este recibo', 'danger')
        return redirect(url_for('asignaciones.index'))

    html = render_template('asignaciones/recibo.html', a=asignacion, fecha=datetime.utcnow)

    # Si ?download=1 -> forzar descarga como .html para imprimir localmente
    if request.args.get('download') == '1':
        headers = {
            'Content-Disposition': f'attachment; filename=recibo_asignacion_{asignacion.id}.html'
        }
        return Response(html, mimetype='text/html', headers=headers)

    return html


@asignaciones_bp.route('/devolucion/<int:id>')
@login_required
def devolucion(id):
    """Genera un formato imprimible/descargable de devolución (reintegración)"""
    asignacion = Asignacion.query.get_or_404(id)

    # Permitir ver a quien corresponda: receptor, asignador, supervisores
    if not _puede_ver_asignacion(asignacion, current_user):
        flash('No autorizado para ver este comprobante', 'danger')
        return redirect(url_for('asignaciones.index'))

    # Solo si ya fue reintegrado
    if asignacion.estatus != 'Reintegrado':
        flash('La asignación no está marcada como reintegrada', 'warning')
        return redirect(url_for('asignaciones.index'))

    html = render_template('asignaciones/devolucion.html', a=asignacion, fecha=datetime.utcnow)

    # Si ?download=1 -> forzar descarga como .html para imprimir localmente
    if request.args.get('download') == '1':
        headers = {
            'Content-Disposition': f'attachment; filename=devolucion_asignacion_{asignacion.id}.html'
        }
        return Response(html, mimetype='text/html', headers=headers)

    return html


@asignaciones_bp.route('/recibo/lote')
@login_required
def recibo_lote():
    """Genera un recibo conjunto para varias asignaciones del mismo receptor."""
    ids_param = request.args.get('ids', '')
    try:
        ids = [int(x) for x in ids_param.split(',') if x.strip().isdigit()]
    except ValueError:
        ids = []

    if not ids:
        flash('Debe seleccionar al menos una asignación para imprimir.', 'warning')
        return redirect(url_for('asignaciones.index'))

    asignaciones = Asignacion.query.filter(Asignacion.id.in_(ids)).order_by(Asignacion.fecha_solicitud.asc()).all()
    if not asignaciones:
        flash('No se encontraron asignaciones para imprimir.', 'warning')
        return redirect(url_for('asignaciones.index'))

    # Validar que todas existan
    if len(asignaciones) != len(ids):
        flash('Algunas asignaciones seleccionadas no existen.', 'danger')
        return redirect(url_for('asignaciones.index'))

    # Permitir agrupar por el mismo receptor, ya sea usuario registrado o receptor externo
    def receptor_key(a):
        if a.id_usuario_receptor:
            return ('user', a.id_usuario_receptor)
        return ('ext', (a.receptor_nombre or '').strip().lower())

    first_key = receptor_key(asignaciones[0])
    if any(receptor_key(a) != first_key for a in asignaciones):
        flash('Solo se pueden agrupar asignaciones del mismo receptor.', 'danger')
        return redirect(url_for('asignaciones.index'))

    # Autorizar y validar estatus
    for a in asignaciones:
        if not _puede_ver_asignacion(a, current_user):
            flash('No autorizado para ver alguna de las asignaciones seleccionadas.', 'danger')
            return redirect(url_for('asignaciones.index'))
        if a.estatus != 'Aprobado':
            flash(f'La asignación #{a.id} no está aprobada y no puede imprimirse en recibo.', 'warning')
            return redirect(url_for('asignaciones.index'))

    html = render_template('asignaciones/recibo.html', asignaciones=asignaciones)

    if request.args.get('download') == '1':
        headers = {
            'Content-Disposition': 'attachment; filename=recibo_asignaciones_lote.html'
        }
        return Response(html, mimetype='text/html', headers=headers)

    return html
