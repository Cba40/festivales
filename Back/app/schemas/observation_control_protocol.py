"""Schemas (DTOs) del Protocolo de Control de Observaciones.

Mismo contrato que ``app/schemas/emergency_protocol.py``: un DTO de lectura, uno
de listado, y DTOs de escritura con un ``Create`` (obligatorios mínimos) y un
``Update`` (todo opcional, para PATCH parcial).

La diferencia con los protocolos de emergencia es la propiedad: aquellos son un
catálogo transversal sin ``event_id``; estos son **por evento**, asi que
``event_id`` es obligatorio en la creación y obligatorio como filtro en el GET.
"""
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.observation_control_protocol import (
    ObservationTriggerMetric,
    ObservationTriggerOperator,
)

#: Intervalos que la UI ofrece. El backend acepta 1..1440.
MIN_INTERVAL_MINUTES = 1
MAX_INTERVAL_MINUTES = 1440


class ObservationControlProtocolResponse(BaseModel):
    """DTO de respuesta con un protocolo de control de observaciones."""

    id: str
    event_id: str
    event_day_id: Optional[str]
    name: str
    description: Optional[str]
    trigger_metric: ObservationTriggerMetric
    trigger_operator: ObservationTriggerOperator
    threshold_value: Decimal
    action_interval_minutes: int
    zone_type_id: Optional[str]
    active: bool
    order: int

    model_config = ConfigDict(from_attributes=True)


class ObservationControlProtocolListResponse(BaseModel):
    """Respuesta del listado de protocolos de un evento."""

    event_id: str
    protocols: list[ObservationControlProtocolResponse]


class ObservationControlProtocolCreate(BaseModel):
    """DTO de creación. ``event_id``, ``name``, ``trigger_metric``,
    ``threshold_value`` y ``action_interval_minutes`` son obligatorios."""

    event_id: str = Field(..., min_length=1, max_length=36)
    event_day_id: Optional[str] = Field(None, max_length=36)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    trigger_metric: ObservationTriggerMetric
    trigger_operator: ObservationTriggerOperator = ObservationTriggerOperator.GT
    threshold_value: Decimal
    action_interval_minutes: int = Field(
        ..., ge=MIN_INTERVAL_MINUTES, le=MAX_INTERVAL_MINUTES
    )
    zone_type_id: Optional[str] = Field(None, max_length=36)
    active: bool = True
    order: int = Field(0, ge=0)


class ObservationControlProtocolUpdate(BaseModel):
    """DTO de actualización. Todos opcionales (PATCH parcial)."""

    event_day_id: Optional[str] = Field(None, max_length=36)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    trigger_metric: Optional[ObservationTriggerMetric] = None
    trigger_operator: Optional[ObservationTriggerOperator] = None
    threshold_value: Optional[Decimal] = None
    action_interval_minutes: Optional[int] = Field(
        None, ge=MIN_INTERVAL_MINUTES, le=MAX_INTERVAL_MINUTES
    )
    zone_type_id: Optional[str] = Field(None, max_length=36)
    active: Optional[bool] = None
    order: Optional[int] = Field(None, ge=0)


class ProtocolSuggestion(BaseModel):
    """Sugerencia predefinida que el operador puede aplicar con un clic."""

    key: str
    name: str
    description: Optional[str] = None
    trigger_metric: ObservationTriggerMetric
    trigger_operator: ObservationTriggerOperator
    threshold_value: Decimal
    action_interval_minutes: int
    rule_sentence: str


class SuggestionsResponse(BaseModel):
    suggestions: list[ProtocolSuggestion]


class ApplySuggestionsRequest(BaseModel):
    """Solicitud para sembrarProtocolos sugeridos en un evento."""

    event_id: str = Field(..., min_length=1, max_length=36)
    suggestion_keys: list[str] = Field(..., min_length=1)


class ApplySuggestionsResponse(BaseModel):
    """Resultado de aplicar sugerencias.

    ``skipped`` cuenta las que ya existían: la siembra es idempotente por
    ``(event_id, name)``, igual que ``seed_protocols`` de seed.py.
    """

    created: int
    skipped: int
    created_names: list[str] = Field(default_factory=list)


class ComplianceAlertResponse(BaseModel):
    """Incumplimiento detectado: el trigger se cumple y no hay observación
    reciente para la zona."""

    protocol_id: str
    protocol_name: str
    event_day_id: Optional[str]
    zone_id: Optional[str]
    zone_name: Optional[str]
    trigger_metric: ObservationTriggerMetric
    trigger_operator: ObservationTriggerOperator
    threshold_value: Decimal
    current_value: Optional[Decimal]
    action_interval_minutes: int
    minutes_since_last_observation: Optional[int]
    overdue_minutes: int
    severity: str
    detail: str


class ComplianceResponse(BaseModel):
    """Estado de cumplimiento de todos los protocolos activos del evento."""

    event_id: str
    evaluated_at: str
    total_alerts: int
    alerts: list[ComplianceAlertResponse]