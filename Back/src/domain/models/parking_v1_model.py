"""Modelo especializado Parking V1 (RFC-008).

Implementa la matemática cerrada de `MODELO_PROBABILISTICO_PARKING_V1.md`:
demanda temporal (`V_expected(t) = estimated_vehicles × Intensity`),
permanencia exponencial (`r_t = exp(-Δt/D)`), stock físico `O_t` acotado por
la capacidad total, distribución espacial (`w_i`, `free_i`, expansión/
contracción) e índices determinísticos por zona (`occupancy_ratio`,
`free_ratio`, `free_spaces`), más la demanda no absorbida `unabsorbed_t`.

Es determinista en igualdad de condiciones y no produce probabilidad
calibrada, ranking de alternativas ni recomendaciones (secciones 35 y 40).
No se registra en `ModelSelector`: el Context Engine no lo ejecuta todavía.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final
from uuid import UUID

from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.zone import Zone
from src.domain.models.specialized_model import (
    ModelExecutionContext,
    ModelSpecificResult,
)

DEFAULT_ALPHA: Final = 0.001


@dataclass(frozen=True)
class TemporalPhase:
    """Resultado de la capa temporal de una fase (secciones 29-30)."""

    v_expected: float
    remain: float
    exits: float
    entries: float
    stock: float
    unabsorbed: float


@dataclass(frozen=True)
class ParkingPhaseState:
    """Estado completo de una fase: capa temporal + distribución espacial."""

    index: int
    v_expected: float
    remain: float
    exits: float
    entries: float
    stock: float
    unabsorbed: float
    occupied: Mapping[UUID, float]


class ParkingV1Model:
    """Modelo probabilístico Parking v1 (contrato `SpecializedModel`).

    `execute(context)` computa el estado de la fase actual de la zona
    entregada por el Context Engine. La matemática interna es sistémica
    (multi-zona, multi-fase): `simulate` evalúa la evolución completa y
    `distribute` reparte el stock entre todas las zonas de estacionamiento.
    """

    model_id = "parking_v1"

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
        return zone.type == "estacionamiento"

    def execute(self, context: ModelExecutionContext) -> ModelSpecificResult:
        zone = context.zone
        if not self.supports(zone):
            raise ValueError(
                f"ParkingV1Model no aplica a la zona {zone.id} (type={zone.type!r})"
            )
        intensity = self._resolve_intensity(context)
        delta_hours = self._phase_duration_hours(context.active_event_day_phase)
        v_expected = self.v_expected(context.estimated_vehicles, intensity)
        capacity = zone.capacity
        duration = context.average_parking_duration
        prev = self.initial_occupied([zone])
        prev_stock = prev.get(zone.id, 0.0)
        temporal = self.temporal_step(
            prev_stock, v_expected, float(capacity), delta_hours, duration
        )
        occupied = self.distribute(prev, [zone], temporal.stock)
        zone_occupied = occupied.get(zone.id, temporal.stock)
        occupancy_ratio, free_ratio, free_spaces = self.indices(
            zone_occupied, capacity
        )
        data = {
            "parking_id": str(zone.id),
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

    def v_expected(self, estimated_vehicles: int | None, intensity: float | None) -> float:
        """`V_expected(t) = estimated_vehicles × Intensity` (sección 9)."""
        if estimated_vehicles is None:
            raise ValueError("estimated_vehicles is required")
        if isinstance(estimated_vehicles, bool) or not isinstance(
            estimated_vehicles, int
        ):
            raise TypeError("estimated_vehicles must be an integer")
        if estimated_vehicles < 0:
            raise ValueError("estimated_vehicles must be >= 0")
        if intensity is None:
            raise ValueError("intensity is required")
        if isinstance(intensity, bool) or not isinstance(intensity, (int, float)):
            raise TypeError("intensity must be a number")
        if intensity < 0:
            raise ValueError("intensity must be >= 0")
        return float(estimated_vehicles) * float(intensity)

    def retention(self, delta_hours: float, duration: float) -> float:
        """Proporción del stock previo que continúa: `r_t = exp(-Δt/D)`."""
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
    ) -> TemporalPhase:
        """Capa temporal cerrada de una fase (secciones 29-30).

        `V_expected` representa los VEHÍCULOS QUE LLEGAN durante la fase (no un
        stock objetivo). `remain = O_(t-1) × r`, `S = O_(t-1) - remain`,
        `free = max(0, Σ capacity - remain)`, `A = min(V_expected, free)`
        (llegadas absorbidas, acotadas por la capacidad restante),
        `O = remain + A` (los retenidos NO se reemplazan por las llegadas),
        `unabsorbed = max(0, V_expected - A)` (demanda no absorbida).
        """
        self._require_nonnegative(prev_stock, "prev_stock")
        self._require_nonnegative(v_expected, "v_expected")
        if isinstance(total_capacity, bool) or not isinstance(
            total_capacity, (int, float)
        ):
            raise TypeError("total_capacity must be a number")
        if total_capacity <= 0:
            raise ValueError("total_capacity must be > 0")
        r = self.retention(delta_hours, duration)
        remain = float(prev_stock) * r
        exits = float(prev_stock) - remain
        free_capacity = max(0.0, float(total_capacity) - remain)
        entries = min(float(v_expected), free_capacity)
        stock = remain + entries
        unabsorbed = max(0.0, float(v_expected) - entries)
        return TemporalPhase(
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
        """Distribución espacial del stock (secciones 31-33).

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
        """Estado inicial de la jornada: O₀ = 0 (sección 38).

        Cada jornada operacional de Parking V1 comienza con ocupación cero:
        `occupied₀(z) = 0` para toda zona y `prev_stock = 0`.

        `available_capacity` es un dato operativo del tablero y NO participa
        en la inicialización de la proyección (no se computa
        `capacity - available_capacity` como ocupación inicial).
        """
        return {zone.id: 0.0 for zone in zones}

    def simulate(
        self,
        phases: Sequence[EventDayPhase],
        zones: Sequence[Zone],
        estimated_vehicles: int,
        duration: float,
    ) -> list[ParkingPhaseState]:
        """Evolución temporal + espacial completa por fases.

        `O_0 = 0`: cada jornada comienza con ocupación cero en todas las zonas
        (sección 38). `available_capacity` no participa en la inicialización.
        Las fases se evalúan en orden cronológico. Devuelve un estado por fase,
        reutilizable para los tests de las tablas de las secciones 30 y 31.
        """
        if not phases:
            raise ValueError("phases must not be empty")
        if not zones:
            raise ValueError("zones must not be empty")
        ordered = sorted(phases, key=lambda p: (p.start_min, str(p.id)))
        total_capacity = sum(zone.capacity for zone in zones)
        prev_occupied = self.initial_occupied(zones)
        prev_stock = float(sum(prev_occupied.values()))
        results: list[ParkingPhaseState] = []
        for index, phase in enumerate(ordered, start=1):
            intensity = phase.intensity
            delta_hours = self._phase_duration_hours(phase)
            expected = self.v_expected(estimated_vehicles, intensity)
            temporal = self.temporal_step(
                prev_stock,
                expected,
                float(total_capacity),
                delta_hours,
                duration,
            )
            occupied = self.distribute(prev_occupied, zones, temporal.stock)
            results.append(
                ParkingPhaseState(
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
        """Índices determinísticos de capacidad (sección 35.5)."""
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