"""Modelo probabilístico Baños V1 (contrato `SpecializedModel`).

Baños V1 usa un modelo de FLUJO basado en Little's law, NO de stock
concurrente (a diferencia de Parking V1):

    concurrent_occupancy = v_expected × (D_hours / Δt_hours)

Inputs:
* Magnitud base: `AttendanceLevel.max_people` (llegadas esperadas durante la
  fase: `v_expected = max_people × intensity`).
* Permanencia: `ServiceConfig.average_duration_min` en MINUTOS, convertida a
  horas internamente (`D_hours = average_duration_min / 60.0`) para coincidir
  con `_phase_duration_hours` (Δt en horas).

Con permanencias cortas (minutos) y fases de horas, `exp(-Δt/D) ≈ 0` entre
fases: el stock de una fase NO se conserva hacia la siguiente (alta rotación).
`stock` representa personas SIMULTÁNEAS estimadas por Little's law (no
acumulado entre fases) y `unabsorbed` es la demanda que excede la capacidad de
servicio de la fase (`capacity × Δt / D`); NO incrementa stock ni occupied.

La matemática interna es sistémica (multi-zona, multi-fase): `simulate` evalúa
la evolución completa y `distribute` reparte la ocupación concurrente entre
todas las zonas de servicios/baños.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.zone import Zone
from src.domain.models.specialized_model import (
    ModelExecutionContext,
    ModelSpecificResult,
)

# Baños V1 usa modelo de FLUJO (Little's law), no de STOCK.
# concurrent_occupancy = llegadas × permanencia / duración_fase.
# Esto difiere de Parking V1 que acumula stock entre fases.
DEFAULT_ALPHA = 0.001


@dataclass(frozen=True)
class BathroomTemporalPhase:
    """Capa temporal de una fase: demanda esperada, retención, stock."""

    v_expected: float
    remain: float
    exits: float
    entries: float
    stock: float
    unabsorbed: float


@dataclass(frozen=True)
class BathroomPhaseState:
    """Estado completo de una fase: capa temporal + distribución espacial."""

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
    """

    model_id = "bathroom_v1"

    def __init__(self, alpha: float = DEFAULT_ALPHA) -> None:
        if isinstance(alpha, bool) or not isinstance(alpha, (int, float)):
            raise TypeError("alpha must be a number")
        if alpha < 0:
            raise ValueError("alpha must be >= 0")
        self._alpha = float(alpha)

    @property
    def alpha(self) -> float:
        return self._alpha

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
        v_expected = self.v_expected(max_people, intensity)
        capacity = zone.capacity
        prev = self.initial_occupied([zone])
        prev_stock = prev.get(zone.id, 0.0)
        temporal = self.temporal_step(
            prev_stock, v_expected, float(capacity), delta_hours, duration_hours
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

    def v_expected(self, max_people: int | None, intensity: float | None) -> float:
        """`V_expected(t) = max_people × Intensity` (espejo de Parking V1 §9)."""
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

    def duration_hours(self, average_duration_min: float | None) -> float:
        """Convierte la permanencia de MINUTOS a HORAS: `D_hours = min / 60.0`.

        La unidad interna del modelo (Δt de `retention`) es la hora; la
        conversión ocurre aquí para coincidir con `_phase_duration_hours`.
        """
        if average_duration_min is None:
            raise ValueError("average_duration_min is required")
        if isinstance(average_duration_min, bool) or not isinstance(
            average_duration_min, (int, float)
        ):
            raise TypeError("average_duration_min must be a number")
        if average_duration_min <= 0:
            raise ValueError("average_duration_min must be > 0")
        return float(average_duration_min) / 60.0

    def retention(self, delta_hours: float, duration: float) -> float:
        """Proporción del stock previo que continúa: `r_t = exp(-Δt/D)`.

        Con permanencias cortas (minutos) y fases de horas, `r_t ≈ 0`: el stock
        de una fase prácticamente no se conserva hacia la siguiente.
        """
        if isinstance(delta_hours, bool) or not isinstance(
            delta_hours, (int, float)
        ):
            raise TypeError("delta_hours must be a number")
        if delta_hours < 0:
            raise ValueError("delta_hours must be >= 0")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)):
            raise TypeError("duration must be a number")
        if duration <= 0:
            raise ValueError("duration must be > 0")
        if delta_hours == 0:
            return 1.0
        return math.exp(-float(delta_hours) / float(duration))

    def temporal_step(
        self,
        prev_stock: float,
        v_expected: float,
        total_capacity: float,
        delta_hours: float,
        duration: float,
    ) -> BathroomTemporalPhase:
        """Capa temporal de una fase — modelo de FLUJO (Little's law).

        `V_expected` representa las PERSONAS QUE LLEGAN durante la fase (no un
        stock objetivo). Para servicios de alta rotación (D ≪ Δt):

        * `concurrent_occupancy = V_expected × (D / Δt)` — personas
          simultáneas estimadas por Little's law.
        * `stock = concurrent_occupancy` — NO acumula entre fases (no es
          `remain + entries`).
        * `service_capacity_phase = total_capacity × (Δt / D)` — cuántas
          personas puede atender el sistema completo durante la fase.
        * `entries = min(V_expected, service_capacity_phase)` — llegadas
          efectivamente absorbidas por la capacidad de servicio.
        * `unabsorbed = max(0, V_expected - entries)` — demanda NO atendida;
          NO incrementa stock ni occupied.
        * `remain = O_(t-1) × r` con `r = exp(-Δt/D)` — retención entre
          fases (≈ 0 cuando D ≪ Δt; no se hardcodea 0).

        NOTA: `remain` y `exits` se calculan por compatibilidad estructural con
        `BathroomTemporalPhase`, pero NO intervienen en `stock`, `occupied` ni
        `unabsorbed` en el régimen de alta rotación. `stock` =
        `concurrent_occupancy` directamente (Little's law), NO es
        `remain + entries`.
        """
        self._require_nonnegative(prev_stock, "prev_stock")
        self._require_nonnegative(v_expected, "v_expected")
        if isinstance(total_capacity, bool) or not isinstance(
            total_capacity, (int, float)
        ):
            raise TypeError("total_capacity must be a number")
        if total_capacity <= 0:
            raise ValueError("total_capacity must be > 0")
        if isinstance(delta_hours, bool) or not isinstance(
            delta_hours, (int, float)
        ):
            raise TypeError("delta_hours must be a number")
        if delta_hours <= 0:
            raise ValueError("delta_hours must be > 0")

        concurrent_occupancy = float(v_expected) * (
            float(duration) / float(delta_hours)
        )
        service_capacity_phase = float(total_capacity) * (
            float(delta_hours) / float(duration)
        )
        entries = min(float(v_expected), service_capacity_phase)
        unabsorbed = max(0.0, float(v_expected) - entries)

        r = self.retention(delta_hours, duration)
        remain = float(prev_stock) * r
        exits = float(prev_stock) - remain

        stock = concurrent_occupancy
        return BathroomTemporalPhase(
            v_expected=float(v_expected),
            remain=remain,
            exits=exits,
            entries=entries,
            stock=stock,
            unabsorbed=unabsorbed,
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

        `O_0 = 0`: cada jornada comienza con ocupación cero en todas las zonas
        (espejo de Parking V1 §38). Las fases se evalúan en orden cronológico.
        Devuelve un estado por fase, reutilizable para los tests.
        """
        if not phases:
            raise ValueError("phases must not be empty")
        if not zones:
            raise ValueError("zones must not be empty")
        ordered = sorted(phases, key=lambda p: (p.start_min, str(p.id)))
        total_capacity = sum(zone.capacity for zone in zones)
        prev_occupied = self.initial_occupied(zones)
        prev_stock = float(sum(prev_occupied.values()))
        results: list[BathroomPhaseState] = []
        for index, phase in enumerate(ordered, start=1):
            intensity = phase.intensity
            delta_hours = self._phase_duration_hours(phase)
            expected = self.v_expected(max_people, intensity)
            temporal = self.temporal_step(
                prev_stock,
                expected,
                float(total_capacity),
                delta_hours,
                duration_hours,
            )
            occupied = self.distribute(prev_occupied, zones, temporal.stock)
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
            prev_stock = temporal.stock
            prev_occupied = occupied
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
    def _require_max_people(attendance_level: object | None) -> int:
        if attendance_level is None:
            raise ValueError("attendance_level is required")
        max_people = getattr(attendance_level, "max_people", None)
        if max_people is None:
            raise ValueError(
                "attendance_level.max_people is required (NULL no permitido)"
            )
        if isinstance(max_people, bool) or not isinstance(max_people, int):
            raise TypeError("max_people must be an integer")
        if max_people < 0:
            raise ValueError("max_people must be >= 0")
        return max_people