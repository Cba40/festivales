"""Aislamiento por zona cuando un modelo especializado no puede calcular.

Por qué existe este archivo
---------------------------
Conectar `ParkingV1Model` y `BathroomV1Model` al Context Engine (que es lo que
hace `_build_model_selector`) hizo suddenly real un riesgo que estaba latente:
los dos modelos exigen insumo que en la base es NULLABLE.

- `ParkingV1Model.v_expected` tira `ValueError` si `estimated_vehicles is None`
  (`parking_v1_model.py:120`), y sale de `event_days.estimated_vehicles`.
- `BathroomV1Model._require_max_people` tira `ValueError` si `attendance_level`
  es `None` o su `max_people` es `None` (`bathroom_v1_model.py:453-461`).

`execute_specialized_models` no tenía try/except, así que **una sola zona sin
`estimated_vehicles` tumbaba el endpoint público `/predictions` completo con un
500**, perdiendo las 38 zonas sanas junto con la que falló.

Estos tests fijan el comportamiento de degradación: la zona que no se puede
modelar se degrada sola, las demás no se enteran, y el error queda logueado.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from uuid import UUID

import pytest

from src.application.context_engine.dto import (
    EventEvaluationResult,
    ZoneApplication,
    ZoneBehaviorApplicationResult,
)
from src.application.context_engine.model_selector import ModelSelector
from src.application.context_engine.stage4_model_execution import (
    execute_specialized_models,
)
from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.event_day import EventDay
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.zone import Zone
from src.domain.entities.zone_behavior import FlowRestriction
from src.domain.models.specialized_model import ModelSpecificResult

DAY_ID = UUID("11111111-1111-1111-1111-111111111111")
PHASE_ID = UUID("22222222-2222-2222-2222-222222222222")
ED_PHASE_ID = UUID("33333333-3333-3333-3333-333333333333")
ATT_ID = UUID("44444444-4444-4444-4444-444444444444")
PROFILE_ID = UUID("55555555-5555-5555-5555-555555555555")

ZONE_OK = UUID("66666666-6666-6666-6666-666666666601")
ZONE_ROTA = UUID("66666666-6666-6666-6666-666666666602")

TIMESTAMP = datetime(2026, 10, 3, 21, 0, tzinfo=timezone.utc)


def _zona(zid: UUID, tipo: str = "estacionamiento") -> Zone:
    return Zone(
        id=zid,
        name=f"zona-{zid}",
        zone_type_id=UUID("77777777-7777-7777-7777-777777777777"),
        capacity=100,
        type=tipo,
    )


def _evaluation() -> EventEvaluationResult:
    op = OperationalPhase(id=PHASE_ID, name="Clausura", sequence_order=2)
    edp = EventDayPhase(
        id=ED_PHASE_ID,
        event_day_id=DAY_ID,
        operational_phase_id=PHASE_ID,
        start_min=1080,
        end_min=1440,
        intensity=0.8,
    )
    return EventEvaluationResult(
        active_operational_phase=op,
        active_event_day_phase=edp,
        timestamp=TIMESTAMP,
        event_impacts={},
    )


def _zone_result(zones: list[Zone]) -> ZoneBehaviorApplicationResult:
    evaluation = _evaluation()
    return ZoneBehaviorApplicationResult(
        active_operational_phase=evaluation.active_operational_phase,
        active_event_day_phase=evaluation.active_event_day_phase,
        timestamp=TIMESTAMP,
        zone_applications={
            z.id: ZoneApplication(
                zone_id=z.id,
                projected_density=50,
                active_restriction=FlowRestriction.OPEN,
                density_factor=0.5,
            )
            for z in zones
        },
    )


def _event_day(*, estimated_vehicles: int | None) -> EventDay:
    return EventDay(
        event_date=date(2026, 10, 3),
        operational_profile_id=PROFILE_ID,
        operational_start_min=0,
        operational_end_min=1440,
        # `EventDay` exige al menos una fase (entity validation). La fase no se
        # usa en esta etapa: el `active_event_day_phase` Relevant viene en el
        # `EventEvaluationResult`.
        phases=(
            EventDayPhase(
                id=ED_PHASE_ID,
                event_day_id=DAY_ID,
                operational_phase_id=PHASE_ID,
                start_min=1080,
                end_min=1440,
                intensity=0.8,
            ),
        ),
        attendance_level_id=ATT_ID,
        id=DAY_ID,
        estimated_vehicles=estimated_vehicles,
        average_parking_duration=2.0,
    )


def _attendance_level() -> AttendanceLevel:
    return AttendanceLevel(
        name="Normal", min_people=100, max_people=1000, id=str(ATT_ID)
    )


class _ModeloQueFalla:
    """Stand-in de un modelo que no puede calcular. Reproduce el caso real."""

    model_id = "falla_v1"

    def supports(self, zone: Zone) -> bool:
        return True

    def execute(self, context) -> ModelSpecificResult:
        raise ValueError("estimated_vehicles is required")


class _ModeloQueAnda:
    model_id = "anda_v1"

    def __init__(self, result: ModelSpecificResult) -> None:
        self._result = result

    def supports(self, zone: Zone) -> bool:
        return True

    def execute(self, context) -> ModelSpecificResult:
        return self._result


class _SelectorPorZona:
    """Selecciona un modelo distinto por zona, para probar el aislamiento."""

    def __init__(self, por_zona: dict[UUID, object]) -> None:
        self._por_zona = por_zona

    def select(self, zone: Zone):
        return self._por_zona.get(zone.id)


class TestDegradacionPorZona:
    def test_una_zona_que_falla_no_tumba_a_las_demas(self):
        """El motivo de existir del try/except: 38 zonas sanas no pueden caer
        por una que no se puede modelar."""
        sana, rota = _zona(ZONE_OK), _zona(ZONE_ROTA)
        ok_result = ModelSpecificResult(
            model_id="anda_v1", zone_id=ZONE_OK, data={"occupancy_ratio": 0.3}
        )
        zones = [sana, rota]

        results = execute_specialized_models(
            _zone_result(zones),
            zones,
            _evaluation(),
            attendance_level=_attendance_level(),
            event_day=_event_day(estimated_vehicles=500),
            model_selector=_SelectorPorZona(
                {ZONE_OK: _ModeloQueAnda(ok_result), ZONE_ROTA: _ModeloQueFalla()}
            ),
        )

        assert set(results) == {ZONE_OK}
        assert results[ZONE_OK].data == {"occupancy_ratio": 0.3}

    def test_el_error_se_loguea_como_warning(self, caplog):
        """Degradar no es tragar en silencio: un modelo que falla en todas las
        zonas tiene que verse en los logs, no pasar desapercibido."""
        zona = _zona(ZONE_ROTA)

        with caplog.at_level(logging.WARNING, logger="src.application.context_engine.stage4_model_execution"):
            execute_specialized_models(
                _zone_result([zona]),
                [zona],
                _evaluation(),
                attendance_level=None,
                event_day=_event_day(estimated_vehicles=None),
                model_selector=_SelectorPorZona({ZONE_ROTA: _ModeloQueFalla()}),
            )

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warnings, "se esperaba al menos un warning por la degradacion"
        assert "falla_v1" in warnings[0].getMessage()
        assert str(ZONE_ROTA) in warnings[0].getMessage()

    def test_sin_modelo_registrado_no_devuelve_nada(self):
        """Zona sin modelo -> sin resultado. Es el caso de las zonas genericas
        y no debe logear warning: no es un fallo, es que no hay modelo."""
        zona = _zona(ZONE_OK, tipo="comida")

        results = execute_specialized_models(
            _zone_result([zona]),
            [zona],
            _evaluation(),
            attendance_level=None,
            event_day=_event_day(estimated_vehicles=None),
            model_selector=ModelSelector(),
        )

        assert results == {}


class TestAislamientoConModelosReales:
    """Los modelos de producción, sin mocks: el `ValueError` real."""

    def test_parking_sin_estimated_vehicles_no_propaga(self):
        from src.domain.models.parking_v1_model import ParkingV1Model

        zona = _zona(ZONE_ROTA, tipo="estacionamiento")

        results = execute_specialized_models(
            _zone_result([zona]),
            [zona],
            _evaluation(),
            attendance_level=None,
            event_day=_event_day(estimated_vehicles=None),  # <- NULL en la base
            model_selector=ModelSelector([ParkingV1Model()]),
        )

        # No hay resultado para esa zona, pero no hubo excepcion.
        assert results == {}

    def test_parking_con_estimated_vehicles_si_produce_resultado(self):
        from src.domain.models.parking_v1_model import ParkingV1Model

        zona = _zona(ZONE_OK, tipo="estacionamiento")

        results = execute_specialized_models(
            _zone_result([zona]),
            [zona],
            _evaluation(),
            attendance_level=None,
            event_day=_event_day(estimated_vehicles=800),
            model_selector=ModelSelector([ParkingV1Model()]),
        )

        assert set(results) == {ZONE_OK}
        assert results[ZONE_OK].model_id == "parking_v1"
        assert "occupancy_ratio" in results[ZONE_OK].data

    def test_banos_sin_attendance_level_no_propaga(self):
        from src.domain.models.bathroom_v1_model import BathroomV1Model

        zona = Zone(
            id=ZONE_ROTA,
            name="bano",
            zone_type_id=UUID("77777777-7777-7777-7777-777777777777"),
            capacity=50,
            type="servicios",
            subtipo="banos",
        )

        results = execute_specialized_models(
            _zone_result([zona]),
            [zona],
            _evaluation(),
            attendance_level=None,  # <- NULL en la base
            event_day=_event_day(estimated_vehicles=800),
            model_selector=ModelSelector([BathroomV1Model()]),
        )

        assert results == {}


class TestLaIntensidadLlegaAlModelo:
    """El punto del PASO 1: `EventDayPhase.intensity` tiene queucketar un
    cálculo real. Antes no llegaba a ningún lado."""

    def _parking_con_intensity(self, intensity: float) -> dict:
        from src.domain.models.parking_v1_model import ParkingV1Model

        op = OperationalPhase(id=PHASE_ID, name="Fase", sequence_order=2)
        edp = EventDayPhase(
            id=ED_PHASE_ID,
            event_day_id=DAY_ID,
            operational_phase_id=PHASE_ID,
            start_min=1080,
            end_min=1440,
            intensity=intensity,
        )
        evaluation = EventEvaluationResult(
            active_operational_phase=op,
            active_event_day_phase=edp,
            timestamp=TIMESTAMP,
            event_impacts={},
        )
        zona = _zona(ZONE_OK, tipo="estacionamiento")
        return execute_specialized_models(
            ZoneBehaviorApplicationResult(
                active_operational_phase=op,
                active_event_day_phase=edp,
                timestamp=TIMESTAMP,
                zone_applications={
                    zona.id: ZoneApplication(
                        zone_id=zona.id,
                        projected_density=50,
                        active_restriction=FlowRestriction.OPEN,
                        density_factor=0.5,
                    )
                },
            ),
            [zona],
            evaluation,
            attendance_level=None,
            # 200 vehiculos contra capacity=100: con intensity 1.0 el modelo
            # proyecta 200 x 2h = 400 y con 0.1 proyecta 40. Ambos por DEBAJO de
            # la capacidad. Con un estimated_vehicles enorme los dos casos
            # saturan contra `capacity` y la prueba daria ocupado == capacidad en
            # los dos, sin distinguir nada.
            event_day=_event_day(estimated_vehicles=200),
            model_selector=ModelSelector([ParkingV1Model()]),
        )[zona.id].data

    def test_mas_intensidad_mas_ocupacion_proyectada(self):
        baja = self._parking_con_intensity(0.1)
        alta = self._parking_con_intensity(1.0)

        assert alta["occupied"] > baja["occupied"], (
            "con intensity 1.0 deberia proyectar mas ocupacion que con 0.1; "
            "si esto falla, la intensidad sigue sin llegar al modelo"
        )
        assert alta["occupancy_ratio"] > baja["occupancy_ratio"]

    @pytest.mark.parametrize("intensity", [0.1, 0.5, 1.0])
    def test_es_monotono_en_intensity(self, intensity: float):
        """Cada phase intensity debe mover el resultado en un solo sentido."""
        resultados = [
            self._parking_con_intensity(i)["occupancy_ratio"]
            for i in (0.1, 0.5, 1.0)
        ]
        assert resultados == sorted(resultados), (
            f"occupancy_ratio no es monotono en intensity: {resultados} "
            f"(intensity={intensity})"
        )