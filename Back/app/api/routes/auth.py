# backend/app/api/routes/auth.py

from datetime import timedelta, datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from jose import jwt

from src.infrastructure.middleware.rate_limit import LOGIN_LIMIT, rate_limit

from app.core.config import settings
from app.schemas.auth import LoginRequest, LoginResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


# 5 intentos por minuto y IP. Esta es la barrera de fuerza bruta del sistema:
# mantiene las credenciales hardcodeadas de abajo igual de deterministas, pero
# impide probarlas a velocidad automatica.
#
# El endpoint paso de `def` a `async def` para que el contador asíncrono del
# rate limit pueda usarse. El cuerpo no hace I/O bloqueante (`jwt.encode` es
# CPU), asi que no cambia el contrato HTTP: solo deja de ejecutarse en un
# threadpool del worker.
@router.post("/login", response_model=LoginResponse)
@rate_limit(limit=LOGIN_LIMIT)
async def login(request: Request, body: LoginRequest):
    if body.username == "admin" and body.password == "1234":
        expire = datetime.now(timezone.utc) + timedelta(hours=8)
        token = jwt.encode(
            {"sub": body.username, "exp": expire},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        return LoginResponse(access_token=token)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
