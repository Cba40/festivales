"""rbac: users, roles, permissions, refresh_tokens y audit_log

Revision ID: a7c8e9f0a1b2
Revises: e1f2a3b4c5
Create Date: 2026-10-02

Identidad y control de acceso (RBAC), Fase 1.

Por que el super admin NO es una fila de `users`
-----------------------------------------------
El sistema se despliega como una instancia por municipalidad, no multi-tenant. Si
la cuenta del proveedor fuera una fila de `users`, un administrador municipal con
permiso `users:manage` podría leer la tabla, verse el rol SUPER_ADMIN y
auto-asignárselo. Por eso esa cuenta se resuelve en el login contra variables de
entorno (`SUPER_ADMIN_USERNAMES`) y su token se firma con una clave distinta
(`PROVIDER_TOKEN_SECRET`). Ninguna de las dos vive en esta base.

Por que el scope va en `user_roles` y no en `roles`
----------------------------------------------------
Un operador de campo acotado a su zona no necesita un rol distinto por zona: es la
MISMA asignación de rol con `zone_id` distinta. Con el scope en el rol habría que
multiplicar roles por zonas.

Idempotencia
------------
Todos los `CREATE TABLE` usan `IF NOT EXISTS` y todas las siembras de catálogo van
con `ON CONFLICT DO NOTHING`, para que la migración sea aplicable sobre una base
que ya tuviera alguna de estas tablas y no rompa un despliegue parcial.

`roles` y `permissions` quedan sembradas con `is_system=true`: son el contrato que
el código referencia por `code`/`code`, y la UI no debe poder borrarlas.

No se crea ningún usuario. El primer usuario real lo crea el super admin desde la
UI de gestión, o el seed de bootstrap si se opta por esa vía.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = 'a7c8e9f0a1b2'
down_revision: Union[str, Sequence[str], None] = 'e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Catálogo de roles y permisos ─────────────────────────────────────────────
#
# Los códigos son el contrato entre el código y la base: `require_role("...")` y
# `require_permission("...")` los escriben literalmente. Cambiar uno deja endpoints
# sin acceso, así que van como constantes en el código y acá se siembran con los
# mismos valores.

ROLES = [
    (
        "SUPER_ADMIN",
        "Super Administrador (proveedor)",
        "Acceso total. Se resuelve por variables de entorno, NO es una fila de "
        "users: no existe en esta base.",
    ),
    (
        "MUNICIPAL_ADMIN",
        "Administrador Municipal",
        "Gestiona usuarios, eventos, configuraciones locales y reportes de su "
        "jurisdiccion.",
    ),
    (
        "OPERADOR_CAMPO",
        "Operador de Campo",
        "Carga de datos y visualizacion acotada a su zona. Sin reportes globales "
        "ni configuracion.",
    ),
    (
        "ANALISTA",
        "Analista",
        "Lectura de datos y reportes. Sin escritura de configuracion.",
    ),
]

# (code, module, action, description)
PERMISSIONS = [
    # --- Identidad -----------------------------------------------------------
    ("users:read", "users", "read", "Ver usuarios y sus roles"),
    ("users:write", "users", "write", "Crear y editar usuarios y asignaciones de rol"),
    ("roles:read", "roles", "read", "Ver roles y permisos"),
    ("audit:read", "audit", "read", "Leer la bitacora de operaciones"),
    # --- Eventos -------------------------------------------------------------
    ("events:read", "events", "read", "Ver eventos, jornadas y zonas"),
    ("events:write", "events", "write", "Crear y editar eventos, jornadas y zonas"),
    # --- Operacion en campo --------------------------------------------------
    ("observations:read", "observations", "read", "Ver observaciones"),
    ("observations:write", "observations", "write", "Registrar y editar observaciones"),
    ("counts:write", "counts", "write", "Cargar conteos de personas y vehiculos"),
    # --- Configuracion -------------------------------------------------------
    ("config:read", "config", "read", "Ver configuracion operativa"),
    ("config:write", "config", "write", "Editar configuracion operativa"),
    ("protocols:read", "protocols", "read", "Ver protocolos de control ySugerencias"),
    ("protocols:write", "protocols", "write", "Gestionar protocolos de control"),
    ("emergency:read", "emergency", "read", "Ver emergencias y protocolos"),
    ("emergency:write", "emergency", "write", "Gestionar emergencias y protocolos"),
    # --- Analisis ------------------------------------------------------------
    ("reports:read", "reports", "read", "Ver reportes globales"),
    ("analytics:read", "analytics", "read", "Ver analytics y recomendaciones"),
    ("analytics:write", "analytics", "write", "Resolver recomendaciones"),
    ("audit_log:read", "audit_log", "read", "Ver la bitacora de recomendaciones"),
]

# (role_code, [permission_codes])
ROLE_PERMISSIONS = {
    "SUPER_ADMIN": [c for c, _m, _a, _d in PERMISSIONS],
    "MUNICIPAL_ADMIN": [
        "users:read", "users:write", "roles:read", "audit:read",
        "events:read", "events:write",
        "observations:read", "observations:write", "counts:write",
        "config:read", "config:write",
        "protocols:read", "protocols:write",
        "emergency:read", "emergency:write",
        "reports:read", "analytics:read", "analytics:write", "audit_log:read",
    ],
    "OPERADOR_CAMPO": [
        "events:read",
        "observations:read", "observations:write",
        "counts:write",
        "emergency:read",
    ],
    "ANALISTA": [
        "events:read", "observations:read", "counts:write",
        "reports:read", "analytics:read", "audit_log:read",
        "protocols:read", "emergency:read",
    ],
}


def upgrade() -> None:
    # ── users ────────────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id varchar(36) PRIMARY KEY,
            username varchar(150) NOT NULL UNIQUE,
            email varchar(254),
            full_name varchar(200),
            password_hash varchar(255) NOT NULL,
            is_active boolean NOT NULL DEFAULT true,
            is_superuser boolean NOT NULL DEFAULT false,
            failed_login_count integer NOT NULL DEFAULT 0,
            locked_until timestamptz,
            last_login_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT ck_users_failed_login_count CHECK (failed_login_count >= 0)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_is_active ON users (is_active)")

    # ── roles ────────────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS roles (
            id varchar(36) PRIMARY KEY,
            code varchar(50) NOT NULL UNIQUE,
            name varchar(100) NOT NULL,
            description text,
            is_system boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT ck_roles_code_upper CHECK (code = upper(code))
        )
        """
    )

    # ── permissions ──────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS permissions (
            id varchar(36) PRIMARY KEY,
            code varchar(80) NOT NULL UNIQUE,
            module varchar(50) NOT NULL,
            action varchar(30) NOT NULL,
            description text,
            is_system boolean NOT NULL DEFAULT true,
            CONSTRAINT ck_permissions_code_has_colon
                CHECK (position(':' in code) > 0)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_permissions_module ON permissions (module)"
    )

    # ── role_permissions ─────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id varchar(36) NOT NULL
                REFERENCES roles (id) ON DELETE CASCADE,
            permission_id varchar(36) NOT NULL
                REFERENCES permissions (id) ON DELETE CASCADE,
            PRIMARY KEY (role_id, permission_id)
        )
        """
    )

    # ── user_roles ───────────────────────────────────────────────────────────
    # El scope (event_id / zone_id) va acá, no en `roles`: ver el docstring.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id varchar(36) NOT NULL
                REFERENCES users (id) ON DELETE CASCADE,
            role_id varchar(36) NOT NULL
                REFERENCES roles (id) ON DELETE CASCADE,
            event_id varchar(36),
            zone_id varchar(36),
            granted_by varchar(36) REFERENCES users (id) ON DELETE SET NULL,
            granted_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, role_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_roles_user_id ON user_roles (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_roles_zone_id ON user_roles (zone_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_roles_event_id ON user_roles (event_id)")

    # ── refresh_tokens ───────────────────────────────────────────────────────
    # Se guarda el SHA-256 del token, nunca el token: una filtración de la tabla
    # o de un backup no debe permitir suplantar sesiones.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            jti varchar(36) PRIMARY KEY,
            user_id varchar(36) NOT NULL
                REFERENCES users (id) ON DELETE CASCADE,
            token_hash varchar(64) NOT NULL,
            expires_at timestamptz NOT NULL,
            revoked_at timestamptz,
            replaced_by_jti varchar(36),
            ip varchar(45),
            user_agent varchar(300),
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_refresh_tokens_expires_at ON refresh_tokens (expires_at)"
    )

    # ── audit_log ────────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id varchar(36) PRIMARY KEY,
            actor_user_id varchar(36) REFERENCES users (id) ON DELETE SET NULL,
            actor_username varchar(150),
            actor_roles JSONB,
            action varchar(80) NOT NULL,
            resource_type varchar(60),
            resource_id varchar(36),
            event_id varchar(36),
            ip varchar(45),
            user_agent varchar(300),
            before JSONB,
            after JSONB,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_created_at ON audit_log (created_at)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_log_actor_user_id ON audit_log (actor_user_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_log_action ON audit_log (action)")

    # ── Siembra del catálogo ─────────────────────────────────────────────────
    # IDs deterministas (no aleatorios) para que la siembra sea reproducible y el
    # diff de una re-aplicación sea legible. Se generan de forma determinista con
    # md5 del código, recortado a 36 chars y con guiones como UUID.
    import hashlib

    def stable_id(prefix: str, code: str) -> str:
        h = hashlib.md5(f"{prefix}:{code}".encode("utf-8")).hexdigest()
        return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"

    for code, name, description in ROLES:
        op.execute(
            sa.text(
                """
                INSERT INTO roles (id, code, name, description, is_system)
                VALUES (:id, :code, :name, :description, true)
                ON CONFLICT (code) DO NOTHING
                """
            ).bindparams(
                id=stable_id("role", code),
                code=code,
                name=name,
                description=description,
            )
        )

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
    # Al revés del upgrade. Las tablas se borran en orden de dependencia para que
    # las FK no bloqueen el DROP.
    op.execute("DROP TABLE IF EXISTS audit_log")
    op.execute("DROP TABLE IF EXISTS refresh_tokens")
    op.execute("DROP TABLE IF EXISTS user_roles")
    op.execute("DROP TABLE IF EXISTS role_permissions")
    op.execute("DROP TABLE IF EXISTS permissions")
    op.execute("DROP TABLE IF EXISTS roles")
    op.execute("DROP TABLE IF EXISTS users")