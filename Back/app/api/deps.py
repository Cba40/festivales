# backend/app/api/deps.py
"""Autenticación y autorización de requests.

Qué cambió respecto de antes
---------------------------
Antes había una sola pieza, `verify_token`, que comprobaba que el JWT tuviera firma
válida y un `sub`. Eso es un booleano: "hay alguien adentro". No distinguía a un
administrador municipal de un contador de campo, así que ambos podían tocar lo
mismo. Ahora hay tres:

- `get_current_user`  resuelve el actor: quién es, qué roles tiene, qué permisos
  resueltos y con qué alcance (scope).
- `require_permission("module:action")`  la dependencia que se usa en endpoints.
  Es la que se quiere por defecto.
- `require_role("CODIGO")`  envoltorio de conveniencia para chequeos gruesos.

Por qué se consulta la base en cada request, si los permisos ya viajan en el token
--------------------------------------------------------------------------------
Porque el token es una foto. Si el acceso vive solo en sus claims, desactivar un
usuario (`is_active=false`) o quitarle un rol tarda en tener efecto: hasta que
expire el access, 15 minutos. Consultar `users` + `user_roles` + `permissions` en
cada request hace la revocación inmediata, que es la diferencia entre "dar de baja
a alguien" y "dar de baja a alguien dentro de 15 minutos".

El costo es una consulta por request. El endpoint ya consulta la base de todos
modos, así que es un caché de primer nivel con los datos que ya se están trayendo.

Los claims `roles`/`perms` del token no se ignoran: son la única fuente para el
super admin del proveedor, que por diseño no existe en `users`.
"""
from __future__ import annotations

from typing import Callable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.permissions import SUPER_PERMISSION_WILDCARD, parse_permission
from app.core.security import TokenError, decode_token
from app.db.session import get_db
from app.models.user import Role, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# Errores. 401 = no sé quién sos (o el token no sirve). 403 = sé quién sos pero no
# te alcanza. La distinción importa: un 403 confirma que la cuenta existe, y en un
# login además permite que la UI diga "no tenés permisos" en vez de "revisá tu
# contraseña".
_CREDENTIALS_HEADERS = {"WWW-Authenticate": "Bearer"}


class TokenPayload(BaseModel):
    """Claims crudos del JWT. Se mantiene por compatibilidad."""

    sub: Optional[str] = None


class CurrentUser(BaseModel):
    """Actor autenticado, ya resuelto."""

    # `None` para el super admin del proveedor: no existe en `users`.
    id: Optional[str] = None
    username: str
    # Nombre y apellido, si el usuario los cargo. Informativo: la identidad la
    # define `username`. `None` para el super admin del proveedor y para cualquiera
    # que no lo haya completado.
    full_name: Optional[str] = None
    # Rol `SUPER_ADMIN` del proveedor. Viene del token, no de la base.
    is_provider_super_admin: bool = False
    is_superuser: bool = False
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    # Alcance. `event_id=None, zone_id=None` en todas las asignaciones = global.
    # Un operador acotado tiene al menos una asignación con `zone_id`.
    scopes: list[dict[str, Optional[str]]] = Field(default_factory=list)

    def has_permission(self, code: str) -> bool:
        # `is_superuser` es la capacidad de emergencia del seed, no un rol
        # asignable. Salta ambas chequeras por la misma razon: si solo pasara
        # `require_permission` y fallara `require_role`, un endpoint protegido con
        # `require_role` le negaria el acceso al superusuario, que es el
        # contrario de lo que se quiere.
        if self.is_provider_super_admin or self.is_superuser:
            return True
        return SUPER_PERMISSION_WILDCARD in self.permissions or code in self.permissions

    def has_role(self, code: str) -> bool:
        if self.is_provider_super_admin or self.is_superuser:
            return True
        return code in self.roles

    @property
    def is_global_scope(self) -> bool:
        """True si el usuario no tiene scope acotado en ninguna asignación."""
        return not self.scopes or all(
            s.get("event_id") is None and s.get("zone_id") is None for s in self.scopes
        )


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers=_CREDENTIALS_HEADERS,
    )


def _load_user_from_db(db: Session, username: str) -> Optional[CurrentUser]:
    """Arma el `CurrentUser` desde la base, o `None` si no existe o está inactivo.

    `None` tanto para usuario inexistente como para desactivado: para un endpoint
   protected da igual, ambos son 401. La diferencia solo importa en el login, que
    distingue los dos casos para poder escribir el bitácora sin filtrarle al
    atacante el padrón de usernames existentes.
    """
    from sqlalchemy.orm import selectinload

    from app.models.user import Role, User, UserRole

    # La cadena arranca en `User.user_roles`: `selectinload` necesita el camino
    # completo desde la entidad raíz de la query, no un atributo suelto.
    user = db.execute(
        select(User)
        .where(User.username == username)
        .options(
            selectinload(User.user_roles)
            .selectinload(UserRole.role)
            .selectinload(Role.role_permissions)
        )
    ).scalar_one_or_none()

    if user is None or not user.is_active:
        return None

    roles: list[str] = []
    permissions: list[str] = []
    scopes: list[dict[str, Optional[str]]] = []

    for ur in user.user_roles:
        role = ur.role
        if role is None:
            continue
        roles.append(role.code)
        scopes.append({"event_id": ur.event_id, "zone_id": ur.zone_id})
        for rp in role.role_permissions:
            if rp.permission is not None:
                permissions.append(rp.permission.code)

    return CurrentUser(
        id=user.id,
        username=user.username,
        # Solo para mostrar. La identidad real la decide `username` + `id`; esto
        # evita que la UI tenga que inventar un nombre o mostrar un UUID. Es
        # None cuando el usuario no lo cargo, y la UI cae al username.
        full_name=user.full_name,
        # `is_superuser` es la capacidad de emergencia del seed. No es un rol
        # asignable, así que nunca aparece en `user_roles` ni se puede otorgar
        # desde la UI.
        is_superuser=user.is_superuser,
        roles=sorted(set(roles)),
        permissions=sorted(set(permissions)),
        scopes=scopes,
    )


def verify_token(token: Optional[str] = Depends(oauth2_scheme)) -> TokenPayload:
    """Solo valida el token. Se conserva para endpoints sin política de permiso.

    Preferí `get_current_user` o, mejor, `require_permission`. Quedarse en
    `verify_token` significa "cualquier usuario autenticado", que es exactamente el
    problema que el RBAC viene a resolver.
    """
    if token is None:
        raise _unauthorized()
    try:
        claims = decode_token(token)
    except (TokenError, JWTError) as exc:
        raise _unauthorized("Invalid token") from exc
    username = claims.get("sub")
    if not username:
        raise _unauthorized("Invalid token")
    return TokenPayload(sub=username)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """Resuelve el actor autenticado.

    Tres caminos, en este orden:

    1. El token fue firmado con `PROVIDER_TOKEN_SECRET`: es el super admin del
       proveedor. No se busca en la base (no existe ahí, a propósito) y se acepta
       el comodín de permisos del propio token.
    2. Token normal: se busca el usuario en la base y se resuelven roles y
       permisos desde ahí, para que una baja o un cambio de rol surtan efecto de
    inmediato.
    3. Sin token o inválido: 401.
    """
    if token is None:
        raise _unauthorized()

    # ── 1) Super admin del proveedor ──
    #
    # Se prueba con la clave del proveedor. Si el token no valida con ella se sigue
    # por el camino normal: un usuario de la municipalidad no tiene por qué probar
    # contra esta clave en cada request.
    if settings.PROVIDER_TOKEN_SECRET:
        try:
            provider_claims = decode_token(
                token, secret=settings.PROVIDER_TOKEN_SECRET
            )
        except (TokenError, JWTError):
            provider_claims = None
        if provider_claims is not None:
            username = provider_claims.get("sub")
            if not username:
                raise _unauthorized("Invalid token")
            return CurrentUser(
                id=None,
                username=username,
                is_provider_super_admin=True,
                roles=list(provider_claims.get("roles") or ["SUPER_ADMIN"]),
                permissions=[SUPER_PERMISSION_WILDCARD],
                scopes=[],
            )

    # ── 2) Usuario de la municipalidad ──
    try:
        claims = decode_token(token)
    except (TokenError, JWTError) as exc:
        raise _unauthorized("Invalid token") from exc

    username = claims.get("sub")
    if not username:
        raise _unauthorized("Invalid token")

    # Un token válido de un usuario dado de baja o desactivado cae acá: el token
    # en sí es válido, la cuenta ya no existe para el sistema.
    current = _load_user_from_db(db, username)
    if current is None:
        raise _unauthorized("Invalid token")

    return current


def require_permission(code: str) -> Callable:
    """Dependencia que exige el permiso `code` (formato `module:action`).

    Es la dependencia de autorización por defecto. Un endpoint que solo pone
    `verify_token` significa "cualquier usuario autenticado"; uno que pone
    `require_permission("observations:write")` significa exactamente eso.

    El super admin del proveedor pasa siempre.
    """
    # Fallar al importar el módulo y no en el primer request: un typo en el código
    # de permiso debe romper los tests, no aparecer como 403 en producción.
    parse_permission(code)

    def dependency(
        current: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not current.has_permission(code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso requerido: {code}",
            )
        return current

    dependency.__name__ = f"require_{code.replace(':', '_')}"
    return dependency


def require_role(code: str) -> Callable:
    """Dependencia que exige el rol `code`.

    Menor granularidad que `require_permission` y más frágil: si mañana se agrega
    un rol nuevo, este chequeo no lo contempla. Se reserva para decisiones de
    negocio ("solo el administrador municipal puede eliminar un evento"), no para
    proteger endpoints.
    """

    def dependency(
        current: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not current.has_role(code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol requerido: {code}",
            )
        return current

    dependency.__name__ = f"require_role_{code.lower()}"
    return dependency


def require_any_permission(*codes: str) -> Callable:
    """Dependencia que exige al menos uno de los permisos indicados."""

    for code in codes:
        parse_permission(code)

    def dependency(
        current: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if not any(current.has_permission(code) for code in codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso requerido (uno de): {', '.join(codes)}",
            )
        return current

    dependency.__name__ = "require_any_permission"
    return dependency