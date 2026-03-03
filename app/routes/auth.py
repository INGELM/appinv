from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import db, csrf
from app.models import Usuario
from app.forms import LoginForm, RegisterForm, ActivarUsuarioForm
from functools import wraps

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


def rol_required(*roles):
    """Decorador para requerir roles específicos"""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.rol not in roles:
                flash('No tiene permisos para acceder a esta página.', 'danger')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(usuario=form.usuario.data).first()
        
        if usuario is None:
            flash('Usuario no encontrado.', 'danger')
            return render_template('auth/login.html', form=form)
        
        if not usuario.activo:
            flash('Su cuenta está inactiva. Contacte a un Supervisor para activarla.', 'warning')
            return render_template('auth/login.html', form=form)
        
        if usuario.check_password(form.password.data):
            login_user(usuario)
            next_page = request.args.get('next')
            flash(f'Bienvenido, {usuario.nombres}!', 'success')
            return redirect(next_page if next_page else url_for('dashboard.index'))
        else:
            flash('Contraseña incorrecta.', 'danger')
    
    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        # Verificar si el usuario ya existe
        if Usuario.query.filter_by(usuario=form.usuario.data).first():
            flash('El nombre de usuario ya existe.', 'danger')
            return render_template('auth/register.html', form=form)
        
        # Crear nuevo usuario
        usuario = Usuario(
            nombres=form.nombres.data,
            usuario=form.usuario.data,
            rol=form.rol.data,
            activo=False  # Por defecto inactivo hasta que un Supervisor lo active
        )
        usuario.set_password(form.password.data)
        
        db.session.add(usuario)
        db.session.commit()
        
        flash('Registro exitoso. Su cuenta será activada por un Supervisor.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Ha cerrado sesión correctamente.', 'info')
    return redirect(url_for('auth.login'))


# API Routes para AJAX

@auth_bp.route('/api/usuarios', methods=['GET'])
@login_required
def listar_usuarios():
    """Listar usuarios para administradores/supervisores"""
    if not current_user.puede_activar():
        return jsonify({'success': False, 'message': 'No autorizado'}), 403
    q = request.args.get('q', '').strip()
    query = Usuario.query
    if q:
        query = query.filter(db.or_(Usuario.nombres.ilike(f'%{q}%'), Usuario.usuario.ilike(f'%{q}%')))

    usuarios = query.all()
    data = []
    for u in usuarios:
        data.append({
            'id': u.id,
            'nombres': u.nombres,
            'usuario': u.usuario,
            'rol': u.rol,
            'activo': u.activo,
            'fecha_creacion': u.fecha_creacion.strftime('%Y-%m-%d %H:%M')
        })

    return jsonify({'success': True, 'data': data})


@auth_bp.route('/api/usuarios/crear', methods=['POST'])
@csrf.exempt
@login_required
def crear_usuario_api():
    """Crear un nuevo usuario vía API (para administradores/supervisores)"""
    if not current_user.puede_activar():
        return jsonify({'success': False, 'message': 'No autorizado'}), 403

    # Log para depuración: imprimir headers y body recibido
    try:
        print('crear_usuario_api: Content-Type=', request.content_type)
        print('crear_usuario_api: Raw body=', request.get_data(as_text=True))
    except Exception as e:
        print('crear_usuario_api: error al leer body:', e)

    # Intentar leer JSON; si no hay, intentar form data para mayor tolerancia
    data = {}
    try:
        if request.is_json:
            data = request.get_json() or {}
        else:
            # intentar parsear como form-encoded
            data = request.form.to_dict() or {}
            # si sigue vacío, intentar decodificar body crudo
            if not data:
                raw = request.get_data(as_text=True)
                try:
                    import json as _json
                    data = _json.loads(raw) if raw else {}
                except Exception:
                    data = {}
    except Exception as e:
        print('Error al parsear body en crear_usuario_api:', e)
        data = {}

    nombres = data.get('nombres')
    usuario = data.get('usuario')
    password = data.get('password')
    rol = data.get('rol')
    activo = bool(data.get('activo', False))

    missing = [k for k in ('nombres', 'usuario', 'password', 'rol') if not data.get(k)]
    if missing:
        return jsonify({'success': False, 'message': f'Datos incompletos, faltan: {", ".join(missing)}', 'received': data}), 400

    if Usuario.query.filter_by(usuario=usuario).first():
        return jsonify({'success': False, 'message': 'El nombre de usuario ya existe'}), 400

    try:
        nuevo = Usuario(
            nombres=nombres,
            usuario=usuario,
            rol=rol,
            activo=activo
        )
        nuevo.set_password(password)
        db.session.add(nuevo)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Usuario creado correctamente', 'data': {'id': nuevo.id}})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@auth_bp.route('/usuarios')
@login_required
def usuarios():
    """Página de gestión de usuarios (DataTable)"""
    if not current_user.puede_activar():
        flash('No tiene permisos para acceder a usuarios.', 'danger')
        return redirect(url_for('dashboard.index'))

    return render_template('auth/usuarios.html')


@auth_bp.route('/api/usuarios/<int:id>/activar', methods=['POST'])
@login_required
def activar_usuario(id):
    """Activar/desactivar usuario"""
    if not current_user.puede_activar():
        return jsonify({'success': False, 'message': 'No autorizado'}), 403
    
    data = request.get_json()
    usuario = Usuario.query.get_or_404(id)
    
    usuario.activo = data.get('activo', False)
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'Usuario {"activado" if usuario.activo else "desactivado"} correctamente'
    })
