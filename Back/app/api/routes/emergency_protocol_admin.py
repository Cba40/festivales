"""Gestión administrativa de Protocolos de Emergencia (Emergencia V2 - S5).

CRUD plano sobre el catálogo ``emergency_protocols`` para el Dashboard
(Infraestructura > Protocolos de Emergencia): crear, listar, actualizar,
activar/desactivar y eliminar (soft delete) protocolos.

El catálogo es transversal (por ``context``, sin ``event_id`` ni ``city_id``).
Patrón idéntico a emergency_admin.py / accommodation_admin.py: preijo
``/api/admin``, lecturas públicas y escrituras con ``verify_token``.

El DELETE es un *soft delete*: establece ``active = False`` preservando el
histórico y ocultando el protocolo del endpoint público (S2 filtra por
``active_only``).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import verify_token
from app.db.session import get_db
from app.models.emergency_protocol import EmergencyProtocol, EmergencyProtocolContext
from app.schemas.emergency_protocol import (
    EmergencyProtocolResponse,
    ProtocolCreate,
    ProtocolUpdate,
)

router = APIRouter(prefix="/api/admin", tags=["EmergencyProtocolAdmin"])


def _get_protocol_or_404(db: Session, protocol_id: str) -> EmergencyProtocol:
    proto = db.query(EmergencyProtocol).filter(EmergencyProtocol.id == protocol_id).first()
    if not proto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Protocol not found",
        )
    return proto


def _title_conflict(
    db: Session,
    context: EmergencyProtocolContext,
    title: str,
    exclude_id: str | None = None,
) -> bool:
    query = db.query(EmergencyProtocol).filter(
        EmergencyProtocol.context == context,
        EmergencyProtocol.title == title,
    )
    if exclude_id is not None:
        query = query.filter(EmergencyProtocol.id != exclude_id)
    return query.first() is not None


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


@router.get("/emergency-protocols", response_model=list[EmergencyProtocolResponse])
def list_protocols(
    context: EmergencyProtocolContext | None = None,
    db: Session = Depends(get_db),
):
    """Lista todos los protocolos (incluye inactivos), opcionalmente por contexto."""
    query = db.query(EmergencyProtocol)
    if context is not None:
        query = query.filter(EmergencyProtocol.context == context)
    return (
        query.order_by(
            EmergencyProtocol.context,
            EmergencyProtocol.priority,
            EmergencyProtocol.order,
            EmergencyProtocol.title,
        )
        .all()
    )


@router.post(
    "/emergency-protocols",
    response_model=EmergencyProtocolResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_protocol(
    body: ProtocolCreate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    title = body.title.strip()
    if not title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Title must not be empty",
        )

    icon = body.icon.strip()
    if not icon:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Icon must not be empty",
        )

    if _title_conflict(db, body.context, title):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Protocol already exists for this context",
        )

    proto = EmergencyProtocol(
        context=body.context,
        title=title,
        description=_clean(body.description),
        icon=icon,
        steps=body.steps,
        priority=body.priority,
        order=body.order,
        target_type=body.target_type,
        active=body.active,
    )
    db.add(proto)
    db.commit()
    db.refresh(proto)
    return proto


@router.put(
    "/emergency-protocols/{protocol_id}",
    response_model=EmergencyProtocolResponse,
)
def update_protocol(
    protocol_id: str,
    body: ProtocolUpdate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    proto = _get_protocol_or_404(db, protocol_id)
    provided = body.model_fields_set

    if "title" in provided and body.title is not None:
        title = body.title.strip()
        if not title:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Title must not be empty",
            )
        proto.title = title
    if "icon" in provided and body.icon is not None:
        icon = body.icon.strip()
        if not icon:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Icon must not be empty",
            )
        proto.icon = icon

    # Unicidad (context, title) excluyendo el propio registro: valida con los
    # valores vigentes una vez aplicados los cambios.
    effective_context = (
        body.context if "context" in provided and body.context is not None else proto.context
    )
    effective_title = proto.title
    if _title_conflict(db, effective_context, effective_title, exclude_id=proto.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Protocol already exists for this context",
        )

    if body.priority is not None:
        proto.priority = body.priority
    if body.order is not None:
        proto.order = body.order
    if body.active is not None:
        proto.active = body.active
    if "target_type" in provided:
        proto.target_type = body.target_type
    if "context" in provided and body.context is not None:
        proto.context = body.context
    if "description" in provided:
        proto.description = _clean(body.description)
    if "steps" in provided:
        proto.steps = body.steps

    db.commit()
    db.refresh(proto)
    return proto


@router.delete("/emergency-protocols/{protocol_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_protocol(
    protocol_id: str,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    proto = _get_protocol_or_404(db, protocol_id)
    # Soft delete: ocultamos del endpoint público sin borrar históricos.
    proto.active = False
    db.commit()