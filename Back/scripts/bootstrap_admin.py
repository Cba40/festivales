"""Crea el primer administrador municipal. Idempotente.

Uso
---
    python -m scripts.bootstrap_admin --username admin --password "una-buena"

Por que es un script y no parte de la migración
-----------------------------------------------
La migración siembra ROLES y PERMISOS, pero no usuarios. Meter un usuario en una
migración significaría guardar una contraseña en el historial de Alembic, que es
texto plano en el repo y no se puede rotar. El primer usuario lo crea una persona
desde la consola del servidor, con una contraseña que elige ella.

Idempotente: si el username ya existe, no lo toca ni cambia su contraseña. Volver a
correrlo es seguro (útil para reinstalar sin duplicar).

El usuario recibe MUNICIPAL_ADMIN por default. Para crear un operador de campo:

    python -m scripts.bootstrap_admin --username campo --password "..." --role OPERADOR_CAMPO

Para acotarlo a una zona u evento:

    python -m scripts.bootstrap_admin --username campo --password "..." \
        --role OPERADOR_CAMPO --zone-id 22222222-2222-2222-2222-222222222222

La contraseña se pide por prompt si no se pasa por `--password`, para que no quede
en el historial del shell.
"""
from __future__ import annotations

import argparse
import getpass
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import ALL_ROLES, ROLE_MUNICIPAL_ADMIN
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import Role, User, UserRole

MIN_PASSWORD_LENGTH = 12


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scripts.bootstrap_admin",
        description="Crea el primer administrador municipal. Idempotente.",
    )
    parser.add_argument("--username", required=True, help="Nombre de usuario")
    parser.add_argument(
        "--password",
        help=(
            "Contraseña. Si se omite, se pide por prompt para que no quede en el "
            "historial del shell."
        ),
    )
    parser.add_argument(
        "--role",
        default=ROLE_MUNICIPAL_ADMIN,
        choices=sorted(set(ALL_ROLES) - {"SUPER_ADMIN"}),
        help=(
            "Rol a asignar. SUPER_ADMIN queda fuera a propósito: esa cuenta no "
            "existe en esta base, entra por variables de entorno."
        ),
    )
    parser.add_argument("--email")
    parser.add_argument("--full-name")
    parser.add_argument(
        "--event-id", help="Acota el alcance a un evento (opcional)"
    )
    parser.add_argument(
        "--zone-id", help="Acota el alcance a una zona (opcional)"
    )
    args = parser.parse_args(argv)

    password = args.password or getpass.getpass("Contraseña: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        print(
            f"ERROR: la contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.",
            file=sys.stderr,
        )
        return 1

    with SessionLocal() as db:
        existing = db.execute(
            select(User).where(User.username == args.username)
        ).scalar_one_or_none()
        if existing is not None:
            print(
                f"El usuario {args.username!r} ya existe (id={existing.id}). "
                "No se modificó nada."
            )
            return 0

        role = db.execute(
            select(Role).where(Role.code == args.role)
        ).scalar_one_or_none()
        if role is None:
            print(
                f"ERROR: el rol {args.role!r} no existe. Aplicá las migraciones "
                "(alembic upgrade head) antes de correr este script.",
                file=sys.stderr,
            )
            return 1

        user = User(
            username=args.username,
            email=args.email,
            full_name=args.full_name,
            password_hash=hash_password(password),
            is_active=True,
        )
        db.add(user)
        db.flush()

        db.add(
            UserRole(
                user_id=user.id,
                role_id=role.id,
                event_id=args.event_id,
                zone_id=args.zone_id,
            )
        )
        db.commit()

        scope = "global"
        if args.zone_id:
            scope = f"zone={args.zone_id}"
        elif args.event_id:
            scope = f"event={args.event_id}"

    print(f"Usuario {args.username!r} creado con rol {args.role} (alcance: {scope}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())