# backend/app/api/routes/auth.py
"""Autenticación: login, refresh, logout y me.

Reemplaza el login anterior, que comparaba `username == "admin" and password ==
"1234"` en memoria. Ahora hay usuarios reales en la tabla `users`, contraseñas
argon2 y un camino aparte para el super admin del proveedor.

El super admin no vive en la base
---------------------------------
La cuenta del proveedor se resuelve contra `settings.SUPER_ADMIN_USERNAMES` y su
token se firma con `settings.PROVIDER_TOKEN_SECRET`. No hay fila en `users`.

Por qué: la base es del cliente. Si nuestra cuenta fuera una fila, el
administrador municipal con permiso `users:manage` podría leer `users`, ver el
rol SUPER_ADMIN y auto-asignárselo. Con este diseño la cuenta no existe en su lado:
no se puede listar, ni ver, ni revocar, ni duplicar. Es la razón de que
`PROVIDER_TOKEN_SECRET` tenga que ser distinta de `SECRET_KEY` (lo valida
`Settings`), porque si compartieran clave el mismo endpoint de login emitiría
tokens de proveedor a partir de credenciales de usuarios.

Login: dos caminos, un mismo contrato
-------------------------------------
1. Si el username está en `SUPER_ADMIN_USERNAMES`, se compara contra la clave del
   proveedor. La contraseña es `PROVIDER_TOKEN_SECRET` en sí (no hay hash que
   verificar).
2. Si no, se busca en `users` y se verifica el hash argon2.

Ambos emiten el mismo `LoginResponse`, para que el frontend no sepa cuál es cuál.

Sobre el timing
---------------
Un usuario inexistente iguala el costo con `dummy_verify()`, y el usuario
inexistente y el password incorrecto devuelven el mismo 401 con el mismo texto.
Si el tiempo de respuesta distinguiera "existe" de "no existe", se podría enumerar
el padrón de usuarios sin crackear nada.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.infrastructure.middleware.rate_limit import LOGIN_LIMIT, rate_limit

from app.api.deps import CurrentUser, get_current_user
from app.core.config import settings
from app.core.security import (
    create_access_token,
    dummy_verify,
    generate_refresh_secret,
    hash_password,
    hash_token,
    needs_rehash,
    new_jti,
    verify_password,
)
from app.db.session import get_db
from app.models.user import RefreshToken, Role, User, UserRole
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    MeResponse,
    RefreshRequest,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"

# Un solo mensaje para "no existe", "contraseña mala" y "inactivo". Distinguirlos
# le diría a un atacante qué usernames están registrados.
_INVALID = "Credenciales inválidas"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _set_refresh_cookie(
    response: Response, token: str, max_age: int, is_https: bool
) -> None:
    """Guarda el refresh en un cookie `HttpOnly`.

    `HttpOnly` es lo que evita que un XSS lo lea: con esto, robar la sesión exige
    además ejecución de script, no solo leer `localStorage`. `SameSite=Strict`
    bloquea el CSRF contra este endpoint (el cookie no se adjunta a requests
    originados en otro sitio).

    `Secure` se decide por el esquema real o por `X-Forwarded-Proto`: detrás de un
    balanceador la request llega en http y el TLS termina en el proxy, así que
    `request.url.scheme` solo miente. El parámetro va aparte para no romper el
    desarrollo en http, donde un cookie `Secure` no vuelve nunca.
    """
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=is_https,
        samesite="strict",
        path="/api/auth",
    )


def _is_https(request: Request) -> bool:
    forwarded = request.headers.get("x-forwarded-proto", "")
    if forwarded:
        return forwarded.split(",")[0].strip().lower() == "https"
    return request.url.scheme == "https"


def _issue_session(
    db: Session,
    response: Response,
    *,
    subject: str,
    user_id: Optional[str],
    roles: list[str],
    permissions: list[str],
    is_https: bool,
    secret: Optional[str] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> LoginResponse:
    """Emite access + refresh y persiste el refresh hasheado."""
    access_token, access_exp, _ = create_access_token(
        subject=subject,
        roles=roles,
        permissions=permissions,
        secret=secret,
    )

    refresh_days = settings.REFRESH_TOKEN_DAYS
    refresh_secret = generate_refresh_secret()
    refresh_jti = new_jti()
    refresh_expires_at = _now() + timedelta(days=refresh_days)

    if user_id is not None:
        db.add(
            RefreshToken(
                jti=refresh_jti,
                user_id=user_id,
                token_hash=hash_token(refresh_secret),
                expires_at=refresh_expires_at,
                ip=ip,
                user_agent=(user_agent or "")[:300] or None,
            )
        )
        db.commit()

    _set_refresh_cookie(response, refresh_secret, refresh_days * 86400, is_https)

    return LoginResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_MINUTES * 60,
        refresh_expires_in=refresh_days * 86400,
        refresh_token=refresh_secret,
        username=subject,
        roles=roles,
        permissions=permissions,
    )


@router.post("/login", response_model=LoginResponse)
@rate_limit(limit=LOGIN_LIMIT)
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    """Autentica y emite la sesión.

    El rate limit por IP sigue en pie como primera barrera, pero ya no es la única:
    ahora también hay lockout por usuario, así que un atacante distribuido que
    saltee el límite por IP igual choca contra el contador de la cuenta.
    """
    # ── Camino 1: super admin del proveedor ──
    provider_usernames = [u.lower() for u in settings.SUPER_ADMIN_USERNAMES]
    if provider_usernames and body.username.lower() in provider_usernames:
        if not settings.PROVIDER_TOKEN_SECRET or not secrets.compare_digest(
            body.password, settings.PROVIDER_TOKEN_SECRET
        ):
            # Mismo 401 y mismo texto que un password incorrecto cualquiera.
            dummy_verify()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID
            )
        return _issue_session(
            db,
            response,
            subject=body.username,
            user_id=None,
            roles=["SUPER_ADMIN"],
            permissions=["*"],
            secret=settings.PROVIDER_TOKEN_SECRET,
            is_https=_is_https(request),
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

    # ── Camino 2: usuario de la municipalidad ──
    from app.models.user import User

    user = db.execute(
        select(User).where(User.username == body.username)
    ).scalar_one_or_none()

    if user is None:
        # Igualar el costo: si el login de un usuario inexistente fuera
        # instantáneo, se enumerarian los usernames midiendo tiempos.
        dummy_verify()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID
        )

    # Lockout antes de verificar el hash: una cuenta bloqueada no gasta CPU de
    # argon2 ni aunque le manden la contraseña correcta.
    if user.locked_until is not None:
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > _now():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "Cuenta bloqueada por intentos fallidos. "
                    f"Reintentá después de {locked_until.isoformat()}."
                ),
            )

    if not user.is_active:
        # Mismo mensaje que una contraseña mala: no confirmamos que la cuenta existe.
        dummy_verify()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID
        )

    if not verify_password(body.password, user.password_hash):
        _register_failed_attempt(db, user)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID
        )

    # Credenciales correctas: se limpia el lockout y se loguea.
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = _now()

    # Re-hash oportunista: si se endurecieron los parámetros de argon2, este es el
    # momento barato de migrar el hash de este usuario.
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)

    # Los permisos se resuelven acá y viajan en el token. Aun así `deps.py` los
    # relee de la base en cada request, así que revocar un rol surte efecto de
    # inmediato sin depender de la expiración.
    roles, permissions = _resolve_roles_and_permissions(db, user)
    db.commit()

    return _issue_session(
        db,
        response,
        subject=user.username,
        user_id=user.id,
        roles=roles,
        permissions=permissions,
        is_https=_is_https(request),
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


def _register_failed_attempt(db: Session, user) -> None:
    """Suma un intento fallido y bloquea la cuenta al llegar al máximo."""
    user.failed_login_count = (user.failed_login_count or 0) + 1
    if user.failed_login_count >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
        user.locked_until = _now() + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
        user.failed_login_count = 0
    db.commit()


def _resolve_roles_and_permissions(
    db: Session, user: "User"
) -> tuple[list[str], list[str]]:
    """Lee los roles y permisos efectivos del usuario desde la base."""
    from sqlalchemy.orm import selectinload

    loaded = db.execute(
        select(User)
        .where(User.id == user.id)
        .options(
            selectinload(User.user_roles)
            .selectinload(UserRole.role)
            .selectinload(Role.role_permissions)
        )
    ).scalar_one()

    roles: list[str] = []
    permissions: list[str] = []
    for ur in loaded.user_roles:
        if ur.role is None:
            continue
        roles.append(ur.role.code)
        for rp in ur.role.role_permissions:
            if rp.permission is not None:
                permissions.append(rp.permission.code)

    if user.is_superuser:
        permissions.append("*")

    return sorted(set(roles)), sorted(set(permissions))


@router.post("/refresh", response_model=LoginResponse)
def refresh(
    request: Request,
    response: Response,
    body: RefreshRequest,
    db: Session = Depends(get_db),
):
    """Renueva la sesión. Rota el refresh: el viejo queda revocado.

    La rotación es lo que hace que el robo de un refresh sea detectable y de un solo
    uso. El `jti` del refresh presentado se marca revocado y se emite uno nuevo; si
    alguien intenta reutilizar el viejo, falla.
    """
    token = body.refresh_token or request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    presented_hash = hash_token(token)

    row = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == presented_hash)
    ).scalar_one_or_none()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh inválido"
        )
    if row.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh ya revocado (posible reuso)",
        )

    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= _now():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh expirado"
        )

    from app.models.user import User

    user = db.execute(
        select(User).where(User.id == row.user_id)
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Cuenta inactiva"
        )

    # Revoca el presented y encadena el nuevo.
    row.revoked_at = _now()
    db.commit()

    roles, permissions = _resolve_roles_and_permissions(db, user)
    db.commit()

    return _issue_session(
        db,
        response,
        subject=user.username,
        user_id=user.id,
        roles=roles,
        permissions=permissions,
        is_https=_is_https(request),
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(
    response: Response,
    body: Optional[RefreshRequest] = None,
    db: Session = Depends(get_db),
):
    """Revoca el refresh actual.

    Revocar el refresh es lo que hace real el logout: el access ya emitido seguirá
    siendo válido hasta su expiración (máximo `ACCESS_TOKEN_MINUTES`), porque un
    JWT autocontenido no se puede invalidar sin una lista de revocación. Ese es el
    motivo de que el access sea corto.
    """
    presented = (body.refresh_token if body else None) or ""
    revoked = False
    if presented:
        row = db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(presented))
        ).scalar_one_or_none()
        if row is not None and row.revoked_at is None:
            row.revoked_at = _now()
            db.commit()
            revoked = True

    # Si vino por cookie, se limpia igual.
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth")

    return LogoutResponse(
        revoked=revoked,
        detail=(
            "Sesión revocada"
            if revoked
            else "Sin sesión activa que revocar"
        ),
    )


@router.get("/me", response_model=MeResponse)
def me(current: CurrentUser = Depends(get_current_user)):
    """Identidad y capacidades del actor.

    Es lo que el frontend usa para decidir qué menús y pantallas mostrar. Acá se
    filtran los permisos: un operador de campo recibe 5, no los 19 del
    administrador.
    """
    return MeResponse(
        id=current.id,
        username=current.username,
        roles=current.roles,
        permissions=current.permissions,
        is_provider_super_admin=current.is_provider_super_admin,
        is_superuser=current.is_superuser,
        scopes=current.scopes,
        is_global_scope=current.is_global_scope,
    )


@router.post("/change-password", response_model=LogoutResponse)
def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    """Cambia la contraseña propia y revoca todas las sesiones abiertas.

    Revocar todas es deliberado: si el cambio viene de una sospecha de robo, dejar
    vivas las sesiones del atacante no sirve de nada.
    """
    from app.models.user import User

    if current.id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El super admin del proveedor no cambia contraseña desde acá",
        )

    user = db.execute(select(User).where(User.id == current.id)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No existe")

    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Contraseña actual incorrecta"
        )
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La contraseña nueva debe ser distinta de la actual",
        )

    user.password_hash = hash_password(body.new_password)

    for rt in db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
        )
    ).scalars():
        rt.revoked_at = _now()
    db.commit()

    return LogoutResponse(revoked=True, detail="Contraseña actualizada y sesiones revocadas")