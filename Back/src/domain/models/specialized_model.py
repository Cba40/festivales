"""Contrato de dominio para modelos especializados.

Define la abstracción por la cual el Context Engine selecciona y ejecuta un
modelo especializado sin conocer su matemática interna. Este contrato NO
contiene fórmulas de ningún modelo concreto (p. ej. Parking V1): la matemática
pertenece exclusivamente a la especificación del modelo (`MODELO_PROBABILISTICO_PARKING_V1.md`).
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.zone import Zone
from src.domain.entities.zone_behavior import FlowRestriction


class ModelExecutionContext:
    """Contexto territorial común resuelto que el Context Engine entrega al modelo.

    El modelo determina si y cómo utiliza estos datos; el Context Engine no
    impone ninguna fórmula universal de cálculo sobre ellos.
    """

    def __init__(
        self,
        timestamp: datetime,
        zone: Zone,
        active_operational_phase: OperationalPhase,
        active_event_day_phase: EventDayPhase,
        intensity: float | None,
        attendance_level: AttendanceLevel | None,
        event_impact: int,
        density_factor: float | None,
        active_restriction: FlowRestriction | None,
        reference_point_distance: float | None,
    ) -> None:
        self._timestamp = timestamp
        self._zone = zone
        self._active_operational_phase = active_operational_phase
        self._active_event_day_phase = active_event_day_phase
        self._intensity = intensity
        self._attendance_level = attendance_level
        self._event_impact = event_impact
        self._density_factor = density_factor
        self._active_restriction = active_restriction
        self._reference_point_distance = reference_point_distance

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def zone(self) -> Zone:
        return self._zone

    @property
    def active_operational_phase(self) -> OperationalPhase:
        return self._active_operational_phase

    @property
    def active_event_day_phase(self) -> EventDayPhase:
        return self._active_event_day_phase

    @property
    def intensity(self) -> float | None:
        return self._intensity

    @property
    def attendance_level(self) -> AttendanceLevel | None:
        return self._attendance_level

    @property
    def event_impact(self) -> int:
        return self._event_impact

    @property
    def density_factor(self) -> float | None:
        return self._density_factor

    @property
    def active_restriction(self) -> FlowRestriction | None:
        return self._active_restriction

    @property
    def reference_point_distance(self) -> float | None:
        return self._reference_point_distance

    def __repr__(self) -> str:
        return (
            f"ModelExecutionContext(timestamp={self._timestamp!r}, "
            f"zone_id={self._zone.id!r}, "
            f"active_operational_phase={self._active_operational_phase!r}, "
            f"active_event_day_phase={self._active_event_day_phase!r}, "
            f"intensity={self._intensity!r}, "
            f"attendance_level={self._attendance_level!r}, "
            f"event_impact={self._event_impact!r}, "
            f"density_factor={self._density_factor!r}, "
            f"active_restriction={self._active_restriction!r}, "
            f"reference_point_distance={self._reference_point_distance!r})"
        )


class ModelSpecificResult:
    """Resultado territorial específico devuelto por un modelo especializado.

    `data` transporta los atributos específicos del modelo. Estos atributos NO
    son campos universales obligatorios de TerritorialPrediction: su schema
    definitivo queda abierto en RFC-004 §10.7.
    """

    def __init__(
        self,
        model_id: str,
        zone_id: UUID,
        data: Mapping[str, object],
    ) -> None:
        self._model_id = model_id
        self._zone_id = zone_id
        self._data = dict(data)

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def zone_id(self) -> UUID:
        return self._zone_id

    @property
    def data(self) -> Mapping[str, object]:
        return dict(self._data)

    def __repr__(self) -> str:
        return (
            f"ModelSpecificResult(model_id={self._model_id!r}, "
            f"zone_id={self._zone_id!r}, data={self._data!r})"
        )


@runtime_checkable
class SpecializedModel(Protocol):
    """Contrato de un modelo especializado ejecutable por el Context Engine."""

    model_id: str

    def supports(self, zone: Zone) -> bool:
        """Determina si este modelo aplica al dominio/zona evaluado."""
        ...

    def execute(self, context: ModelExecutionContext) -> ModelSpecificResult:
        """Aplica la matemática específica del modelo y devuelve su resultado."""
        ...