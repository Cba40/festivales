"""Gestión de Protocolos de Control de Observaciones.

CRUD plano sobre ``observation_control_protocols`` para el Dashboard
(Motor > Protocolos de observación), calcado de ``emergency_protocol_admin.py``:
prefijo ``/api/admin``, lecturas sin token, escrituras con ``verify_token`` y
soft delete.

Dos diferencias con los protocolos de emergencia, y las dos son a propósito:

1. **Son por evento.** ``event_id`` es obligatorio en el POST y en el GET. El
   catálogo de emergencias es transversal; estas reglas no.
2. **Sesión mixta.** El CRUD usa ``Session`` síncrona como el admin de emergencia,
   porque solo toca modelos de ``app/``. Pero ``/compliance`` lee
   ``predictions`` y ``operational_observations``, que viven en el registro
   ``src/`` y se consultan en toda la app con ``AsyncSession``. Forzarlo por la
   sesión síncrona es exactamente lo que produce ``MissingGreenlet``.

Orden de declaración
--------------------
``/suggestions`` y ``/apply-suggestions`` van antes que ``/{protocol_id}``; si no,
FastAPI los capturaría como si fueran un id.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.api.deps import verify_token
from app.db.session import get_async_db, get_db
from app.models.observation_control_protocol import (
    ObservationControlProtocol,
    ObservationTriggerMetric,
    ObservationTriggerOperator,
)
from app.schemas.observation_control_protocol import (
    ApplySuggestionsRequest,
    ApplySuggestionsResponse,
    ComplianceAlertResponse,
    ComplianceResponse,
    ObservationControlProtocolCreate,
    ObservationControlProtocolResponse,
    ObservationControlProtocolUpdate,
    ProtocolSuggestion,
    SuggestionsResponse,
)
from app.services.observation_compliance import ObservationComplianceEvaluator

router = APIRouter(prefix="/api/admin/observation-control-protocols", tags=["ObservationControlProtocol"])


# ── Sugerencias predefinidas ────────────────────────────────────────────────
#
# Constante de módulo, no filas en base: son sugerencias de arranque, no
# configuracion. El operador elige cuales aplicar y despues son filas normales,
# editables. Cada `key` coincide con `name`, que es la clave natural que hace
# idempotente la siembra.
SUGGESTIONS: list[ProtocolSuggestion] = [
    ProtocolSuggestion(
        key="saturacion_alta",
        name="Saturación alta",
        description="Se activa cuando una zona se llena y hay riesgo de cola.",
        trigger_metric=ObservationTriggerMetric.SATURATION_LEVEL,
        trigger_operator=ObservationTriggerOperator.GT,
        threshold_value=Decimal("0.80"),
        action_interval_minutes=5,
        rule_sentence=(
            "Si la saturación supera 80%, registrar una observación cada 5 minutos."
        ),
    ),
    ProtocolSuggestion(
        key="espera_larga",
        name="Espera larga",
        description="Se activa cuando la espera estimada crece en puntos de control.",
        trigger_metric=ObservationTriggerMetric.ESTIMATED_WAIT,
        trigger_operator=ObservationTriggerOperator.GT,
        threshold_value=Decimal("15"),
        action_interval_minutes=10,
        rule_sentence=(
            "Si la espera estimada supera 15 minutos, registrar una observación "
            "cada 10 minutos."
        ),
    ),
    ProtocolSuggestion(
        key="disponibilidad_critica",
        name="Disponibilidad crítica",
        description="Se activa cuando a una zona le quedan pocas personas de aforo.",
        trigger_metric=ObservationTriggerMetric.AVAILABILITY,
        trigger_operator=ObservationTriggerOperator.LT,
        threshold_value=Decimal("20"),
        action_interval_minutes=5,
        rule_sentence=(
            "Si la disponibilidad es menor que 20, registrar una observación "
            "cada 5 minutos."
        ),
    ),
    ProtocolSuggestion(
        key="confianza_baja",
        name="Confianza baja",
        description="Se activa cuando el motor no está seguro de su propia predicción.",
        trigger_metric=ObservationTriggerMetric.CONFIDENCE,
        trigger_operator=ObservationTriggerOperator.LT,
        threshold_value=Decimal("0.50"),
        action_interval_minutes=15,
        rule_sentence=(
            "Si la confianza del motor es menor que 50%, registrar una observación "
            "cada 15 minutos."
        ),
    ),
]

_SUGGESTIONS_BY_KEY = {s.key: s for s in SUGGESTIONS}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_or_404(db: Session, protocol_id: str) -> ObservationControlProtocol:
    proto = (
        db.query(ObservationControlProtocol)
        .filter(ObservationControlProtocol.id == protocol_id)
        .first()
    )
    if not proto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Protocol not found"
        )
    return proto


def _name_conflict(
    db: Session, event_id: str, name: str, exclude_id: Optional[str] = None
) -> bool:
    query = db.query(ObservationControlProtocol).filter(
        ObservationControlProtocol.event_id == event_id,
        ObservationControlProtocol.name == name,
    )
    if exclude_id is not None:
        query = query.filter(ObservationControlProtocol.id != exclude_id)
    return query.first() is not None


def _clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _validate_event(db: Session, event_id: str) -> None:
    """El evento tiene que existir: si no, la FK revienta con un 500 opaco."""
    from app.models.event import Event

    exists = db.query(Event.id).filter(Event.id == event_id).first()
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )


def _validate_event_day(db: Session, event_day_id: Optional[str]) -> None:
    if event_day_id is None:
        return
    from app.models.event_day import EventDay

    exists = db.query(EventDay.id).filter(EventDay.id == event_day_id).first()
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="EventDay not found"
        )


def _validate_zone_type(db: Session, zone_type_id: Optional[str]) -> None:
    if zone_type_id is None:
        return
    from app.models.zone_type import ZoneType

    exists = db.query(ZoneType.id).filter(ZoneType.id == zone_type_id).first()
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="ZoneType not found"
        )


# ── Sugerencias (antes de /{protocol_id}) ────────────────────────────────────


@router.get("/suggestions", response_model=SuggestionsResponse)
def list_suggestions(_=Depends(verify_token)):
    """Las 4 sugerencias de arranque, para que el operador no escriba reglas de cero."""
    return SuggestionsResponse(suggestions=SUGGESTIONS)


@router.post("/apply-suggestions", response_model=ApplySuggestionsResponse)
def apply_suggestions(
    body: ApplySuggestionsRequest,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    """Crea los protocolos sugeridos que falten en el evento.

    Idempotente por ``(event_id, name)``, igual que ``seed_protocols`` de
    ``seed.py``: si el operador vuelve a aplicar una sugerencia que ya adoptó, no
    se duplica. Devuelve los conteos para que la UI pueda decir "se crearon 2, ya
    existían 2".
    """
    unknown = [k for k in body.suggestion_keys if k not in _SUGGESTIONS_BY_KEY]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown suggestion keys: {', '.join(sorted(unknown))}",
        )

    _validate_event(db, body.event_id)

    created = 0
    skipped = 0
    created_names: list[str] = []
    for key in body.suggestion_keys:
        suggestion = _SUGGESTIONS_BY_KEY[key]
        if _name_conflict(db, body.event_id, suggestion.name):
            skipped += 1
            continue
        db.add(
            ObservationControlProtocol(
                event_id=body.event_id,
                event_day_id=None,
                name=suggestion.name,
                description=suggestion.description,
                trigger_metric=suggestion.trigger_metric,
                trigger_operator=suggestion.trigger_operator,
                threshold_value=suggestion.threshold_value,
                action_interval_minutes=suggestion.action_interval_minutes,
                zone_type_id=None,
                active=True,
                order=created,
            )
        )
        created += 1
        created_names.append(suggestion.name)

    db.commit()
    return ApplySuggestionsResponse(
        created=created, skipped=skipped, created_names=created_names
    )


# ── Compliance ───────────────────────────────────────────────────────────────


@router.get("/compliance", response_model=ComplianceResponse)
async def get_compliance(
    event_id: str = Query(..., min_length=1, max_length=36),
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    """Evalúa en el momento los protocolos activos contra las observaciones reales.

    Sesión async a propósito: lee ``predictions`` y ``operational_observations``,
    que están en el registro de ``src/``.
    """
    evaluator = ObservationComplianceEvaluator(db)
    alerts, protocols_evaluated = await evaluator.evaluate_with_count(event_id)
    return ComplianceResponse(
        event_id=event_id,
        evaluated_at=datetime.now(timezone.utc).isoformat(),
        protocols_evaluated=protocols_evaluated,
        total_alerts=len(alerts),
        alerts=alerts,
    )


# ── CRUD ─────────────────────────────────────────────────────────────────────


@router.get("", response_model=list[ObservationControlProtocolResponse])
@router.get("/", response_model=list[ObservationControlProtocolResponse], include_in_schema=False)
def list_protocols(
    event_id: str = Query(..., min_length=1, max_length=36),
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    """Lista los protocolos de un evento. Sin token: lo consume el dashboard."""
    query = db.query(ObservationControlProtocol).filter(
        ObservationControlProtocol.event_id == event_id
    )
    if not include_inactive:
        query = query.filter(ObservationControlProtocol.active.is_(True))
    return query.order_by(
        ObservationControlProtocol.order,
        ObservationControlProtocol.name,
    ).all()


@router.post("", response_model=ObservationControlProtocolResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ObservationControlProtocolResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_protocol(
    body: ObservationControlProtocolCreate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    name = body.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Name must not be empty",
        )

    _validate_event(db, body.event_id)
    _validate_event_day(db, body.event_day_id)
    _validate_zone_type(db, body.zone_type_id)

    if _name_conflict(db, body.event_id, name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A protocol with this name already exists for this event",
        )

    proto = ObservationControlProtocol(
        event_id=body.event_id,
        event_day_id=body.event_day_id,
        name=name,
        description=_clean(body.description),
        trigger_metric=body.trigger_metric,
        trigger_operator=body.trigger_operator,
        threshold_value=body.threshold_value,
        action_interval_minutes=body.action_interval_minutes,
        zone_type_id=body.zone_type_id,
        active=body.active,
        order=body.order,
    )
    db.add(proto)
    db.commit()
    db.refresh(proto)
    return proto


@router.put("/{protocol_id}", response_model=ObservationControlProtocolResponse)
def update_protocol(
    protocol_id: str,
    body: ObservationControlProtocolUpdate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    proto = _get_or_404(db, protocol_id)
    provided = body.model_fields_set

    # ── Validar ANTES de tocar el objeto ──
    #
    # El orden importa. `db.query()` dispara autoflush, asi que si se asigna
    # `proto.name` antes de comprobar la unicidad, el UPDATE con el nombre
    # duplicado sale en la base y revienta con UniqueViolation (500) en vez de
    # devolver 409. Se calcula el valor efectivo en local, se comprueba, y solo
    # después se aplica.
    if "event_day_id" in provided:
        _validate_event_day(db, body.event_day_id)
    if "zone_type_id" in provided:
        _validate_zone_type(db, body.zone_type_id)

    new_name = proto.name
    if "name" in provided and body.name is not None:
        new_name = body.name.strip()
        if not new_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Name must not be empty",
            )

    # `event_id` no se cambia por PUT: mudarlo de evento dejaría duplicados los
    # nombres ya sembrados en el destino.
    if _name_conflict(db, proto.event_id, new_name, exclude_id=proto.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A protocol with this name already exists for this event",
        )

    # ── Aplicar ──
    if "event_day_id" in provided:
        proto.event_day_id = body.event_day_id
    if "zone_type_id" in provided:
        proto.zone_type_id = body.zone_type_id
    proto.name = new_name

    if body.trigger_metric is not None:
        proto.trigger_metric = body.trigger_metric
    if body.trigger_operator is not None:
        proto.trigger_operator = body.trigger_operator
    if body.threshold_value is not None:
        proto.threshold_value = body.threshold_value
    if body.action_interval_minutes is not None:
        proto.action_interval_minutes = body.action_interval_minutes
    if body.active is not None:
        proto.active = body.active
    if body.order is not None:
        proto.order = body.order
    if "description" in provided:
        proto.description = _clean(body.description)

    db.commit()
    db.refresh(proto)
    return proto


@router.delete("/{protocol_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_protocol(
    protocol_id: str,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    """Soft delete: ``active=False`` preserva el histórico de qué regla se violated."""
    proto = _get_or_404(db, protocol_id)
    proto.active = False
    db.commit()