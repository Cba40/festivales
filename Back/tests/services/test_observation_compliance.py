"""Tests del evaluador de cumplimiento de Protocolos de Control de Observaciones.

Dos capas:

1. ``TestEvaluateTrigger`` y los formateadores: funciones puras, sin base.
2. ``TestObservationComplianceEvaluator``: el recorrido completo contra una
   sesion async con ``AsyncMock`` que devuelve las filas que cada consulta pide.

Se cubre a proposito el caso en que la metrica del trigger **no** viene en la
prediccion: una regla no puede afirmar que se supero un umbral sobre un dato que
no existe, y ese es el camino que mas se prestaria a generar ruido.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.observation_control_protocol import (
    ObservationTriggerMetric,
    ObservationTriggerOperator,
)
from app.services.observation_compliance import (
    ObservationComplianceEvaluator,
    _build_detail,
    _trim,
    _zone_states_from_prediction,
    evaluate_trigger,
)

GT = ObservationTriggerOperator.GT
GTE = ObservationTriggerOperator.GTE
LT = ObservationTriggerOperator.LT
LTE = ObservationTriggerOperator.LTE


# ── evaluate_trigger ─────────────────────────────────────────────────────────


class TestEvaluateTrigger:
    @pytest.mark.parametrize(
        "value,operator,threshold,expected",
        [
            (90, GT, Decimal("80"), True),
            (80, GT, Decimal("80"), False),
            (80.01, GT, Decimal("80"), True),
            (80, GTE, Decimal("80"), True),
            (79, GTE, Decimal("80"), False),
            (10, LT, Decimal("20"), True),
            (20, LT, Decimal("20"), False),
            (20, LTE, Decimal("20"), True),
            (21, LTE, Decimal("20"), False),
        ],
    )
    def test_comparadores(self, value, operator, threshold, expected):
        assert evaluate_trigger(value, operator, threshold) is expected

    def test_valor_none_nunca_dispara(self):
        """Sin dato no hay incumplimiento que afirmar."""
        for operator in (GT, GTE, LT, LTE):
            assert evaluate_trigger(None, operator, Decimal("80")) is False

    def test_valor_no_numerico_no_dispara(self):
        assert evaluate_trigger("mucha", GT, Decimal("80")) is False

    def test_umbral_decimal_se_compara_bien(self):
        assert evaluate_trigger(0.85, GT, Decimal("0.80")) is True
        assert evaluate_trigger(0.75, GT, Decimal("0.80")) is False

    def test_acepta_float_del_json(self):
        assert evaluate_trigger(0.81, GT, Decimal("0.80")) is True


# ── Lectura de zone_states_data ─────────────────────────────────────────────


class TestZoneStatesParsing:
    def _prediction(self, raw):
        return SimpleNamespace(zone_states_data=raw)

    def test_acepta_lista_de_dicts(self):
        states = _zone_states_from_prediction(
            self._prediction([{"zone_id": "z1", "saturation_level": 0.9}])
        )
        assert states == [{"zone_id": "z1", "saturation_level": 0.9}]

    def test_acepta_json_string(self):
        states = _zone_states_from_prediction(
            self._prediction('[{"zone_id": "z1", "saturation_level": 0.9}]')
        )
        assert len(states) == 1

    def test_acepta_objeto_contenedor(self):
        states = _zone_states_from_prediction(
            self._prediction({"zone_states": [{"zone_id": "z1"}]})
        )
        assert states == [{"zone_id": "z1"}]

    def test_devuelve_vacio_si_es_none(self):
        assert _zone_states_from_prediction(self._prediction(None)) == []

    def test_devuelve_vacio_si_el_json_esta_roto(self):
        assert _zone_states_from_prediction(self._prediction("{no json")) == []

    def test_devuelve_vacio_si_no_es_lista_ni_objeto(self):
        assert _zone_states_from_prediction(self._prediction("texto")) == []

    def test_filtra_entradas_que_no_son_dict(self):
        states = _zone_states_from_prediction(
            self._prediction([{"zone_id": "z1"}, "basura", None])
        )
        assert states == [{"zone_id": "z1"}]


# ── Formateadores ───────────────────────────────────────────────────────────


class TestDetailFormatting:
    def test_trim_quita_ceros_innecesarios(self):
        assert _trim(Decimal("80.00")) == "80"
        assert _trim(Decimal("0.80")) == "0.8"

    def test_frase_con_umbral_superado(self):
        detalle = _build_detail(
            ObservationTriggerMetric.SATURATION_LEVEL,
            GT,
            Decimal("0.80"),
            Decimal("0.92"),
            5,
            None,
        )
        assert "saturación" in detalle
        assert "supera" in detalle
        assert "0.8" in detalle
        assert "no hay ninguna observación" in detalle

    def test_frase_con_observacion_reciente(self):
        detalle = _build_detail(
            ObservationTriggerMetric.ESTIMATED_WAIT,
            GT,
            Decimal("15"),
            Decimal("22"),
            10,
            12,
        )
        assert "hace 12 min" in detalle

    def test_frase_sin_dato_de_metrica(self):
        detalle = _build_detail(
            ObservationTriggerMetric.CONFIDENCE,
            LT,
            Decimal("0.5"),
            None,
            15,
            None,
        )
        assert "sin dato" in detalle


# ── Evaluador completo ──────────────────────────────────────────────────────


def _protocolo(
    *,
    metric=ObservationTriggerMetric.SATURATION_LEVEL,
    operator=GT,
    threshold="0.80",
    interval=5,
    zone_type_id=None,
    event_day_id=None,
    name="Saturación alta",
):
    return SimpleNamespace(
        id="proto-1",
        event_id="ev-1",
        event_day_id=event_day_id,
        name=name,
        description=None,
        trigger_metric=metric,
        trigger_operator=operator,
        threshold_value=Decimal(threshold),
        action_interval_minutes=interval,
        zone_type_id=zone_type_id,
        active=True,
        order=0,
    )


class _Result:
    """Stub de Result que soporta los cuatro accesores que usa el evaluador."""

    def __init__(self, rows):
        self._rows = list(rows)

    def scalars(self):
        return self

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None

    def scalar_one(self):
        return self._rows[0]

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None


class _FakeAsyncSession:
    """Session async que devuelve filas distintas segun la tabla consultada.

    Despacha mirando el FROM de la sentencia, y para la consulta de
    observaciones saca la zona de los parametros compilados en vez de parsear el
    SQL (que viene con marcadores `__[POSTCOMPILE_...]__`).
    """

    def __init__(
        self,
        *,
        protocols=(),
        prediction=None,
        observations=None,
        zones=(),
        event_day_id="day-1",
    ):
        self._protocols = list(protocols)
        self._prediction = prediction
        self._observations = dict(observations or {})
        self._zones = dict(zones)
        self._event_day_id = event_day_id
        self.queries: list[str] = []

    async def execute(self, stmt):
        sql = str(stmt)
        self.queries.append(sql)

        if "observation_control_protocols" in sql:
            return _Result(self._protocols)
        if "FROM predictions" in sql:
            return _Result([self._prediction] if self._prediction else [])
        if "operational_observations" in sql:
            zona = self._zone_of(stmt)
            ultima = self._observations.get(zona)
            return _Result([ultima] if ultima else [])
        if "FROM event_days" in sql:
            return _Result([self._event_day_id])
        if "FROM zones" in sql:
            return _Result(list(self._zones.items()))
        return _Result([])

    @staticmethod
    def _zone_of(stmt) -> str:
        """El id de zona viaja como bind param `zone_id_1`, junto a `event_day_id_1`.

        Se busca por nombre de clave: la consulta trae las dos y el primero que
        aparezca no es necesariamente la zona.
        """
        params = stmt.compile().params
        for key, value in params.items():
            if "zone_id" in key and isinstance(value, str):
                return value
        return ""


NOW = datetime(2026, 7, 15, 15, 0, tzinfo=timezone.utc)


def _zone_states(**metrics):
    base = {"zone_id": "z1", "type": "escenario"}
    base.update(metrics)
    return [base]


class TestObservationComplianceEvaluator:
    async def test_sin_protocolos_no_hay_alertas(self):
        session = _FakeAsyncSession(protocols=[])
        evaluador = ObservationComplianceEvaluator(session)

        assert await evaluador.evaluate("ev-1") == []

    async def test_umbral_superado_sin_observacion_genera_alerta(self):
        session = _FakeAsyncSession(
            protocols=[_protocolo()],
            prediction=SimpleNamespace(zone_states_data=_zone_states(saturation_level=0.92)),
        )

        alertas = await ObservationComplianceEvaluator(session).evaluate("ev-1")

        assert len(alertas) == 1
        alerta = alertas[0]
        assert alerta.protocol_name == "Saturación alta"
        assert alerta.zone_id == "z1"
        assert alerta.current_value == Decimal("0.92")
        assert alerta.minutes_since_last_observation is None
        assert alerta.severity == "critical"

    async def test_umbral_no_superado_no_genera_alerta(self):
        session = _FakeAsyncSession(
            protocols=[_protocolo()],
            prediction=SimpleNamespace(zone_states_data=_zone_states(saturation_level=0.40)),
        )

        assert await ObservationComplianceEvaluator(session).evaluate("ev-1", now=NOW) == []

    async def test_observacion_reciente_cumple_el_protocolo(self):
        session = _FakeAsyncSession(
            protocols=[_protocolo(interval=5)],
            prediction=SimpleNamespace(zone_states_data=_zone_states(saturation_level=0.92)),
            observations={"z1": NOW - timedelta(minutes=2)},
        )

        assert await ObservationComplianceEvaluator(session).evaluate("ev-1", now=NOW) == []

    async def test_observacion_vieja_no_cumple(self):
        session = _FakeAsyncSession(
            protocols=[_protocolo(interval=5)],
            prediction=SimpleNamespace(zone_states_data=_zone_states(saturation_level=0.92)),
            observations={"z1": NOW - timedelta(minutes=9)},
        )

        alertas = await ObservationComplianceEvaluator(session).evaluate("ev-1", now=NOW)

        assert len(alertas) == 1
        assert alertas[0].minutes_since_last_observation == 9
        assert alertas[0].overdue_minutes == 9

    async def test_observacion_doble_del_intervalo_es_critica(self):
        session = _FakeAsyncSession(
            protocols=[_protocolo(interval=5)],
            prediction=SimpleNamespace(zone_states_data=_zone_states(saturation_level=0.92)),
            observations={"z1": NOW - timedelta(minutes=11)},
        )

        alertas = await ObservationComplianceEvaluator(session).evaluate("ev-1", now=NOW)

        assert alertas[0].severity == "critical"

    async def test_observacion_levemente_vencida_es_warning(self):
        session = _FakeAsyncSession(
            protocols=[_protocolo(interval=10)],
            prediction=SimpleNamespace(zone_states_data=_zone_states(saturation_level=0.92)),
            observations={"z1": NOW - timedelta(minutes=12)},
        )

        alertas = await ObservationComplianceEvaluator(session).evaluate("ev-1", now=NOW)

        assert alertas[0].severity == "warning"

    async def test_metrica_ausente_no_dispara(self):
        """Sin la metrica en la prediccion no se puede afirmar nada."""
        session = _FakeAsyncSession(
            protocols=[_protocolo()],
            prediction=SimpleNamespace(zone_states_data=_zone_states()),
        )

        assert await ObservationComplianceEvaluator(session).evaluate("ev-1", now=NOW) == []

    async def test_sin_prediccion_no_hay_alertas(self):
        session = _FakeAsyncSession(protocols=[_protocolo()], prediction=None)

        assert await ObservationComplianceEvaluator(session).evaluate("ev-1", now=NOW) == []

    async def test_filtra_por_tipo_de_zona(self):
        """Con zone_type_id, solo evalua las zonas de ese tipo."""
        estados = [
            {"zone_id": "z_esc", "type": "escenario", "saturation_level": 0.95},
            {"zone_id": "z_bano", "type": "bano", "saturation_level": 0.95},
        ]
        session = _FakeAsyncSession(
            protocols=[_protocolo(zone_type_id="escenario")],
            prediction=SimpleNamespace(zone_states_data=estados),
            zones={"z_esc": "escenario", "z_bano": "bano"},
        )

        alertas = await ObservationComplianceEvaluator(session).evaluate("ev-1")

        assert [a.zone_id for a in alertas] == ["z_esc"]

    async def test_incluye_el_nombre_de_la_zona(self):
        session = _FakeAsyncSession(
            protocols=[_protocolo()],
            prediction=SimpleNamespace(zone_states_data=_zone_states(saturation_level=0.92)),
            zones={"z1": "Escenario Norte"},
        )

        alertas = await ObservationComplianceEvaluator(session).evaluate("ev-1")

        assert alertas[0].zone_name == "Escenario Norte"

    async def test_usa_la_jornada_del_protocolo_si_la_tiene(self):
        session = _FakeAsyncSession(
            protocols=[_protocolo(event_day_id="day-especifico")],
            prediction=SimpleNamespace(zone_states_data=_zone_states(saturation_level=0.92)),
            event_day_id="day-activo",
        )

        alertas = await ObservationComplianceEvaluator(session).evaluate("ev-1")

        assert len(alertas) == 1
        assert alertas[0].event_day_id == "day-especifico"

    async def test_usa_la_jornada_activa_si_el_protocolo_no_tiene(self):
        session = _FakeAsyncSession(
            protocols=[_protocolo(event_day_id=None)],
            prediction=SimpleNamespace(zone_states_data=_zone_states(saturation_level=0.92)),
            event_day_id="day-activo",
        )

        alertas = await ObservationComplianceEvaluator(session).evaluate("ev-1")

        assert alertas[0].event_day_id == "day-activo"

    async def test_varios_protocolos_por_zona(self):
        """Dos reglas incumplidas sobre la misma zona generan dos alertas."""
        session = _FakeAsyncSession(
            protocols=[
                _protocolo(name="Saturación alta"),
                _protocolo(
                    name="Espera larga",
                    metric=ObservationTriggerMetric.ESTIMATED_WAIT,
                    threshold="15",
                    interval=10,
                ),
            ],
            prediction=SimpleNamespace(
                zone_states_data=_zone_states(saturation_level=0.92, estimated_wait=25)
            ),
        )

        alertas = await ObservationComplianceEvaluator(session).evaluate("ev-1")

        assert {a.protocol_name for a in alertas} == {"Saturación alta", "Espera larga"}

    async def test_operador_lt_se_respeta(self):
        session = _FakeAsyncSession(
            protocols=[
                _protocolo(
                    metric=ObservationTriggerMetric.AVAILABILITY,
                    operator=LT,
                    threshold="20",
                    interval=5,
                    name="Disponibilidad crítica",
                )
            ],
            prediction=SimpleNamespace(zone_states_data=_zone_states(availability=8)),
        )

        alertas = await ObservationComplianceEvaluator(session).evaluate("ev-1")

        assert len(alertas) == 1
        assert alertas[0].current_value == Decimal("8")

    async def test_evalua_con_now_explicito(self):
        session = _FakeAsyncSession(
            protocols=[_protocolo(interval=5)],
            prediction=SimpleNamespace(zone_states_data=_zone_states(saturation_level=0.92)),
            observations={"z1": NOW - timedelta(minutes=3)},
        )

        alertas = await ObservationComplianceEvaluator(session).evaluate("ev-1", now=NOW)

        assert alertas == []