"""Modelo probabilístico Baños V1 usando flujo continuo y la Ley de Little.

Por fase calcula `N = max_people × intensity`, `λ = N × u` y `L = λ × W`,
donde `u` (usos/persona-hora) viene de `service_configs` y `W` (horas) es la
permanencia media. Cada fase se distribuye independientemente entre las zonas
físicas, sin acumular ocupación de fases anteriores.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.zone import Zone
from src.domain.models.specialized_model import (
    MissingModelInputError,
    ModelExecutionContext,
    ModelSpecificResult,
)

DEFAULT_ALPHA = 0.001


@dataclass(frozen=True)
class BathroomTemporalPhase:
    """Resultado temporal por fase.

    `remain`, `exits` y `unabsorbed` se conservan para compatibilidad con
    consumidores existentes, pero ya no participan en el cálculo. `v_expected`
    y `entries` representan los usos esperados durante la fase.
    """

    v_expected: float
    remain: float
    exits: float
    entries: float
    stock: float
    unabsorbed: float


@dataclass(frozen=True)
class BathroomPhaseState:
    """Estado de una fase: métricas de flujo y distribución espacial."""

    index: int
    v_expected: float
    remain: float
    exits: float
    entries: float
    stock: float
    unabsorbed: float
    occupied: Mapping[UUID, float]


class BathroomV1Model:
    """Modelo probabilístico Baños v1 (contrato `SpecializedModel`).

    `execute(context)` computa el estado de la fase actual de la zona
    entregada por el Context Engine. La matemática interna es sistémica
    (multi-zona, multi-fase): `simulate` evalúa la evolución completa y
    `distribute` reparte el stock entre todas las zonas de servicios/baños.

    Faltan datos (sin `average_duration_min`, sin `attendance_level` o sin
    `bathroom_use_rate_per_person_hour`) NO se
    inventan: `execute` eleva `MissingModelInputError` y la etapa 4 degrada esa
    zona sola, dejándola sin `occupancy_ratio` y por lo tanto sin
    `saturation_level`, como cualquier zona sin modelo.
    """

    model_id = "bathroom_v1"

    def __init__(
        self,
        alpha: float = DEFAULT_ALPHA,
        use_rate_per_person_hour: float | None = None,
    ) -> None:
        if isinstance(alpha, bool) or not isinstance(alpha, (int, float)):
            raise TypeError("alpha must be a number")
        if alpha < 0:
            raise ValueError("alpha must be >= 0")
        self._alpha = float(alpha)
        if use_rate_per_person_hour is not None:
            self._validate_use_rate(use_rate_per_person_hour)
        self._use_rate_per_person_hour = (
            None
            if use_rate_per_person_hour is None
            else float(use_rate_per_person_hour)
        )

    @property
    def alpha(self) -> float:
        return self._alpha

    @property
    def use_rate_per_person_hour(self) -> float | None:
        return self._use_rate_per_person_hour

    def supports(self, zone: Zone) -> bool:
        return zone.type == "servicios" and zone.subtipo == "banos"

    def execute(self, context: ModelExecutionContext) -> ModelSpecificResult:
        zone = context.zone
        if not self.supports(zone):
            raise ValueError(
                f"BathroomV1Model no aplica a la zona {zone.id} "
                f"(type={zone.type!r}, subtipo={zone.subtipo!r})"
            )
        intensity = self._resolve_intensity(context)
        delta_hours = self._phase_duration_hours(context.active_event_day_phase)
        max_people = self._require_max_people(context.attendance_level)
        duration_hours = self.duration_hours(context.average_duration_min)
        people_present = self.people_present(max_people, intensity)
        arrival_rate = self.arrival_rate_per_hour(people_present)
        capacity = zone.capacity
        prev = self.initial_occupied([zone])
        temporal = self.temporal_step(
            arrival_rate, delta_hours, duration_hours
        )
        occupied = self.distribute(prev, [zone], temporal.stock)
        zone_occupied = occupied.get(zone.id, temporal.stock)
        occupancy_ratio, free_ratio, free_spaces = self.indices(
            zone_occupied, capacity
        )
        data = {
            "bathroom_id": str(zone.id),
            "occupied": zone_occupied,
            "capacity": capacity,
            "occupancy_ratio": occupancy_ratio,
            "free_ratio": free_ratio,
            "free_spaces": free_spaces,
            "distance": self._zone_distance(zone, context.reference_point_distance),
            "unabsorbed": temporal.unabsorbed,
        }
        return ModelSpecificResult(
            model_id=self.model_id, zone_id=zone.id, data=data
        )

    def people_present(
        self, max_people: int | None, intensity: float | None
    ) -> float:
        """Calcula `N = max_people × intensity` en personas presentes."""
        if max_people is None:
            raise ValueError("max_people is required")
        if isinstance(max_people, bool) or not isinstance(max_people, int):
            raise TypeError("max_people must be an integer")
        if max_people < 0:
            raise ValueError("max_people must be >= 0")
        if intensity is None:
            raise ValueError("intensity is required")
        if isinstance(intensity, bool) or not isinstance(intensity, (int, float)):
            raise TypeError("intensity must be a number")
        if intensity < 0:
            raise ValueError("intensity must be >= 0")
        return float(max_people) * float(intensity)

    def arrival_rate_per_hour(self, people_present: float) -> float:
        """Calcula `λ = N × u` en usos de baño por hora."""
        self._require_nonnegative(people_present, "people_present")
        return float(people_present) * self._require_use_rate()

    def concurrent_occupancy(
        self, arrival_rate_per_hour: float, duration_hours: float
    ) -> float:
        """Calcula `L = λ × W` en personas simultáneas."""
        self._require_nonnegative(arrival_rate_per_hour, "arrival_rate_per_hour")
        self._require_positive(duration_hours, "duration_hours")
        return float(arrival_rate_per_hour) * float(duration_hours)

    def duration_hours(self, average_duration_min: float | None) -> float:
        """Convierte la permanencia de MINUTOS a HORAS: `D_hours = min / 60.0`.

        La unidad interna del modelo (Δt de `retention`) es la hora; la
        conversión ocurre aquí para coincidir con `_phase_duration_hours`.
        """
        if average_duration_min is None:
            raise MissingModelInputError(
                "average_duration_min is required (sin fila en service_configs "
                "para el tipo de zona de banos); la zona degrada sin saturacion"
            )
        if isinstance(average_duration_min, bool) or not isinstance(
            average_duration_min, (int, float)
        ):
            raise TypeError("average_duration_min must be a number")
        if average_duration_min <= 0:
            raise ValueError("average_duration_min must be > 0")
        return float(average_duration_min) / 60.0

    def temporal_step(
        self,
        arrival_rate_per_hour: float,
        delta_hours: float,
        duration_hours: float,
    ) -> BathroomTemporalPhase:
        """Calcula `L = λ × W`, sin retención ni acumulación entre fases.

        `delta_hours` solo permite conservar el total de usos esperados de la
        fase; no interviene en la ocupación simultánea.
        """
        self._require_nonnegative(arrival_rate_per_hour, "arrival_rate_per_hour")
        self._require_positive(delta_hours, "delta_hours")
        stock = self.concurrent_occupancy(arrival_rate_per_hour, duration_hours)
        expected_uses = float(arrival_rate_per_hour) * float(delta_hours)
        return BathroomTemporalPhase(
            v_expected=expected_uses,
            remain=0.0,
            exits=0.0,
            entries=expected_uses,
            stock=stock,
            unabsorbed=0.0,
        )

    def distribute(
        self,
        prev_occupied: Mapping[UUID, float],
        zones: Sequence[Zone],
        stock: float,
        alpha: float | None = None,
    ) -> Mapping[UUID, float]:
        """Distribución espacial del stock (espejo de Parking V1 §§31-33).

        Solo mueve el incremento neto `Δ = O_t - Σ occupied_i(t-1)`:
        expansión proporcional a `w_i` con tope `free_i` y redistribución
        iterativa; contracción retirando desde la zona de menor `w_i`.
        Conserva `Σ occupied_i(t) = O_t`.
        """
        resolved_alpha = self._alpha if alpha is None else alpha
        if isinstance(resolved_alpha, bool) or not isinstance(
            resolved_alpha, (int, float)
        ):
            raise TypeError("alpha must be a number")
        if resolved_alpha < 0:
            raise ValueError("alpha must be >= 0")
        self._require_nonnegative(stock, "stock")
        if not zones:
            raise ValueError("zones must not be empty")

        current: dict[UUID, float] = {}
        for zone in zones:
            prev = prev_occupied.get(zone.id, 0.0)
            self._require_nonnegative(prev, f"occupied_{zone.id}")
            current[zone.id] = min(float(prev), float(zone.capacity))

        total_prev = sum(current.values())
        delta = float(stock) - total_prev

        if delta > 0:
            self._expand(current, zones, delta, float(resolved_alpha))
        elif delta < 0:
            self._contract(current, zones, -delta, float(resolved_alpha))

        for zone in zones:
            current[zone.id] = min(
                max(current[zone.id], 0.0), float(zone.capacity)
            )
        return {zone.id: current[zone.id] for zone in zones}

    def initial_occupied(
        self, zones: Sequence[Zone]
    ) -> dict[UUID, float]:
        """Estado inicial de la jornada: O₀ = 0 (espejo de Parking V1 §38).

        Cada jornada operacional de Baños V1 comienza con ocupación cero:
        `occupied₀(z) = 0` para toda zona y `prev_stock = 0`.
        """
        return {zone.id: 0.0 for zone in zones}

    def simulate(
        self,
        phases: Sequence[EventDayPhase],
        zones: Sequence[Zone],
        max_people: int,
        duration_hours: float,
    ) -> list[BathroomPhaseState]:
        """Evolución temporal + espacial completa por fases.

        Cada fase se calcula y distribuye desde ocupación cero, sin transferir
        estado espacial de la fase anterior.
        """
        if not phases:
            raise ValueError("phases must not be empty")
        if not zones:
            raise ValueError("zones must not be empty")
        ordered = sorted(phases, key=lambda p: (p.start_min, str(p.id)))
        use_rate = self._require_use_rate()
        results: list[BathroomPhaseState] = []
        for index, phase in enumerate(ordered, start=1):
            intensity = phase.intensity
            delta_hours = self._phase_duration_hours(phase)
            people_present = self.people_present(max_people, intensity)
            arrival_rate = people_present * use_rate
            temporal = self.temporal_step(
                arrival_rate,
                delta_hours,
                duration_hours,
            )
            occupied = self.distribute({}, zones, temporal.stock)
            results.append(
                BathroomPhaseState(
                    index=index,
                    v_expected=temporal.v_expected,
                    remain=temporal.remain,
                    exits=temporal.exits,
                    entries=temporal.entries,
                    stock=temporal.stock,
                    unabsorbed=temporal.unabsorbed,
                    occupied=dict(occupied),
                )
            )
        return results

    def indices(
        self, occupied: float, capacity: int
    ) -> tuple[float, float, float]:
        """Índices determinísticos de capacidad (espejo de Parking V1 §35.5)."""
        self._require_nonnegative(occupied, "occupied")
        if isinstance(capacity, bool) or not isinstance(capacity, int):
            raise TypeError("capacity must be an integer")
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        clamped = min(float(occupied), float(capacity))
        occupancy_ratio = clamped / float(capacity)
        free_ratio = 1.0 - occupancy_ratio
        free_spaces = float(capacity) - clamped
        return occupancy_ratio, free_ratio, free_spaces

    def _expand(
        self,
        current: dict[UUID, float],
        zones: Sequence[Zone],
        delta: float,
        alpha: float,
    ) -> None:
        remaining = delta
        while remaining > 1e-9:
            eligible = [z for z in zones if current[z.id] < z.capacity]
            if not eligible:
                break
            total_weight = sum(self._weight(z, alpha) for z in eligible)
            if total_weight <= 0:
                break
            placed_round = 0.0
            for zone in eligible:
                weight = self._weight(zone, alpha)
                free = float(zone.capacity) - current[zone.id]
                target = remaining * weight / total_weight
                placed = min(target, free)
                current[zone.id] += placed
                placed_round += placed
            remaining -= placed_round
            if placed_round <= 0:
                break

    def _contract(
        self,
        current: dict[UUID, float],
        zones: Sequence[Zone],
        amount: float,
        alpha: float,
    ) -> None:
        remaining = amount
        order = sorted(zones, key=lambda z: self._weight(z, alpha))
        for zone in order:
            if remaining <= 1e-9:
                break
            removed = min(current[zone.id], remaining)
            current[zone.id] -= removed
            remaining -= removed

    def _weight(self, zone: Zone, alpha: float) -> float:
        distance = zone.reference_point_distance
        if distance is None:
            return 1.0
        return 1.0 / (1.0 + alpha * distance)

    @staticmethod
    def _zone_distance(
        zone: Zone, transported: float | None
    ) -> float | None:
        if transported is not None:
            return transported
        return zone.reference_point_distance

    @staticmethod
    def _resolve_intensity(context: ModelExecutionContext) -> float | None:
        if context.intensity is not None:
            return context.intensity
        phase = context.active_event_day_phase
        if phase is None:
            return None
        return phase.intensity

    @staticmethod
    def _phase_duration_hours(phase: EventDayPhase) -> float:
        return (phase.end_min - phase.start_min) / 60.0

    @staticmethod
    def _require_nonnegative(value: float, name: str) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be a number")
        if value < 0:
            raise ValueError(f"{name} must be >= 0")

    @staticmethod
    def _require_positive(value: float, name: str) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be a number")
        if value <= 0:
            raise ValueError(f"{name} must be > 0")

    @staticmethod
    def _validate_use_rate(value: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("use_rate_per_person_hour must be a number")
        if not math.isfinite(float(value)):
            raise ValueError("use_rate_per_person_hour must be finite")
        if value < 0:
            raise ValueError("use_rate_per_person_hour must be >= 0")

    def _require_use_rate(self) -> float:
        if self._use_rate_per_person_hour is None:
            raise MissingModelInputError(
                "bathroom_use_rate_per_person_hour is required from "
                "service_configs; Bathroom V1 cannot calculate without it"
            )
        return self._use_rate_per_person_hour

    @staticmethod
    def _require_max_people(attendance_level: object | None) -> int:
        if attendance_level is None:
            raise MissingModelInputError(
                "attendance_level is required (event_days.attendance_level_id "
                "en NULL); la zona degrada sin saturacion"
            )
        max_people = getattr(attendance_level, "max_people", None)
        if max_people is None:
            raise MissingModelInputError(
                "attendance_level.max_people is required (NULL no permitido); "
                "la zona degrada sin saturacion"
            )
        if isinstance(max_people, bool) or not isinstance(max_people, int):
            raise TypeError("max_people must be an integer")
        if max_people < 0:
            raise ValueError("max_people must be >= 0")
        return max_people