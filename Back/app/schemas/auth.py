# backend/app/schemas/auth.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=150)
    password: str = Field(..., min_length=1, max_length=200)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    # Segundos. El frontend lo usa para renovar el access antes de que expire en
    # lugar de esperar al 401.
    expires_in: int
    refresh_expires_in: int
    # Se devuelve además del cookie: el frontend lo guarda en memoria. El cookie
    # `HttpOnly` es la vía principal (no lo puede leer un XSS); esto es para
    # clientes no-browser o para el refresh silencioso desde una SPA.
    refresh_token: str
    username: str
    roles: list[str]
    permissions: list[str]


class RefreshRequest(BaseModel):
    # Opcional si el navegador manda el cookie HttpOnly. Se acepta en el cuerpo
    # para clientes que no manejen cookies.
    refresh_token: Optional[str] = None


class MeResponse(BaseModel):
    """Identidad y capacidades del actor. Alimenta la UI para ocultar menús."""

    id: Optional[str]
    username: str
    roles: list[str]
    permissions: list[str]
    # `true` para el super admin del proveedor, que no existe en `users`.
    is_provider_super_admin: bool
    is_superuser: bool
    # Asignaciones con su alcance. `{"event_id": null, "zone_id": null}` = global.
    scopes: list[dict[str, Optional[str]]]
    is_global_scope: bool


class LogoutResponse(BaseModel):
    revoked: bool
    detail: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=200)
    new_password: str = Field(..., min_length=12, max_length=200)