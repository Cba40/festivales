"""rbac: permisos de acciones de campo (alertas e incidentes)

Revision ID: d2a4b6c8e0f1
Revises: b8d9e0f1a2b3
Create Date: 2026-10-03

Por que esta migracion y no editar las anteriores
-------------------------------------------------
Porque `a7c8e9f0a1b2` y `b8d9e0f1a2b3` ya estan aplicadas. Editar su contenido
dejaria la base con un `alembic_version` que miente: el stamp diria revision nueva
sin que el DDL se haya ejecutado.

Que cambia y por que
-------------------
1. Se agregan `alerts:write` e `incidents:write`, que antes no existian.
2. OPERADOR_CAMPO los recibe, y PERDE `events:read`.
3. ANALISTA pierde `counts:write`.

Sobre el punto 2, la perdida de `events:read`
    Con `events:read` el operador habilitaba la pestaña de predicciones del motor,
    que es analisis y no carga de campo. Perderlo no le cierra ninguna pantalla que
    necesite: la de observaciones se abre con `observations:read`, que se conserva.

    `observations:read` NO se quita a proposito. Si se quitara, la tarjeta
    "Registrar Observacion" (que exige `observations:write`) llevaria a una
    pantalla sin permiso y el operador veria "No tenes permisos para ver ninguna
    seccion del motor". Leer lo que vas a editar es parte de poder editarlo.

Sobre el punto 3, la perdida de `counts:write` para ANALISTA
    ANALISTA es un rol de solo lectura: cargar conteos en el terreno es operacion de
    campo. Este permiso no lo exige ningun endpoint todavia, asi que la perdida es
    solo de permisos, no de funcionalidad.

Por que `alerts:write` / `incidents:write` y no `emergency:write`
-----------------------------------------------------------------
Porque `emergency:write` protege el CRUD de puntos de emergencia y ciudades
(`emergency_admin.py`), que es configuracion de infraestructura. Si las acciones de
campo colgaran de ese permiso, el operador ganaria crear y borrar puntos de
emergencia como efecto secundario de poder reportar un incidente. Son codigos
aparte, y `emergency:write` sigue siendo solo de quien administra.

Nota: estos permisos todavia no los exige ningun endpoint
--------------------------------------------------------
`alert_admin.py` y `operational_events.py` siguen con `verify_token`. Es decir: hoy
esto no cambia quien puede hacer QUE, cambia que ve y que puede hacer la UI, que es
justamente el alcance de este cambio. Los permisos quedan listos para cuando esos
endpoints pasen a `require_permission`.

Idempotente: `ON CONFLICT DO NOTHING` en las siembras.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd2a4b6c8e0f1'
down_revision: Union[str, Sequence[str], None] = 'b8d9e0f1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISSIONS = [
    ("alerts:write", "alerts", "write", "Publicar y gestionar alertas y mensajes al publico"),
    ("incidents:write", "incidents", "write", "Reportar y gestionar incidentes operativos"),
]

# (role_code, [permisos]). Refleja `ROLE_PERMISSIONS` de app/core/permissions.py.
ROLE_PERMISSIONS = {
    "SUPER_ADMIN": ["alerts:write", "incidents:write"],
    "MUNICIPAL_ADMIN": ["alerts:write", "incidents:write"],
    "OPERADOR_CAMPO": ["alerts:write", "incidents:write"],
    # ANALISTA no entra: es de solo lectura.
}

# (role_code, permiso) que se le SACA. Ver el docstring para el porque de cada uno.
REVOKED_PERMISSIONS = [
    ("OPERADOR_CAMPO", "events:read"),
    ("ANALISTA", "counts:write"),
]


def upgrade() -> None:
    import hashlib

    def stable_id(prefix: str, code: str) -> str:
        # Mismo esquema que `a7c8e9f0a1b2` y `b8d9e0f1a2b3`: id determinista para
        # que una re-aplicacion sea idempotente y el diff legible.
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

    # Las revocaciones van DESPUES de las siembras a proposito: si se ejecutaran
    # antes y un permiso ya no existiera en la base, el DELETE no haria nada y la
    # asignacion siguiente la volveria a dejar como estaba, sin avisar.
    for role_code, perm_code in REVOKED_PERMISSIONS:
        op.execute(
            sa.text(
                """
                DELETE FROM role_permissions
                WHERE role_id = (SELECT id FROM roles WHERE code = :role_code)
                  AND permission_id = (
                      SELECT id FROM permissions WHERE code = :perm_code
                  )
                """
            ).bindparams(role_code=role_code, perm_code=perm_code)
        )


def downgrade() -> None:
    # Se restituye lo que `upgrade` saco: un downgrade que deja al operador con
    # `events:read` de mas, o al analista con `counts:write`, no desharia el cambio.
    for role_code, perm_code in REVOKED_PERMISSIONS:
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

    # Solo se Quitan las asignaciones. El permiso en si se deja, por el mismo
    # motivo que en `b8d9e0f1a2b3`: borrarlo dejaria filas huerfanas en cualquier
    # rol que lo tuviera asignado y un `require_permission` sobre el volveria a dar
    # 403 para todo el mundo sin explicacion.
    for role_code, perm_codes in ROLE_PERMISSIONS.items():
        for perm_code in perm_codes:
            op.execute(
                sa.text(
                    """
                    DELETE FROM role_permissions
                    WHERE role_id = (SELECT id FROM roles WHERE code = :role_code)
                      AND permission_id = (
                          SELECT id FROM permissions WHERE code = :perm_code
                      )
                    """
                ).bindparams(role_code=role_code, perm_code=perm_code)
            )