from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager

# Tabla de relación usuario-rol para permisos
roles_permissions = {
    'Superintendente': ['aprobar', 'asignar', 'activar', 'solicitar', 'ver_inventario', 'ver_dashboard'],
    'Supervisor': ['asignar', 'activar', 'solicitar', 'ver_inventario', 'ver_dashboard'],
    'Analista': ['solicitar', 'ver_dashboard']
}

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nombres = db.Column(db.String(100), nullable=False)
    usuario = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.String(20), nullable=False)  # Superintendente, Supervisor, Analista
    activo = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    asignaciones_recibidas = db.relationship('Asignacion', foreign_keys='Asignacion.id_usuario_receptor', 
                                              backref='receptor', lazy='dynamic')
    asignaciones_hechas = db.relationship('Asignacion', foreign_keys='Asignacion.id_usuario_asignador',
                                           backref='asignador', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def tiene_permiso(self, permiso):
        return permiso in roles_permissions.get(self.rol, [])
    
    def puede_activar(self):
        return self.rol in ['Supervisor', 'Superintendente']
    
    def __repr__(self):
        return f'<Usuario {self.usuario}>'


class Inventario(db.Model):
    __tablename__ = 'inventario'
    
    id = db.Column(db.Integer, primary_key=True)
    fecha_ingreso = db.Column(db.DateTime, default=datetime.utcnow)
    num_proceso = db.Column(db.String(50), nullable=True)
    proveedor = db.Column(db.String(100), nullable=True)
    material = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    cantidad = db.Column(db.Integer, default=0)
    tipo = db.Column(db.String(20), nullable=False)  # Herramienta, Consumible, Equipo, Repuesto, Accesorio
    observaciones = db.Column(db.Text, nullable=True)
    activo = db.Column(db.Boolean, default=True)
    foto1 = db.Column(db.String(200), nullable=True)
    foto2 = db.Column(db.String(200), nullable=True)
    
    # Relaciones
    asignaciones = db.relationship('Asignacion', backref='material', lazy='dynamic')
    
    @property
    def cantidad_asignada(self):
        return sum(a.cantidad for a in self.asignaciones.filter_by(estatus='Aprobado').all())
    
    @property
    def cantidad_disponible(self):
        # Disponibilidad = total (`cantidad`) menos las asignaciones aprobadas.
        return self.cantidad - self.cantidad_asignada
    
    def puede_eliminarse(self):
        # Sólo permitir eliminar si NO existen asignaciones activas
        # Consideramos activas las asignaciones con estatus 'Pendiente' o 'Aprobado'.
        return self.asignaciones.filter(
            db.or_(
                Asignacion.estatus == 'Pendiente',
                Asignacion.estatus == 'Aprobado'
            )
        ).count() == 0
    
    def __repr__(self):
        return f'<Inventario {self.material}>'


class Asignacion(db.Model):
    __tablename__ = 'asignaciones'
    
    id = db.Column(db.Integer, primary_key=True)
    id_material = db.Column(db.Integer, db.ForeignKey('inventario.id'), nullable=False)
    id_usuario_receptor = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    id_usuario_asignador = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    cantidad = db.Column(db.Integer, nullable=False)
    estatus = db.Column(db.String(20), default='Pendiente')  # Pendiente, Aprobado, Rechazado
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_aprobacion = db.Column(db.DateTime, nullable=True)
    fecha_devolucion = db.Column(db.DateTime, nullable=True)
    observaciones = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<Asignacion {self.id} - {self.estatus}>'


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))
