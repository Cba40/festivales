"""Endpoints for OperationalObservation (RFC-006): ingesta, consulta y correccion.

El router es el unico de todo `app/api/routes` que exponia escritura sin token
(`operational_observations.py:19-61` en la version previa a este cambio). Con la
correccion in-place, mutar una medicion de campo pasa a ser una operacion
sensibile, asi que los cuatro endpoints exigen `verify_token`.

La autenticacion no es autorizacion: `verify_token` prueba que hay un token
valido y devuelve su `sub`, pero no hay roles. El `sub` se usa para firmar la
correccion (`corrected_by`), no para decidir quien puede corregir.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TokenPayload, verify_token
from app.crud.operational_observation import (
    create_observation,
    find_all,
    get_observation,
    update_observation,
)
from app.db.session import get_async_db
from app.schemas.operational_observation import (
    OperationalObservationCreate,
    OperationalObservationResponse,
    OperationalObservationUpdate,
)

router = APIRouter(prefix="/operational-observations", tags=["Operational Observations"])


@router.post("/", response_model=OperationalObservationResponse, status_code=status.HTTP_201_CREATED)
async def create_observation_endpoint(
    observation_in: OperationalObservationCreate,
    db: AsyncSession = Depends(get_async_db),
    _: TokenPayload = Depends(verify_token),
):
    try:
        return await create_observation(db, observation_in)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.get("/", response_model=list[OperationalObservationResponse])
async def list_observations(
    event_day_id: Optional[str] = None,
    zone_id: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    db: AsyncSession = Depends(get_async_db),
    _: TokenPayload = Depends(verify_token),
):
    return await find_all(
        db,
        event_day_id=event_day_id,
        zone_id=zone_id,
        start_date=start,
        end_date=end,
    )


@router.get("/{observation_id}", response_model=OperationalObservationResponse)
async def get_observation_endpoint(
    observation_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _: TokenPayload = Depends(verify_token),
):
    result = await get_observation(db, observation_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OperationalObservation not found",
        )
    return result


@router.patch("/{observation_id}", response_model=OperationalObservationResponse)
async def update_observation_endpoint(
    observation_id: UUID,
    observation_in: OperationalObservationUpdate,
    db: AsyncSession = Depends(get_async_db),
    user: TokenPayload = Depends(verify_token),
):
    """Corrige una observacion. Solo densidad, observador, fuente y notas.

    `timestamp`, `zone_id` y `event_day_id` no son editables: el schema los
    rechaza con 422 en vez de ignorarlos.
    """
    if not user.sub:
        # `verify_token` ya garantiza un `sub` no vacio; este guard existe solo
        # para que el tipo Optional de TokenPayload no se Filtrar a la columna.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin identidad de usuario",
        )
    try:
        result = await update_observation(
            db, observation_id, observation_in, corrected_by=user.sub
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OperationalObservation not found",
        )
    return result
