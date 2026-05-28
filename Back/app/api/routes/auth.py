# backend/app/api/routes/auth.py

from datetime import timedelta, datetime, timezone

from fastapi import APIRouter, HTTPException, status
from jose import jwt

from app.core.config import settings
from app.schemas.auth import LoginRequest, LoginResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest):
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
