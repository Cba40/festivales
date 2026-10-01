"""Evaluación de cumplimiento de los Protocolos de Control de Observaciones.

Qué hace
--------
Para cada protocolo **activo** de un evento:

1. Resuelve la jornada a la que aplica (la del protocolo, o la jornada activa).
2. Toma la **última predicción** de esa jornada, que es donde el Context Engine
   deja las métricas por zona (``zone_states_data``).
3. Para cada zona alcanzada por el filtro (``zone_type_id``) whose métrica
   ``trigger_metric`` cumple ``trigger_operator threshold_value``:
   busca la última observación de esa zona. Si es más vieja que
   ``action_interval_minutes``, emite una alerta de cumplimiento.

Por qué async
-------------
Lee ``predictions`` y ``operational_observations``, que viven en el registro de
``src/`` y se consultan en toda la app con ``AsyncSession`` (``event_reports.py``
y ``crud/operational_event.py`` ya lo hacen igual). El CRUD de esta feature sí usa
``Session`` síncrona como el admin de protocolos de emergencia, porque solo toca
modelos de ``app/``. Mezclar ambos registros en una sesión síncrona es lo que
provoca ``MissingGreenlet``.

Fuente de la métrica
--------------------
``predictions.zone_states_data`` es un JSON con una entrada por zona, escrita por
``prediction_mapper._zone_state_to_dict``. Sus claves numéricas son exactamente
las de ``ObservationTriggerMetric``; si una Prediction no trae la clave, el valor
se trata como ``None`` y la zona se ignora (no hay nada que evaluar).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.observation_control_protocol import (
    ObservationControlProtocol,
    ObservationTriggerMetric,
    ObservationTriggerOperator,
)
from app.schemas.observation_control_protocol import ComplianceAlertResponse

logger = logging.getLogger(__name__)

SEVERITY_CRITICAL = "critical"
SEVERITY_WARNING = "warning"


def evaluate_trigger(
    value: Optional[float],
    operator: ObservationTriggerOperator,
    threshold: Decimal,
) -> bool:
    """Aplica el comparador del protocolo.

    Un valor ``None`` (la métrica no la trajo la predicción) nunca dispara: no se
    puede afirmar que se superó un umbral sobre un dato que no existe. Devolver
    ``False`` es lo conservador; marcarlo como alerta sería ruido.
    """
    if value is None:
        return False
    try:
        numeric = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return False
    if operator is ObservationTriggerOperator.GT:
        return numeric > threshold
    if operator is ObservationTriggerOperator.GTE:
        return numeric >= threshold
    if operator is ObservationTriggerOperator.LT:
        return numeric < threshold
    return numeric <= threshold


def _zone_states_from_prediction(prediction: Any) -> list[dict]:
    """Normaliza ``zone_states_data`` a una lista de dicts.

    La columna es ``JSONB`` pero el mapper también sabe devolverla como string
    (mismo caso que contempla ``ObservationsScreen``), así que se tolera.
    """
    raw = getattr(prediction, "zone_states_data", None)
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []
    if isinstance(raw, dict):
        # Algunas filas guardan el JSONB como objeto contenedor.
        for key in ("zone_states", "items"):
            if isinstance(raw.get(key), list):
                raw = raw[key]
                break
        else:
            return []
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


class ObservationComplianceEvaluator:
    """Evalúa el cumplimiento de los protocolos de un evento."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._prediction_model = None
        self._observation_model = None

    def _models(self) -> tuple[Any, Any]:
        """Import perezoso: los modelos de ``src/`` comparten registro async."""
        if self._prediction_model is None:
            from src.infrastructure.persistence.models.prediction import PredictionModel

            self._prediction_model = PredictionModel
        if self._observation_model is None:
            from src.infrastructure.persistence.models.operational_observation import (
                OperationalObservationModel,
            )

            self._observation_model = OperationalObservationModel
        return self._prediction_model, self._observation_model

    async def _active_protocols(
        self, event_id: str
    ) -> list[ObservationControlProtocol]:
        from sqlalchemy.orm import Session

        # El modelo es de `app/`, pero la sesión de esta feature es async. La
        # lectura se hace con `select()` sobre la sesión async contra el mismo
        # Postgres, que es lo que hace el resto del código de `src/`.
        result = await self._db.execute(
            select(ObservationControlProtocol).where(
                ObservationControlProtocol.event_id == event_id,
                ObservationControlProtocol.active.is_(True),
            )
        )
        return list(result.scalars().all())

    async def _active_event_day_id(self, event_id: str) -> Optional[str]:
        from app.models.event_day import EventDay

        result = await self._db.execute(
            select(EventDay.id)
            .where(EventDay.event_id == event_id)
            .where(EventDay.is_active.is_(True))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _latest_prediction(self, event_day_id: str) -> Optional[Any]:
        prediction_model, _ = self._models()
        result = await self._db.execute(
            select(prediction_model)
            .where(prediction_model.event_day_id == event_day_id)
            .order_by(prediction_model.timestamp.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def _last_observation_at(
        self, event_day_id: str, zone_id: str
    ) -> Optional[datetime]:
        _, observation_model = self._models()
        result = await self._db.execute(
            select(observation_model.timestamp)
            .where(observation_model.event_day_id == event_day_id)
            .where(observation_model.zone_id == zone_id)
            .order_by(observation_model.timestamp.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _zone_names(self, zone_ids: Iterable[str]) -> dict[str, str]:
        """Nombre legible de las zonas, para que la alerta sea accionable."""
        from app.models.zone import Zone

        ids = [z for z in zone_ids if z]
        if not ids:
            return {}
        result = await self._db.execute(
            select(Zone.id, Zone.name).where(Zone.id.in_(ids))
        )
        return {row[0]: row[1] for row in result.all()}

    async def evaluate(
        self, event_id: str, now: Optional[datetime] = None
    ) -> list[ComplianceAlertResponse]:
        """Devuelve una alerta por cada (protocolo, zona) incumplido."""
        now = now or datetime.now(timezone.utc)
        protocols = await self._active_protocols(event_id)
        if not protocols:
            return []

        # Días a resolver: los del protocolo o, si no tiene, la jornada activa.
        day_ids = {p.event_day_id for p in protocols if p.event_day_id}
        if len(day_ids) < len(protocols):
            fallback_day = await self._active_event_day_id(event_id)
            day_ids.add(fallback_day)
        day_ids.discard(None)
        if not day_ids:
            logger.info(
                "Compliance sin jornadas evaluables | event_id=%s | protocolos=%d",
                event_id,
                len(protocols),
            )
            return []

        predictions: dict[str, list[dict]] = {}
        for day_id in day_ids:
            prediction = await self._latest_prediction(day_id)
            predictions[day_id] = _zone_states_from_prediction(prediction) if prediction else []

        zone_types = await self._zone_type_map()
        names = await self._zone_names(
            zone["zone_id"]
            for states in predictions.values()
            for zone in states
            if zone.get("zone_id")
        )

        alerts: list[ComplianceAlertResponse] = []
        for protocol in protocols:
            day_id = protocol.event_day_id or self._single(day_ids)
            states = predictions.get(day_id) or []
            if not states:
                continue
            alerts.extend(
                await self._protocol_alerts(protocol, states, day_id, now, names, zone_types)
            )
        return alerts

    @staticmethod
    def _single(values: set) -> Optional[str]:
        return next(iter(values)) if len(values) == 1 else None

    async def _zone_type_map(self) -> dict[str, Optional[str]]:
        """Mapa ``zone_id -> zone.type`` para evaluar el filtro ``zone_type_id``."""
        from app.models.zone import Zone

        result = await self._db.execute(select(Zone.id, Zone.type))
        return {row[0]: row[1] for row in result.all()}

    async def _protocol_alerts(
        self,
        protocol: ObservationControlProtocol,
        states: list[dict],
        day_id: str,
        now: datetime,
        names: dict[str, str],
        zone_types: dict[str, Optional[str]],
    ) -> list[ComplianceAlertResponse]:
        metric = protocol.trigger_metric
        operator = protocol.trigger_operator
        threshold = Decimal(protocol.threshold_value)
        interval = protocol.action_interval_minutes
        deadline = now - timedelta(minutes=interval)

        alerts: list[ComplianceAlertResponse] = []
        for state in states:
            zone_id = state.get("zone_id")
            if not zone_id:
                continue
            # El protocolo compara por tipo de zona (slug). `Zone.type` ya guarda
            # el slug canonico ("estacionamiento", "escenario", ...).
            if protocol.zone_type_id:
                zone_type_id = zone_types.get(zone_id)
                if zone_type_id != protocol.zone_type_id:
                    continue

            current = _to_decimal(state.get(metric.value))
            if not evaluate_trigger(current, operator, threshold):
                continue

            last_seen = await self._last_observation_at(day_id, zone_id)
            minutes_since = None
            if last_seen is not None:
                aware = last_seen if last_seen.tzinfo else last_seen.replace(tzinfo=timezone.utc)
                if aware > deadline:
                    # Observada dentro de la ventana: el protocolo se cumple.
                    continue
                minutes_since = int((now - aware).total_seconds() // 60)

            overdue = interval if minutes_since is None else minutes_since
            alerts.append(
                ComplianceAlertResponse(
                    protocol_id=protocol.id,
                    protocol_name=protocol.name,
                    event_day_id=day_id,
                    zone_id=zone_id,
                    zone_name=names.get(zone_id),
                    trigger_metric=metric,
                    trigger_operator=operator,
                    threshold_value=threshold,
                    current_value=current,
                    action_interval_minutes=interval,
                    minutes_since_last_observation=minutes_since,
                    overdue_minutes=overdue,
                    severity=(
                        SEVERITY_CRITICAL
                        if minutes_since is None or minutes_since >= interval * 2
                        else SEVERITY_WARNING
                    ),
                    detail=_build_detail(
                        metric, operator, threshold, current, interval, minutes_since
                    ),
                )
            )
        return alerts


_METRIC_LABELS = {
    ObservationTriggerMetric.SATURATION_LEVEL: "la saturación",
    ObservationTriggerMetric.AVAILABILITY: "la disponibilidad",
    ObservationTriggerMetric.ESTIMATED_WAIT: "la espera estimada",
    ObservationTriggerMetric.CONFIDENCE: "la confianza del motor",
    ObservationTriggerMetric.PROJECTED_DENSITY: "la densidad proyectada",
}

_OPERATOR_LABELS = {
    ObservationTriggerOperator.GT: "supera",
    ObservationTriggerOperator.GTE: "supera o iguala",
    ObservationTriggerOperator.LT: "es menor que",
    ObservationTriggerOperator.LTE: "es menor o igual que",
}


def _build_detail(
    metric: ObservationTriggerMetric,
    operator: ObservationTriggerOperator,
    threshold: Decimal,
    current: Optional[Decimal],
    interval: int,
    minutes_since: Optional[int],
) -> str:
    """Frase en español para que el operador no tenga que interpretar números."""
    label = _METRIC_LABELS.get(metric, metric.value)
    comparison = _OPERATOR_LABELS.get(operator, operator.value)
    valor = f"{_trim(current)}" if current is not None else "sin dato"
    if minutes_since is None:
        cuando = "no hay ninguna observación registrada"
    else:
        cuando = f"la última observación fue hace {minutes_since} min"
    return (
        f"{label} está en {valor} y {comparison} el umbral de "
        f"{_trim(threshold)}, pero {cuando} (se esperaba una cada {interval} min)."
    )


def _trim(value: Decimal) -> str:
    """Sin ceros decimales inútiles: 80 en vez de 80.00."""
    normalized = value.normalize()
    sign, digits, exponent = normalized.as_tuple()
    if isinstance(exponent, int) and exponent > 0:
        normalized = normalized.quantize(Decimal(1))
    return str(normalized)