"""Identidad: usuarios, roles, permisos y sus asignaciones.

Qué modela
----------
El sistema se despliega como **una instancia por municipalidad**, no multi-tenant.
Eso tiene una consecuencia de diseño importante: la identidad vive íntegramente en
la base del cliente, y por eso el super admin (nosotros/proveedor) **no** es una
fila acá sino un camino de login aparte, resuelto por variables de entorno y
firmado con una clave distinta. Ver `app/api/routes/auth.py`.

Si el super admin fuera una fila de `users`, un administrador municipal con
`users:manage` podría leer la tabla, verse el rol y auto-asignárselo. La
separación no es decorativa: es lo que impide que el cliente nos escale.

`Role.is_system` marca los roles base (los que siembra la migración) para que
la UI no permita borrarlos ni renombrarlos: son el contrato del código.

`UserRole` lleva el **scope** (`event_id` / `zone_id` opcionales) en la
asignación, no en el rol. Así un operador de campo acotado a su zona no necesita un
rol distinto por zona, y "veo el conteo de vehículos" y "veo el conteo de personas"
son dos asignaciones del mismo rol.

`Permission.code` es un string `module:action`. Se eligió string y no una
tabla de permisos por fila con dependencias porque el control de acceso real del
sistema es "este endpoint me corresponde", no "qué acción puedo hacer sobre qué
entidad".
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class User(Base):
    """Persona con acceso al sistema. Tabla `users`."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    username: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    email: Mapped[Optional[str]] = mapped_column(String(254), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Hash argon2id. Nunca la contraseña en claro. El formato de argon2 incluye sus
    # propios parámetros (m, t, p  salt) en el string, así que subir el coste
    # no invalida los hashes existentes: cada verificación usa los del hash que
    # encuentra.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true", default=True
    )
    # Capacidad interna del código (seed inicial y escape de emergencia), NO un
    # permiso asignable: no existe ningún `superuser` en `UserRole`, así que no
    # se puede otorgar desde la UI. Queda para el recovery de un administrador
    # municipal que se queda sin nadie con `users:manage`.
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )

    # Lockout por intentos fallidos. `locked_until` en el futuro bloquea el
    # login aunque la contraseña sea correcta.
    failed_login_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", default=0
    )
    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # `foreign_keys` es obligatorio, no cosmético: `user_roles` tiene DOS FKs a
    # `users` (`user_id` y `granted_by`). Sin esto SQLAlchemy no puede decidir
    # cuál une las tablas y revienta con `AmbiguousForeignKeysError` al primer
    # `db.add(User(...))`. Ver también `UserRole.granted_by` más abajo, que tiene
    # el problema espejo.
    user_roles: Mapped[list["UserRole"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="UserRole.user_id",
    )

    __table_args__ = (
        CheckConstraint("failed_login_count >= 0", name="ck_users_failed_login_count"),
        Index("ix_users_is_active", "is_active"),
    )


class Role(Base):
    """Rol de sistema. Tabla `roles`."""

    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Código estable en MAYÚSCULAS: es lo que viaja en el JWT y lo que escriben
    # las dependencias (`require_role("MUNICIPAL_ADMIN")`). Cambiar un código
    # invalida los tokens emitidos y las asignaciones.
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Los roles del sistema los siembra la migración. La UI de gestión de roles
    # los muestra pero no los deja borrar ni renombrar: el código los referencia
    # por `code`, así que borrarlos rompería el control de acceso.
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    role_permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="role", cascade="all, delete-orphan", lazy="selectin"
    )
    user_roles: Mapped[list["UserRole"]] = relationship(back_populates="role")

    __table_args__ = (
        CheckConstraint("code = upper(code)", name="ck_roles_code_upper"),
    )


class Permission(Base):
    """Permiso atómico. Tabla `permissions`."""

    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Formato obligatorio `module:action`, p. ej. `observations:write`.
    # Lo parsea `require_permission` en app/api/deps.py.
    code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    # Descomposición de `code`, materializada para poder filtrar por módulo en la
    # UI ("todos los permisos de observations") sin parsear strings en SQL.
    module: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true", default=True
    )

    role_permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="permission", lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint("position(':' in code) > 0", name="ck_permissions_code_has_colon"),
        Index("ix_permissions_module", "module"),
    )


class UserRole(Base):
    """Asignación de un rol a un usuario, con scope opcional. `user_roles`."""

    __tablename__ = "user_roles"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )

    # Scope. `NULL` en ambos = alcance global (lo ve todo). Con `event_id` = solo
    # ese evento. Con `zone_id` = solo esa zona. La resolución de permisos en
    # `deps.py` combina todos los scopes del usuario.
    event_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    zone_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    granted_by: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relación del `user_id` de la asignación. El `foreign_keys` explícito es
    # necesario por la ambigüedad que introduce `granted_by`, que también apunta a
    # `users.id`.
    user: Mapped["User"] = relationship(
        back_populates="user_roles", foreign_keys=[user_id]
    )
    role: Mapped["Role"] = relationship(back_populates="user_roles", lazy="selectin")
    # Quién asignó el rol. `SET NULL` en la BD: si se borra el administrador que dio
    # el alta, la asignación sobrevive y queda sin autor conocido.
    granted_by_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[granted_by], remote_side="User.id"
    )

    __table_args__ = (
        # Evita duplicar el mismo rol con alcance global. Sin este índice, la PK
        # compuesta (user_id, role_id) igual lo impediría; el índice parcial
        # documenta la intención y cubre las consultas de scope global.
        Index("ix_user_roles_user_id", "user_id"),
        Index("ix_user_roles_zone_id", "zone_id"),
        Index("ix_user_roles_event_id", "event_id"),
    )


class RolePermission(Base):
    """Permisos de un rol. Tabla `role_permissions`."""

    __tablename__ = "role_permissions"

    role_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )

    role: Mapped["Role"] = relationship(back_populates="role_permissions")
    permission: Mapped["Permission"] = relationship(
        back_populates="role_permissions", lazy="selectin"
    )


class RefreshToken(Base):
    """Refresh tokens emitidos. Tabla `refresh_tokens`.

    Es lo que hace que el logout sea real. Un access token es un JWT
    autocontenido que no se puede revocar (cualquiera que lo tenga lo valida hasta
    que expira), así que la sesión se sostiene en el refresh: este se guarda
    hasheado —nunca en claro, por si alguien lee la tabla o un backup— y el
    logout marca `revoked_at`.
    """

    __tablename__ = "refresh_tokens"

    # El `jti` del JWT. Es clave primaria y también lo que viaja en el token, así
    # que revocar es un UPDATE por `jti`.
    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # SHA-256 del token completo. Guardar el hash y no el token significa que una
    # filtración de la tabla o de un backup no permite suplantar sesiones.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Rotación: al refrescar, el refresh viejo se revoca y se emite uno nuevo.
    # `replaced_by_jti` deja la cadena de una sesión completa.
    replaced_by_jti: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_expires_at", "expires_at"),
    )


class AuditLog(Base):
    """Bitácora de operaciones. Tabla `audit_log`.

    `actor_username` y `actor_roles` van desnormalizados a propósito: si el usuario
    se borra o se le cambia el rol, la fila tiene que seguir diciendo quién y con
    qué permisos obró en su momento. Una bitácora que se reescribe sola con el
    usuario no sirve para investigar.

    Escritura-only desde la API: no hay endpoint de update ni de delete. Se
    depura por retención (una tarea programada), no desde la app.
    """

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # NULL cuando el actor es el super admin del proveedor: no existe en `users`.
    actor_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_username: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    actor_roles: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # "auth.login", "users.update", "observations.create"...
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    event_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    # Estado antes y después. Solo se llena en operaciones de escritura.
    before: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    after: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_audit_log_created_at", "created_at"),
        Index("ix_audit_log_actor_user_id", "actor_user_id"),
        Index("ix_audit_log_action", "action"),
    )