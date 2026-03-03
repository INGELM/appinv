"""
Script de inicialización de base de datos
Crea la base de datos y el usuario inicial: Henry Morales
"""

import os
import sys

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Usuario, Inventario, Asignacion


def init_database():
    """Inicializa la base de datos con el usuario inicial"""
    
    # Crear la aplicación
    app = create_app()
    
    with app.app_context():
        # Crear todas las tablas
        print("Creando tablas de base de datos...")
        db.create_all()
        
        # Verificar si ya existe el usuario admin
        usuario_existente = Usuario.query.filter_by(usuario='moraleshl').first()
        
        if usuario_existente:
            print("El usuario 'moraleshl' ya existe en la base de datos.")
        else:
            # Crear usuario Superintendente inicial
            admin = Usuario(
                nombres='Henry Morales',
                usuario='moraleshl',
                rol='Superintendente',
                activo=True  # Activado por defecto (script inicial)
            )
            admin.set_password('123456')
            
            db.session.add(admin)
            db.session.commit()
            
            print("Usuario Administrador creado exitosamente:")
            print("  - Usuario: moraleshl")
            print("  - Contraseña: 123456")
            print("  - Rol: Superintendente")
        
       

if __name__ == '__main__':
    init_database()
