"""DTOs del CRUD de usuarios del administrador municipal.

Decisiones
----------
**El password nunca vuelve en una respuesta.** `UserResponse` no tiene campo de
password ni `password_hash`. Es la regla que evita que un `GET /api/admin/users`
termine filtrando credenciales hasheadas a cualquier operador con permiso de
lectura: el hash no es la contraseña, pero alimenta el offline cracking, y no
tiene razón de estar en una respuesta de API.

`password` solo se acepta en `UserCreate` y en `UserChangePassword`. El resto de
los DTOs ni siquiera lo mencionan, así que un `UserUpdate` con un campo `password`
sobrante lo rechaza en vez de ignorarlo en silencio.

**`role` singular en el create, lista en la respuesta.** La creación acepta un rol
único porque es el caso normal (se da de alta a alguien con un rol). A partir de
ahí el usuario puede tener varios, y por eso la respuesta trae `roles: list`. La
asignación de roles adicionales tiene su propio endpoint.

`is_superuser` NO es un campo editable. Es capacidad de emergencia del seed y no
un permiso asignable; si se pudiera cambiar por API, cualquier administrador con
`users:write` se autoelevaría a superusuario. Editarlo requiere acceso a la base.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

MIN_PASSWORD_LENGTH = 8


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=150)
    # Mínimo 8, aunque argon2 es lo que realmente protege. Un mínimo bajo no
    # agrega seguridad; solo evita el typosquatting de "admin1".
    password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=200)
    email: Optional[str] = Field(None, max_length=254)
    full_name: Optional[str] = Field(None, max_length=200)
    role: str = Field(..., max_length=50)
    is_active: bool = True


class UserUpdate(BaseModel):
    """Edición de un usuario.

    `password` va aparte de la clase a propósito: por default es opcional, así que
    un `PUT` que solo cambia el email no manda un hash nuevo (lo que dejaría al
    usuario con una contraseña que nunca eligió).
    """

    password: Optional[str] = Field(None, min_length=MIN_PASSWORD_LENGTH, max_length=200)
    email: Optional[str] = Field(None, max_length=254)
    full_name: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None


class RoleAssign(BaseModel):
    """Asignación de un rol a un usuario.

    `event_id` / `zone_id` implementan el scope. Un operador de campo acotado a su
    zona se crea con `zone_id`; sin eso el usuario vería toda la municipalidad.
    """

    role_code: str = Field(..., min_length=1, max_length=50)
    event_id: Optional[str] = Field(None, max_length=36)
    zone_id: Optional[str] = Field(None, max_length=36)


class UserRoleResponse(BaseModel):
    role_id: str
    role_code: str
    role_name: str
    event_id: Optional[str] = None
    zone_id: Optional[str] = None
    granted_at: datetime


class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str]
    full_name: Optional[str]
    is_active: bool
    # Desnormalizado: es la capacidad de emergencia del seed. Se muestra para que
    # el administrador sepa que existe, pero `UserUpdate` no la acepta, así que no
    # se puede otorgar por API.
    is_superuser: bool
    locked_until: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime
    roles: list[UserRoleResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    total: int
    users: list[UserResponse]