from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operational_event import OperationalEvent
from app.models.zone import Zone
from app.models.zone_type import ZoneType
from src.application.learning.metric_result import MetricResult
from src.infrastructure.persistence.models import (
    OperationalObservationModel,
    PredictionModel,
    ZoneBehaviorModel,
)
from src.infrastructure.persistence.repositories.operational_observation_repository import (
    SQLOperationalObservationRepository,
)
from src.infrastructure.persistence.repositories.prediction_repository import (
    SQLPredictionRepository,
)

STATUS_ENABLED = "ENABLED"
STATUS_LIMITED = "LIMITED"
STATUS_BLOCKED = "BLOCKED"

MATCH_WINDOW_MINUTES = 30

SUBTIPO_TO_ZONE_TYPE_SLUG = {
    "banos": "bano",
    "hidratacion": "hidratacion",
    "descanso": "descanso",
}


class MetricService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._prediction_repo = SQLPredictionRepository(db)
        self._observation_repo = SQLOperationalObservationRepository(db)

    async def calculate_all(
        self,
        event_day_id: str,
        phase_id: str,
    ) -> list[MetricResult]:
        return [
            await self.calculate_density_deviation(event_day_id),
            await self.calculate_incident_frequency(event_day_id),
            self.calculate_phase_transition_latency(),
            await self.calculate_zone_behavior_adherence(event_day_id, phase_id),
        ]

    async def calculate_density_deviation(self, event_day_id: str) -> MetricResult:
        predictions = await self._prediction_repo.find_by_event_day_id(event_day_id)
        if not predictions:
            return MetricResult(
                name="density_deviation",
                display_name="Desviación de Densidad",
                status=STATUS_BLOCKED,
                value=None,
                reason="No hay predicciones para el event_day.",
                data_points=0,
                limitations=self._density_deviation_limitations(),
            )

        observations = await self._observation_repo.find_all(event_day_id=event_day_id)
        if not observations:
            return MetricResult(
                name="density_deviation",
                display_name="Desviación de Densidad",
                status=STATUS_BLOCKED,
                value=None,
                reason="Hay predicciones pero no observaciones contemporáneas para el event_day.",
                data_points=0,
                limitations=self._density_deviation_limitations(),
            )

        zone_ids = {str(state.zone_id) for prediction in predictions for state in prediction.zone_states}
        zone_ids |= {observation.zone_id for observation in observations}
        zones = await self._load_zones_by_id(zone_ids)

        window = timedelta(minutes=MATCH_WINDOW_MINUTES)
        deviations: list[float] = []
        for prediction in predictions:
            for state in prediction.zone_states:
                zone_key = str(state.zone_id)
                capacity = self._capacity_of(zones, zone_key)
                if capacity <= 0:
                    continue
                for observation in observations:
                    if observation.zone_id != zone_key:
                        continue
                    delta = observation.timestamp - prediction.timestamp
                    if abs(delta.total_seconds()) > window.total_seconds():
                        continue
                    deviations.append(
                        abs(state.projected_density - observation.observed_density) / capacity,
                    )

        if not deviations:
            return MetricResult(
                name="density_deviation",
                display_name="Desviación de Densidad",
                status=STATUS_BLOCKED,
                value=None,
                reason="Hay predicciones y observaciones pero ninguna coincide en zona y ventana temporal (±30 min).",
                data_points=0,
                limitations=self._density_deviation_limitations(),
            )

        average = sum(deviations) / len(deviations)
        return MetricResult(
            name="density_deviation",
            display_name="Desviación de Densidad",
            status=STATUS_ENABLED,
            value=average,
            reason="Promedio de |projected_density - observed_density| / capacity con coincidencia en zona y ±30 min.",
            data_points=len(deviations),
            limitations=self._density_deviation_limitations(),
        )

    @staticmethod
    def _density_deviation_limitations() -> list[str]:
        return [
            "Requiere coincidencia temporal (±30 min) y espacial entre predicciones y observaciones.",
            "La ventana de coincidencia temporal (±30 min) es un default; debe definirse formalmente.",
            "El denominador usa zones.capacity; las zonas sin capacity > 0 se omiten.",
            "No distingue predicciones solapadas para la misma zona y ventana temporal.",
        ]

    async def calculate_incident_frequency(self, event_day_id: str) -> MetricResult:
        stmt = select(OperationalEvent).where(
            OperationalEvent.event_day_id == event_day_id,
        )
        events = (await self._db.execute(stmt)).scalars().all()

        limitations = [
            "El denominador (horas totales) se calcula desde el rango de timestamps de los eventos.",
            "No distingue entre incidentes superpuestos.",
            "Si el rango temporal de eventos es nulo o cero, la métrica queda BLOCKED.",
        ]
        if not events:
            return MetricResult(
                name="incident_frequency",
                display_name="Frecuencia de Incidentes",
                status=STATUS_BLOCKED,
                value=None,
                reason="No hay operational_events para el event_day.",
                data_points=0,
                limitations=limitations,
            )

        incidents = [event for event in events if event.is_incident]
        if not incidents:
            return MetricResult(
                name="incident_frequency",
                display_name="Frecuencia de Incidentes",
                status=STATUS_LIMITED,
                value=0.0,
                reason="Hay eventos pero ningún incidente (is_incident = true); frecuencia 0.",
                data_points=0,
                limitations=limitations,
            )

        start = min(event.start_timestamp for event in events)
        end = max(event.end_timestamp for event in events)
        hours = (end - start).total_seconds() / 3600.0
        if hours <= 0:
            return MetricResult(
                name="incident_frequency",
                display_name="Frecuencia de Incidentes",
                status=STATUS_BLOCKED,
                value=None,
                reason="El rango temporal de los eventos es nulo o cero; denominador inválido.",
                data_points=0,
                limitations=limitations,
            )

        frequency = len(incidents) / hours
        return MetricResult(
            name="incident_frequency",
            display_name="Frecuencia de Incidentes",
            status=STATUS_ENABLED,
            value=frequency,
            reason="Cantidad de incidentes dividida por el rango de horas de los eventos.",
            data_points=len(incidents),
            limitations=limitations,
        )

    @staticmethod
    def calculate_phase_transition_latency() -> MetricResult:
        return MetricResult(
            name="phase_transition_latency",
            display_name="Latencia de Transición de Fase",
            status=STATUS_BLOCKED,
            value=None,
            reason="No existe fuente de observación de transición de fase; RFC-006 no define cómo observar la transición efectiva.",
            data_points=0,
            limitations=[
                "No existe fuente de observación de transición de fase.",
                "RFC-006 no define cómo observar la transición efectiva.",
                "La métrica queda BLOCKED de forma permanente hasta definir la fuente de observación.",
            ],
        )

    async def calculate_zone_behavior_adherence(
        self,
        event_day_id: str,
        phase_id: str,
    ) -> MetricResult:
        behaviors = await self._load_behaviors_by_phase(phase_id)

        limitations = [
            "Fórmula v1 provisional.",
            "No incluye accumulated_impact (Stage 3 usa: projected = capacity × density_factor + accumulated_impact).",
            "Se validará contra Stage 3 cuando haya datos contemporáneos.",
            "Requiere coincidencia temporal entre observaciones y fase operativa.",
            "La resolución zone_id → zone_type_id usa zones.type como slug con fallback de subtipo.",
        ]
        if not behaviors:
            return MetricResult(
                name="zone_behavior_adherence",
                display_name="Adherencia a ZoneBehavior",
                status=STATUS_BLOCKED,
                value=None,
                reason="No hay zone_behaviors para la fase indicada.",
                data_points=0,
                limitations=limitations,
            )

        observations = await self._observation_repo.find_all(event_day_id=event_day_id)
        if not observations:
            return MetricResult(
                name="zone_behavior_adherence",
                display_name="Adherencia a ZoneBehavior",
                status=STATUS_BLOCKED,
                value=None,
                reason="Hay zone_behaviors pero no observaciones para el event_day.",
                data_points=0,
                limitations=limitations,
            )

        zones = await self._load_zones_by_id({o.zone_id for o in observations})
        zone_type_ids = await self._load_zone_type_ids_by_slug()

        scores: list[float] = []
        for observation in observations:
            zone = zones.get(observation.zone_id)
            if zone is None or zone.capacity <= 0:
                continue
            zone_type_id = self._resolve_zone_type_id(
                zone.type or "",
                zone.subtipo,
                zone_type_ids,
            )
            if zone_type_id is None:
                continue
            behavior = behaviors.get(zone_type_id)
            if behavior is None:
                continue
            expected = zone.capacity * behavior.density_factor
            score = 1.0 - abs(observation.observed_density - expected) / zone.capacity
            scores.append(score)

        if not scores:
            return MetricResult(
                name="zone_behavior_adherence",
                display_name="Adherencia a ZoneBehavior",
                status=STATUS_BLOCKED,
                value=None,
                reason="Hay zone_behaviors y observaciones pero ninguna observación tiene comportamiento aplicable de la fase.",
                data_points=0,
                limitations=limitations,
            )

        average = sum(scores) / len(scores)
        return MetricResult(
            name="zone_behavior_adherence",
            display_name="Adherencia a ZoneBehavior",
            status=STATUS_ENABLED,
            value=average,
            reason="Promedio de 1 - |observed_density - capacity × density_factor| / capacity.",
            data_points=len(scores),
            limitations=limitations,
        )

    @staticmethod
    def _capacity_of(zones: dict[str, Zone], zone_key: str) -> int:
        zone = zones.get(zone_key)
        if zone is None:
            return 0
        return zone.capacity or 0

    @staticmethod
    def _resolve_zone_type_id(
        zone_type: str,
        subtipo: str | None,
        zone_type_ids: dict[str, str],
    ) -> str | None:
        direct = zone_type_ids.get(zone_type)
        if direct is not None:
            return direct
        slug = SUBTIPO_TO_ZONE_TYPE_SLUG.get((subtipo or "").lower())
        if slug is None:
            return None
        return zone_type_ids.get(slug)

    async def _load_zones_by_id(self, zone_ids: set[str]) -> dict[str, Zone]:
        if not zone_ids:
            return {}
        stmt = select(Zone).where(Zone.id.in_(zone_ids))
        result = await self._db.execute(stmt)
        return {str(zone.id): zone for zone in result.scalars().all()}

    async def _load_zone_type_ids_by_slug(self) -> dict[str, str]:
        result = await self._db.execute(select(ZoneType))
        return {zone_type.slug: str(zone_type.id) for zone_type in result.scalars().all()}

    async def _load_behaviors_by_phase(
        self,
        phase_id: str,
    ) -> dict[str, ZoneBehaviorModel]:
        stmt = select(ZoneBehaviorModel).where(
            ZoneBehaviorModel.operational_phase_id == phase_id,
        )
        result = await self._db.execute(stmt)
        return {str(behavior.zone_type_id): behavior for behavior in result.scalars().all()}