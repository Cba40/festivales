"""Product Endpoint Público de Protocolos de Emergencia (Emergencia V2 - S2).

Expone el catálogo de protocolos por contexto (festival / transporte /
hospedaje) sin autenticación, mismo patrón público de V1: async,
``get_async_db``, sin ``verify_token``.

Filtra y ordena con el adapter puro (``src/interfaces/rest/
emergency_protocol_product``). La resolución de ``target_type`` → recursos
(``emergencies``) se implementa en la Fase S3.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_db
from app.models.emergency_protocol import EmergencyProtocol, EmergencyProtocolContext
from app.schemas.emergency_protocol import (
    EmergencyProtocolListResponse,
    EmergencyProtocolResponse,
)
from src.interfaces.rest.emergency_protocol_product import (
    filter_protocols,
    sort_protocols,
)

router = APIRouter(prefix="/api", tags=["EmergencyProtocol"])


@router.get("/emergency-protocols", response_model=EmergencyProtocolListResponse)
async def list_emergency_protocols(
    context: EmergencyProtocolContext = Query(...),
    active_only: bool = Query(True),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
):
    """Protocolos de emergencia de un contexto (público).

    Consulta el catálogo completo, filtra por contexto y estado activo y ordena
    determinísticamente (priority ASC, order ASC, id ASC) con el adapter puro.
    Un contexto sin protocolos (o todos inactivos) devuelve lista vacía, no 404.
    """
    result = await db.execute(select(EmergencyProtocol))
    rows = result.scalars().all()

    filtered = filter_protocols(rows, context, active_only=active_only)
    ordered = sort_protocols(filtered)

    return EmergencyProtocolListResponse(
        context=context,
        protocols=[
            EmergencyProtocolResponse.model_validate(p) for p in ordered[:limit]
        ],
    )