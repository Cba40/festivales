"""Minting de tokens para los tests.

Por qué existe
--------------
Antes, cada módulo de test armaba su JWT a mano:

    token = jwt.encode({"sub": "admin", "exp": expire}, settings.SECRET_KEY, ...)

Eso duplicaba la construcción del token en 23 archivos y, peor, quedó desactualizado
respecto de `app/core/security.py`: al empezar a exigir `typ`, `iss` y `aud`, esos
23 archivos quedaron fallando por su cuenta: los tests seguían siendo correctos,
lo que estaba mal era el token que fabricaban.

Con `mint_token()` el token sale de la misma función que usa producción, así que si
aparece un claim nuevo los tests lo heredan solos en vez de romperse con un 401.

Qué NO hace este helper
-----------------------
No crea usuarios en la base. La mayoría de los endpoints bajo prueba siguen usando
`verify_token`, que solo valida la firma y no toca la base, así que un `sub` que no
existe en `users` es suficiente. Cuando un endpoint pase a usar `get_current_user`,
el test va a necesitar un usuario real: para eso están `mint_token_for_user` y el
fixture de la suite.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.security import create_access_token

DEFAULT_SUBJECT = "admin"


def mint_token(
    subject: str = DEFAULT_SUBJECT,
    roles: list[str] | None = None,
    permissions: list[str] | None = None,
    expires_minutes: int = 60,
) -> str:
    """Token de acceso válido, firmado con la `SECRET_KEY` de `settings`.

    Sale de `create_access_token`, la misma función que usa el login real, así que
    los claims no pueden derivar: si producción exige `typ`, el test también.
    """
    token, _expires, _jti = create_access_token(
        subject=subject,
        roles=roles or ["MUNICIPAL_ADMIN"],
        permissions=permissions or ["*"],
        expires_minutes=expires_minutes,
    )
    return token


def mint_token_for_user(user, expires_minutes: int = 60) -> str:
    """Token para un `User` real de la base.

    Para los endpoints que usan `get_current_user`: ahí el token no basta, la
    dependencia relee el usuario de `users`, así que el usuario tiene que existir y
    estar activo.
    """
    return mint_token(
        subject=user.username,
        roles=[ur.role.code for ur in user.user_roles if ur.role is not None],
        permissions=["*"],
        expires_minutes=expires_minutes,
    )


def auth_headers(
    subject: str = DEFAULT_SUBJECT,
    roles: list[str] | None = None,
    permissions: list[str] | None = None,
) -> dict[str, str]:
    """Header `Authorization` listo para usar."""
    return {
        "Authorization": f"Bearer {mint_token(subject, roles=roles, permissions=permissions)}"
    }