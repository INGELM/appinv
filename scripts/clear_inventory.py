#!/usr/bin/env python3
"""
scripts/clear_inventory.py

Crear un backup de `instance/inventario.db` y eliminar TODOS los registros
de las tablas `asignaciones` e `inventario` de forma segura.

Uso:
  python scripts/clear_inventory.py        # interactivo (pregunta confirmación)
  python scripts/clear_inventory.py --yes  # confirma sin preguntar
  python scripts/clear_inventory.py --no-backup  # no crear backup
"""
from pathlib import Path
import shutil
import datetime
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / 'instance' / 'inventario.db'

def backup_db():
    if not DB_PATH.exists():
        print(f"No se encontró {DB_PATH}")
        return None
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    dest = DB_PATH.with_name(f"inventario_{ts}.db.bak")
    shutil.copy2(DB_PATH, dest)
    return dest

def clear_db(confirm: bool):
    from app import create_app, db
    from app.models import Inventario, Asignacion

    app = create_app()
    with app.app_context():
        asig_count = Asignacion.query.count()
        inv_count = Inventario.query.count()
        print(f"Registros antes - Asignaciones: {asig_count}, Inventario: {inv_count}")
        if not confirm:
            print("No confirmado. Abortando sin cambios.")
            return

        # Eliminar asignaciones primero (FK -> inventario)
        deleted_asigs = db.session.query(Asignacion).delete()
        deleted_invs = db.session.query(Inventario).delete()
        db.session.commit()

        print(f"Eliminados - Asignaciones: {deleted_asigs}, Inventario: {deleted_invs}")
        asig_count2 = Asignacion.query.count()
        inv_count2 = Inventario.query.count()
        print(f"Registros después - Asignaciones: {asig_count2}, Inventario: {inv_count2}")

def main():
    parser = argparse.ArgumentParser(description='Backup y eliminación segura de registros de inventario')
    parser.add_argument('--yes', '-y', action='store_true', help='Confirmar sin preguntar')
    parser.add_argument('--no-backup', action='store_true', help='No crear backup')
    args = parser.parse_args()

    if not args.no_backup:
        dest = backup_db()
        if dest:
            print(f"Backup creado: {dest}")
        else:
            print("No se creó backup (archivo no encontrado). Abortando.")
            sys.exit(1)

    if args.yes:
        confirm = True
    else:
        ans = input("Confirma eliminar TODOS los registros de Inventario y Asignaciones? Escribe 'si' para confirmar: ")
        confirm = ans.strip().lower() == 'si'

    clear_db(confirm)

if __name__ == '__main__':
    main()
