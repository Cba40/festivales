"""rbac: permisos de protocolos de emergencia

Revision ID: b8d9e0f1a2b3
Revises: a7c8e9f0a1b2
Create Date: 2026-10-02

Por que una migracion nueva y no editar `a7c8e9f0a1b2`
-----------------------------------------------------
Porque esa ya esta aplicada. Editarla solo por cambiar el contenido del archivo
dejaria la base con un `alembic_version` que miente: el stamp diria revision nueva
sin que el DDL se haya ejecutado. Una migracion nueva es la unica forma de que el
estado en disco y el estado en la base coincidan.

Por que `emergency_protocols:*` y no reusar `protocols:*`
--------------------------------------------------------
`protocols:read` / `protocols:write` ya los usa el modulo de Protocolos de Control
de Observaciones. Los protocolos de emergencia son otro dominio (transversal por
`context`, no por `event_id`) y otro modulo. Compartir el prefijo haria que un
usuario con lectura de protocolos de observacion ganara automaticamente los de
emergencia, sin que nadie lo haya decidido.

Nota sobre `emergency_protocols:read` y los roles no admin
----------------------------------------------------------
El GET de `/api/admin/emergency-protocols` era publico. Este permiso se le da a
OPERADOR_CAMPO y ANALISTA justamente para que no pierdan un acceso que ya
tenian: la idea de least privilege es no otorgar mas de lo que ya se podia hacer,
no cerrar la puerta a lo que ya estaba abierta. El permiso `write` va solo a
SUPER_ADMIN y MUNICIPAL_ADMIN.

Idempotente: `ON CONFLICT DO NOTHING` en las siembras.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b8d9e0f1a2b3'
down_revision: Union[str, Sequence[str], None] = 'a7c8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISSIONS = [
    (
        "emergency_protocols:read",
        "emergency_protocols",
        "read",
        "Ver el catalogo de protocolos de emergencia",
    ),
    (
        "emergency_protocols:write",
        "emergency_protocols",
        "write",
        "Gestionar el catalogo de protocolos de emergencia",
    ),
]

# (role_code, [permisos]). Refleja `ROLE_PERMISSIONS` de app/core/permissions.py.
ROLE_PERMISSIONS = {
    "SUPER_ADMIN": ["emergency_protocols:read", "emergency_protocols:write"],
    "MUNICIPAL_ADMIN": ["emergency_protocols:read", "emergency_protocols:write"],
    "OPERADOR_CAMPO": ["emergency_protocols:read"],
    "ANALISTA": ["emergency_protocols:read"],
}


def upgrade() -> None:
    import hashlib

    def stable_id(prefix: str, code: str) -> str:
        # Mismo esquema que `a7c8e9f0a1b2`: id determinista para que una
        # re-aplicacion sea idempotente y el diff legible.
        h = hashlib.md5(f"{prefix}:{code}".encode("utf-8")).hexdigest()
        return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"

    for code, module, action, description in PERMISSIONS:
        op.execute(
            sa.text(
                """
                INSERT INTO permissions (id, code, module, action, description, is_system)
                VALUES (:id, :code, :module, :action, :description, true)
                ON CONFLICT (code) DO NOTHING
                """
            ).bindparams(
                id=stable_id("perm", code),
                code=code,
                module=module,
                action=action,
                description=description,
            )
        )

    for role_code, perm_codes in ROLE_PERMISSIONS.items():
        for perm_code in perm_codes:
            op.execute(
                sa.text(
                    """
                    INSERT INTO role_permissions (role_id, permission_id)
                    VALUES (
                        (SELECT id FROM roles WHERE code = :role_code),
                        (SELECT id FROM permissions WHERE code = :perm_code)
                    )
                    ON CONFLICT DO NOTHING
                    """
                ).bindparams(role_code=role_code, perm_code=perm_code)
            )


def downgrade() -> None:
    # Se quitan solo las asignaciones de estos permisos; el permiso en si se deja.
    # Borrarlo dejaria sin permiso a SUPER_ADMIN (cuyo `perms` es "*" en el token),
    # pero dejaria filas huerfanas en cualquier rol que lo tuviera asignado, y un
    # `require_permission("emergency_protocols:write")` volveria a dar 403 para todo
    # el mundo sin explicacion. Dejar el permiso es el estado seguro.
    for role_code in ROLE_PERMISSIONS:
        op.execute(
            sa.text(
                """
                DELETE FROM role_permissions
                WHERE role_id = (SELECT id FROM roles WHERE code = :role_code)
                  AND permission_id = (
                      SELECT id FROM permissions
                      WHERE code LIKE 'emergency_protocols:%'
                  )
                """
            ).bindparams(role_code=role_code)
        )