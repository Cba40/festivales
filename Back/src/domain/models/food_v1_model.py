"""Modelo probabilístico Food V1 (contrato `SpecializedModel`).

Tercer modelo especializado del Context Engine. Implementa la matemática
cerrada de `MODELO PROBABILÍSTICO FOOD V1.md` (PARTE II, §§18-23):

* Demanda por fase: `P_expected(t) = max_people × Intensity(t)` (llegadas
  esperadas durante la fase, NO ocupación simultánea).
* Capacidad de servicio por zona con permanencias INDIVIDUALES:
  `service_capacity_phase = Σ [capacity_i × Δt / D_i]`.
  Esta cantidad NO se calcula con D_eff (decisión de diseño §20/R3).
* Entradas efectivas: `entries_t = min(P_expected(t), service_capacity_phase)`.
* Permanencia efectiva: promedio armónico ponderado por capacidad
  `D_eff = Σ capacity_i / Σ (capacity_i / D_i)` (§21). Preserva la capacidad
  de servicio agregada pero NO reproduce las permanencias individuales por
  subtipo (hipótesis V1 #1, aproximación MVP defendible).
* Modelo temporal exponencial (§19):
  `O_t = O_(t-1) × exp(-Δt/D_eff) + (entries_t/Δt) × D_eff × (1 - exp(-Δt/D_eff))`
  Es un modelo de STOCK acumulado entre fases (a diferencia de Baños V1,
  que es flujo instantáneo por Little's law).
* Distribución espacial iterativa de Parking/Baños V1 (§22): pesos
  `w_i = 1 / (1 + α × distance_i)`, expansión con tope `capacity_i`,
  contracción desde la zona menos preferida. Conservación exacta
  `Σ occupied_i(t) = O_t`.

UNIDADES: el modelo trabaja internamente en HORAS (Δt, D_i, D_eff).
`ServiceConfig.average_duration_min` llega en MINUTOS; la conversión
min→h se ejecuta UNA vez en la frontera de composición vía
`duration_hours()` antes de invocar `simulate()`. El núcleo matemático
nunca mezcla unidades.

HIPÓTESIS V1 EXPLÍCITAS (§15, aproximaciones MVP):
1. `D_eff` es una duración efectiva equivalente, no una permanencia real.
2. `unabsorbed_t` es un residual instantáneo por fase: NO se arrastra como
   backlog ni persiste con `r_t`; nunca incrementa stock ni occupied.
3. La capacidad gastronómica es estable durante la simulación.
4. La distancia es proxy de distribución espacial (sin preferencias por
   subtipo, precio ni tipo de comida).
5. Se ignoran preferencias por subtipo: todas las zonas compiten por la
   misma demanda agregada.
6. Se ignoran throughput operativos no expresados vía capacity/duration.
7. No se modelan colas físicas, abandono ni comportamiento individual.
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

# α controla el decaimiento del peso espacial w_i = 1/(1 + α × distance_i).
# Mismo valor calibrable que Parking V1 y Baños V1 (§26).
DEFAULT_ALPHA: Final = 0.001


@dataclass(frozen=True)
class FoodTemporalPhase:
    """Capa temporal de una fase (§19): demanda, servicio y stock."""

    p_expected: float
    entries: float
    unabsorbed: float
    retention: float
    remain: float
    contribution: float
    stock: float


@dataclass(frozen=True)
class FoodPhaseState:
    """Estado completo de una fase: capa temporal + distribución espacial."""

    index: int
    p_expected: float
    entries: float
    unabsorbed: float
    retention: float
    remain: float
    contribution: float
    stock: float
    d_effective_hours: float
    service_capacity_phase: float
    occupied: Mapping[UUID, float]


class FoodV1Model:
    """Modelo probabilístico Food v1 (contrato `SpecializedModel`).

    `execute(context)` computa el estado de la fase actual de la zona
    entregada por el Context Engine (aproximación por-zona donde D_eff
    degenera a la permanencia de la propia zona). La matemática real es
    sistémica (multi-zona, multi-fase): `simulate` evalúa la evolución
    completa con D_eff agregado y `distribute` reparte el stock entre
    todas las zonas gastronómicas. La entrada canónica de producción es
    `simulate`.
    """

    model_id = "food_v1"

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
        return zone.type == "comida"

    def execute(self, context: ModelExecutionContext) -> ModelSpecificResult:
        zone = context.zone
        if not self.supports(zone):
            raise ValueError(
                f"FoodV1Model no aplica a la zona {zone.id} "
                f"(type={zone.type!r}, subtipo={zone.subtipo!r})"
            )
        intensity = self._resolve_intensity(context)
        delta_hours = self._phase_duration_hours(context.active_event_day_phase)
        max_people = self._require_max_people(context.attendance_level)
        duration_hours = self.duration_hours(context.average_duration_min)
        p_expected = self.p_expected(max_people, intensity)
        capacity = zone.capacity
        # Aproximación por-zona (contrato SpecializedModel): con una única
        # zona D_eff degenera a D_zona y la capacidad de servicio usa esa
        # misma permanencia. La evolución sistémica real es `simulate`.
        d_effective = duration_hours
        service_capacity = self.service_capacity_phase(
            [float(capacity)], [duration_hours], delta_hours
        )
        prev = self.initial_occupied([zone])
        prev_stock = prev.get(zone.id, 0.0)
        temporal = self.temporal_step(
            prev_stock,
            p_expected,
            service_capacity,
            delta_hours,
            d_effective,
        )
        occupied = self.distribute(prev, [zone], temporal.stock)
        zone_occupied = occupied.get(zone.id, temporal.stock)
        occupancy_ratio, free_ratio, free_spaces = self.indices(
            zone_occupied, capacity
        )
        data = {
            "food_id": str(zone.id),
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

    def p_expected(self, max_people: int | None, intensity: float | None) -> float:
        """`P_expected(t) = max_people × Intensity` (§18).

        Representa personas que INTENTAN comer durante la fase (llegadas),
        no ocupación simultánea (§8, tabla de distinción obligatoria).
        """
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
        """Convierte MINUTOS a HORAS: `D = min / 60.0` (frontera de unidades).

        `ServiceConfig.average_duration_min` llega en minutos; la conversión
        ocurre una única vez antes de entrar al núcleo matemático (que opera
        exclusivamente en horas, igual que `_phase_duration_hours`).
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

    def effective_duration(
        self,
        capacities: Sequence[float],
        durations_hours: Sequence[float],
    ) -> float:
        """Permanencia efectiva del sistema (§21):

        `D_eff = Σ capacity_i / Σ (capacity_i / D_i)`

        Promedio armónico ponderado por capacidad (NO aritmético). Propiedad
        clave (V9): preserva exactamente la capacidad de servicio agregada,
        `(Σ capacity_i) × Δt / D_eff = Σ [capacity_i × Δt / D_i]`.
        """
        self._validate_capacity_duration_series(capacities, durations_hours)
        weighted_sum = sum(
            float(capacity) / float(duration)
            for capacity, duration in zip(capacities, durations_hours)
        )
        total_capacity = sum(float(capacity) for capacity in capacities)
        return total_capacity / weighted_sum

    def service_capacity_phase(
        self,
        capacities: Sequence[float],
        durations_hours: Sequence[float],
        delta_hours: float,
    ) -> float:
        """Capacidad de atención durante la fase (§20):

        `service_capacity_phase = Σ [capacity_i × (Δt / D_i)]`

        Usa las permanencias INDIVIDUALES de cada zona (no D_eff): la
        rotación de un foodtruck (20 min) no es la de un restaurante
        (60 min). Es la cantidad que acota `entries_t` (V2).
        """
        self._validate_capacity_duration_series(capacities, durations_hours)
        if isinstance(delta_hours, bool) or not isinstance(delta_hours, (int, float)):
            raise TypeError("delta_hours must be a number")
        if delta_hours <= 0:
            raise ValueError("delta_hours must be > 0")
        return sum(
            float(capacity) * (float(delta_hours) / float(duration))
            for capacity, duration in zip(capacities, durations_hours)
        )

    def retention(self, delta_hours: float, duration: float) -> float:
        """Proporción del stock que continúa: `r_t = exp(-Δt / D_eff)` (§19).

        A diferencia de Parking V1 (r ≈ 0.78) y Baños V1 (r ≈ 0), en Food V1
        `r_t` varía según la relación Δt/D_eff (tabla §16: 0.01-0.37 típico).
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
        p_expected: float,
        service_capacity: float,
        delta_hours: float,
        duration: float,
    ) -> FoodTemporalPhase:
        """Capa temporal de una fase — ecuación exponencial (§19).

        * `entries = min(P_expected, service_capacity_phase)` — entradas
          efectivas acotadas por la capacidad de servicio (V2).
        * `unabsorbed = max(0, P_expected - entries)` — residual instantáneo
          por fase; NO se arrastra como backlog ni incrementa stock (V6/V7).
        * `r = exp(-Δt / D_eff)`, `remain = O_(t-1) × r` — decaimiento
          exponencial del stock previo.
        * `contribution = (entries / Δt) × D_eff × (1 - r)` — solución de la
          EDO dO/dt = λ - O/D con λ = entries/Δt constante en la fase.
        * `stock = remain + contribution` — conservación temporal (V8).

        Casos límite (§12): D_eff ≪ Δt reproduce Little's Law
        (`O ≈ entries × D/Δt`); D_eff = Δt da `O ≈ entries × 0.632`;
        D_eff ≫ Δt acumula fuerte.
        """
        self._require_nonnegative(prev_stock, "prev_stock")
        self._require_nonnegative(p_expected, "p_expected")
        if isinstance(service_capacity, bool) or not isinstance(
            service_capacity, (int, float)
        ):
            raise TypeError("service_capacity must be a number")
        if service_capacity <= 0:
            raise ValueError("service_capacity must be > 0")
        if isinstance(delta_hours, bool) or not isinstance(
            delta_hours, (int, float)
        ):
            raise TypeError("delta_hours must be a number")
        if delta_hours <= 0:
            raise ValueError("delta_hours must be > 0")

        entries = min(float(p_expected), float(service_capacity))
        unabsorbed = max(0.0, float(p_expected) - entries)

        r = self.retention(delta_hours, duration)
        remain = float(prev_stock) * r
        contribution = (entries / float(delta_hours)) * float(duration) * (1.0 - r)
        stock = remain + contribution
        return FoodTemporalPhase(
            p_expected=float(p_expected),
            entries=entries,
            unabsorbed=unabsorbed,
            retention=r,
            remain=remain,
            contribution=contribution,
            stock=stock,
        )

    def distribute(
        self,
        prev_occupied: Mapping[UUID, float],
        zones: Sequence[Zone],
        stock: float,
        alpha: float | None = None,
    ) -> Mapping[UUID, float]:
        """Distribución espacial del stock (§22, algoritmo de Parking V1).

        Solo mueve el incremento neto `Δ = O_t - Σ occupied_i(t-1)`:
        expansión proporcional a `w_i` con tope `free_i` y redistribución
        iterativa; contracción retirando desde la zona de menor `w_i`.
        Conserva `Σ occupied_i(t) = O_t` (V5) y respeta los topes
        `occupied_i ≤ capacity_i` (V4).
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
        """Estado inicial de la jornada: O₀ = 0 (§19 condición inicial).

        La jornada comienza sin comensales en el sistema.
        """
        return {zone.id: 0.0 for zone in zones}

    def simulate(
        self,
        phases: Sequence[EventDayPhase],
        zones: Sequence[Zone],
        max_people: int,
        durations_hours: Mapping[UUID, float],
    ) -> list[FoodPhaseState]:
        """Evolución temporal + espacial completa por fases (§9, §19).

        `O_0 = 0`: la jornada comienza sin comensales. Las fases se evalúan
        en orden cronológico `(start_min, id)`. Cada fase calcula su
        capacidad de servicio con las D_i individuales, acota las entradas
        y evoluciona el stock con D_eff. Devuelve un estado por fase,
        reutilizable para los tests de las validaciones V1-V12.
        """
        if not phases:
            raise ValueError("phases must not be empty")
        if not zones:
            raise ValueError("zones must not be empty")
        if max_people is None:
            raise ValueError("max_people is required")
        if isinstance(max_people, bool) or not isinstance(max_people, int):
            raise TypeError("max_people must be an integer")
        if max_people < 0:
            raise ValueError("max_people must be >= 0")
        capacities = [float(zone.capacity) for zone in zones]
        durations = [
            self._resolve_zone_duration(durations_hours, zone) for zone in zones
        ]
        d_effective = self.effective_duration(capacities, durations)

        ordered = sorted(phases, key=lambda p: (p.start_min, str(p.id)))
        prev_occupied = self.initial_occupied(zones)
        prev_stock = float(sum(prev_occupied.values()))
        results: list[FoodPhaseState] = []
        for index, phase in enumerate(ordered, start=1):
            intensity = phase.intensity
            delta_hours = self._phase_duration_hours(phase)
            expected = self.p_expected(max_people, intensity)
            service_capacity = self.service_capacity_phase(
                capacities, durations, delta_hours
            )
            temporal = self.temporal_step(
                prev_stock,
                expected,
                service_capacity,
                delta_hours,
                d_effective,
            )
            occupied = self.distribute(prev_occupied, zones, temporal.stock)
            results.append(
                FoodPhaseState(
                    index=index,
                    p_expected=temporal.p_expected,
                    entries=temporal.entries,
                    unabsorbed=temporal.unabsorbed,
                    retention=temporal.retention,
                    remain=temporal.remain,
                    contribution=temporal.contribution,
                    stock=temporal.stock,
                    d_effective_hours=d_effective,
                    service_capacity_phase=service_capacity,
                    occupied=dict(occupied),
                )
            )
            prev_stock = temporal.stock
            prev_occupied = occupied
        return results

    def indices(
        self, occupied: float, capacity: int
    ) -> tuple[float, float, float]:
        """Índices determinísticos de saturación (§23, espejo Parking §35.5).

        `occupancy_ratio` NO es una probabilidad: es la proporción
        determinística de capacidad ocupada.
        """
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
    def _resolve_zone_duration(
        durations_hours: Mapping[UUID, float], zone: Zone
    ) -> float:
        duration = durations_hours.get(zone.id)
        if duration is None:
            raise ValueError(
                "durations_hours must define a positive duration "
                f"for zone {zone.id} (subtipo={zone.subtipo!r})"
            )
        if isinstance(duration, bool) or not isinstance(duration, (int, float)):
            raise TypeError(f"duration for zone {zone.id} must be a number")
        if duration <= 0:
            raise ValueError(
                f"duration for zone {zone.id} must be > 0 (got {duration})"
            )
        return float(duration)

    @staticmethod
    def _validate_capacity_duration_series(
        capacities: Sequence[float],
        durations_hours: Sequence[float],
    ) -> None:
        if not capacities or not durations_hours:
            raise ValueError("capacities and durations must not be empty")
        if len(capacities) != len(durations_hours):
            raise ValueError(
                "capacities and durations must have the same length"
            )
        for i, (capacity, duration) in enumerate(zip(capacities, durations_hours)):
            if isinstance(capacity, bool) or not isinstance(capacity, (int, float)):
                raise TypeError(f"capacities[{i}] must be a number")
            if capacity <= 0:
                raise ValueError(f"capacities[{i}] must be > 0")
            if isinstance(duration, bool) or not isinstance(duration, (int, float)):
                raise TypeError(f"durations_hours[{i}] must be a number")
            if duration <= 0:
                raise ValueError(f"durations_hours[{i}] must be > 0")

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
