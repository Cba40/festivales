"""Gestión de usuarios del administrador municipal.

CRUD sobre la tabla ``users`` y sus asignaciones de ``user_roles``. Es la
interfaz que reemplaza tener que crear usuarios desde la consola con
``scripts/bootstrap_admin.py``, que sigue existiendo para el primer alta (cuando
todavía no hay ningún usuario con permisos para usar esta API).

Autorización
------------
- Lecturas: ``users:read``
- Escrituras: ``users:write``

El requerimiento original pedía un permiso único ``users:manage``. No se agregó
por dos razones: el catálogo ya tenía ``users:read`` / ``users:write`` desde la
Fase 1, y un tercer permiso que solapara con esos dos sería ambiguo (¿cuál
rige?) además de obligar a decidir a quién se le asignaba. Separar lectura de
escritura además es lo correcto: un rol que solo necesita ver la lista de usuarios
no debería poder darlos de baja.

Dos capas de seguridad
---------------------
Este módulo administra identidades, así que hay que blindar contra el
administrador que se sabotea a sí mismo por error:

1. **No se puede desactivar a uno mismo.** Es el error más fácil de cometer desde
   la UI y deja al municipio sin nadie con ``users:write``. Sale 409 con un
   mensaje que lo dice.
2. **No se puede quitar el propio `MUNICIPAL_ADMIN`.** Un admin que se lo quita
   puede dejar la instancia sin administradores. Se permite quitárselo a otro
   (el bootstrap empieza a necesitar otro admin), pero no a sí mismo.

Ninguno de los dos se resuelve en el frontend: son reglas de negocio del servidor,
porque un cliente alternativo o un `curl` los saltaría igual.

El password nunca sale
----------------------
``UserResponse`` no tiene campo de password ni ``password_hash``. Un ``GET`` de la
lista no puede filtrar hashes, que no son la contraseña pero alimentan el offline
cracking.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_permission
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import Role, User, UserRole
from app.schemas.user_admin import (
    RoleAssign,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserRoleResponse,
    UserUpdate,
)

router = APIRouter(prefix="/api/admin/users", tags=["User Admin"])

# El super admin del proveedor no se administra desde acá: no existe en `users`.
# Su cuenta se resuelve por variables de entorno (ver `app/api/routes/auth.py`), así
# que no hay fila que editar ni que dar de baja.
_NO_GESTIONABLE = "El usuario del proveedor se administra por variables de entorno."


def _get_or_404(db: Session, user_id: str) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


def _clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _username_taken(db: Session, username: str, exclude_id: Optional[str] = None) -> bool:
    query = db.execute(
        select(User.id).where(User.username == username)
    ).scalar_one_or_none()
    if query is None:
        return False
    return query != exclude_id


def _role_or_404(db: Session, code: str) -> Role:
    role = db.execute(
        select(Role).where(Role.code == code)
    ).scalar_one_or_none()
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rol desconocido: {code}",
        )
    return role


def _to_response(user: User) -> UserResponse:
    """Arma la respuesta. Es la UNICA función que decide qué sale de un usuario.

    Construir la respuesta aca y no devolver el modelo es lo que garantiza que
    `password_hash` no se salga por accidente. Si en el futuro alguien agrega un
    campo sensible al modelo, esta función lo ignora salvo que lo agregue a
    propósito.
    """
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        locked_until=user.locked_until,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        roles=[
            UserRoleResponse(
                role_id=ur.role_id,
                role_code=ur.role.code if ur.role else "",
                role_name=ur.role.name if ur.role else "",
                event_id=ur.event_id,
                zone_id=ur.zone_id,
                granted_at=ur.granted_at,
            )
            for ur in user.user_roles
            if ur.role is not None
        ],
    )


def _load(db: Session, user_id: str) -> User:
    """Carga el usuario con sus roles resueltos (evita N+1 al serializar)."""
    from sqlalchemy.orm import selectinload

    return db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
    ).scalar_one()


@router.get("", response_model=UserListResponse)
@router.get("/", response_model=UserListResponse, include_in_schema=False)
def list_users(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _=Depends(require_permission("users:read")),
):
    """Lista usuarios con sus roles y alcance.

    `include_inactive` está off por defecto: la pantalla de gestión arranca
    mostrando solowho puede entrar al sistema.
    """
    from sqlalchemy.orm import selectinload

    query = select(User).options(
        selectinload(User.user_roles).selectinload(UserRole.role)
    )
    if not include_inactive:
        query = query.where(User.is_active.is_(True))
    users = db.execute(query.order_by(User.username)).scalars().all()
    return UserListResponse(
        total=len(users), users=[_to_response(u) for u in users]
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permission("users:write")),
):
    username = body.username.strip()
    if not username:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username must not be empty",
        )
    if _username_taken(db, username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese nombre",
        )

    role = _role_or_404(db, body.role)

    user = User(
        username=username,
        email=_clean(body.email),
        full_name=_clean(body.full_name),
        # argon2 antes de tocar la base: la contraseña en claro no llega a disco.
        password_hash=hash_password(body.password),
        is_active=body.is_active,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    return _to_response(_load(db, user.id))


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    body: UserUpdate,
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(require_permission("users:write")),
):
    """Edita un usuario.

    `password` es opcional: si no viene, la contraseña no se toca. Manda una
    siempre re-hashearía al usuario con una contraseña que nunca eligió.
    """
    user = _get_or_404(db, user_id)

    # ── No desactivarse a sí mismo ──
    #
    # Es el error más fácil de cometer desde la UI y deja al municipio sin nadie
    # con `users:write`. Se compara por id, no por username: dos personas podrían
    # tener el mismo username en bases distintas y la comparación por string
    # banalizaría la protección.
    if body.is_active is False and user.id == actor.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No podés desactivar tu propia cuenta: dejarías al municipio "
            "sin nadie que pueda gestionar usuarios.",
        )

    if body.password:
        user.password_hash = hash_password(body.password)
        # Una contraseña nueva reinicia el lockout: si alguien estaba bloqueado por
        # intentos fallidos y el admin le restablece la clave, sigue bloqueado sin
        # motivo.
        user.failed_login_count = 0
        user.locked_until = None

    if body.email is not None:
        user.email = _clean(body.email)
    if body.full_name is not None:
        user.full_name = _clean(body.full_name)
    if body.is_active is not None:
        user.is_active = body.is_active

    db.commit()
    return _to_response(_load(db, user.id))


@router.delete("/{user_id}", response_model=UserResponse)
def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(require_permission("users:write")),
):
    """Soft delete: `is_active=False`.

    No borra la fila. Los refresh tokens y el `audit_log` la referencian, y un
    `DELETE` duro dejaría filas huérfanas y un `audit_log` que ya no dice quién
    obró. Desactivar además es reversible desde `PUT`, que un borrado no es.
    """
    user = _get_or_404(db, user_id)

    if user.id == actor.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No podés desactivar tu propia cuenta: dejarías al municipio "
            "sin nadie que pueda gestionar usuarios.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario ya está desactivado.",
        )

    user.is_active = False
    db.commit()
    return _to_response(_load(db, user.id))


@router.post("/{user_id}/roles", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def assign_role(
    user_id: str,
    body: RoleAssign,
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(require_permission("users:write")),
):
    """Asigna un rol, opcionalmente acotado a un evento o una zona."""
    user = _get_or_404(db, user_id)
    role = _role_or_404(db, body.role_code)

    # La PK de `user_roles` es `(user_id, role_id)`: un usuario tiene cada rol, como
    # mucho, UNA vez. No hay forma de asignar el mismo rol con dos alcances
    # distintos, porque la segunda fila choca con la clave primaria.
    #
    # La primera versión de esta ruta chequeaba el scope también y devolvía 500 con
    # `UniqueViolation` en ese caso. Ahora el 409 explica la restricción, que es lo
    # que el operador necesita para entender qué hacer.
    existing = db.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role.id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        alcance = (
            f"evento {existing.event_id}" if existing.event_id
            else f"zona {existing.zone_id}" if existing.zone_id
            else "toda la municipalidad"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"El usuario ya tiene el rol {role.code}, con alcance: {alcance}. "
                "Un usuario tiene cada rol una sola vez; para cambiarle el alcance "
                "quitalo primero y volvé a asignarlo."
            ),
        )

    db.add(
        UserRole(
            user_id=user_id,
            role_id=role.id,
            event_id=body.event_id,
            zone_id=body.zone_id,
            granted_by=actor.id,
        )
    )
    db.commit()
    return _to_response(_load(db, user_id))


@router.delete("/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_role(
    user_id: str,
    role_id: str,
    db: Session = Depends(get_db),
    actor: CurrentUser = Depends(require_permission("users:write")),
):
    """Quita un rol. Se permite el último rol de otro, no el propio.

    El super admin del proveedor no depende de ninguna fila de `users`, así que
    quedarse sin roles lo deja sin acceso: es exactamente el caso que este módulo
    no puede dejar pasar.
    """
    user = _get_or_404(db, user_id)
    assignment = db.execute(
        select(UserRole)
        .where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    ).scalar_one_or_none()
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no tiene ese rol.",
        )

    if (
        user.id == actor.id
        and assignment.role_id == role_id
        and not user.is_superuser
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No podés quitarte tu propio rol: te quedarías sin acceso al "
            "sistema.",
        )

    db.delete(assignment)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)