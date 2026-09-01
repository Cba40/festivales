"""OperationalEventAdapter — Fase 3 RFC-OPERATIONAL-EVENTS-V1.

Cubre el contrato `OperationalEventRepository` del Context Engine: filtro
temporal + is_active, formulas de impacto (reduccion/cierre/aumento/sin
impacto) con capacity (zones) y density_factor (zone_behaviors de la fase
activa), normalizacion a [-100, 100] y manejo seguro de zone_id nulo/
inexistente y zone_type sin catalogar.

Mismo patron que el resto de la suite de composicion: sesion AsyncMock con
despacho por tabla (inmune al N de queries del adapter), sin base de datos.
"""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from src.domain.entities.operational_event import OperationalEvent
from src.infrastructure.composition.adapters.operational_event_adapter import (
    OperationalEventAdapter,
    clamp_impact,
    compute_impact,
    minutes_in_local_day,
    resolve_active_phase_id,
    resolve_zone_type_id,
)

AR = ZoneInfo("America/Argentina/Buenos_Aires")

EVENT_DAY_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
ZONE_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1"
ZONE_B = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2"
ZONE_C = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3"
MISSING_ZONE = "dddddddd-dddd-dddd-dddd-dddddddddddd"
ZT_COMIDA = "cccccccc-0000-0000-0000-000000000001"
ZT_BANO = "cccccccc-0000-0000-0000-000000000002"
ZT_OTRO = "cccccccc-0000-0000-0000-000000000003"
OP_P1 = "99999999-0000-0000-0000-000000000001"
OP_P2 = "99999999-0000-0000-0000-000000000002"
OP_P3 = "99999999-0000-0000-0000-000000000003"

TS = datetime(2026, 7, 15, 13, 0, tzinfo=AR)


def _event_row(
    rid: str,
    zone_id: str | None,
    effect_type: str,
    effect_value: int | None,
    *,
    start_min: int = 720,
    end_min: int = 840,
    is_active: bool = True,
    is_incident: bool = False,
    latitude=None,
    longitude=None,
) -> SimpleNamespace:
    start = datetime(2026, 7, 15, 0, 0, tzinfo=AR).replace(hour=12, minute=0)
    return SimpleNamespace(
        id=rid,
        event_day_id=EVENT_DAY_ID,
        zone_id=zone_id,
        event_type="tormenta",
        description=None,
        effect_type=effect_type,
        effect_value=effect_value,
        is_incident=is_incident,
        start_timestamp=start.replace(hour=start_min // 60, minute=start_min % 60),
        end_timestamp=start.replace(hour=end_min // 60, minute=end_min % 60),
        is_active=is_active,
        latitude=latitude,
        longitude=longitude,
    )


def _zone_row(zid: str, ztype: str, subtipo: str | None, capacity: int) -> SimpleNamespace:
    return SimpleNamespace(id=zid, capacity=capacity, type=ztype, subtipo=subtipo)


def _scalars_result(models):
    result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = list(models)
    result.scalars = MagicMock(return_value=scalars_mock)
    return result


def _all_result(rows):
    result = MagicMock()
    result.all = MagicMock(return_value=list(rows))
    return result


def _make_session(
    event_rows,
    *,
    ts=TS,
    zone_rows=None,
    zone_type_rows=None,
    day_phase_rows=None,
    behavior_rows=None,
):
    """Sesion con despacho por tabla.

    El adapter delega el filtro temporal + `is_active` al SQL; para que el
    test sea fiel a la semantica, el despacho de `operational_events` aplica
    el mismo predicado que emite el adapter. Las filas resultantes se devuelven
    en el orden en que fueron creadas.
    """
    zone_rows = zone_rows or []
    zone_type_rows = zone_type_rows or []
    day_phase_rows = day_phase_rows or []
    behavior_rows = behavior_rows or []
    day_rows = [SimpleNamespace(id=EVENT_DAY_ID, date=datetime(2026, 7, 15).date())]
    captured_stmts: list[str] = []

    def fake_execute(stmt, *args, **kwargs):
        sql = str(stmt)
        captured_stmts.append(sql)
        if "zone_behaviors" in sql:
            return _scalars_result(behavior_rows)
        if "zone_types" in sql:
            return _scalars_result(zone_type_rows)
        if "operational_events" in sql:
            active = [
                row
                for row in event_rows
                if row.is_active
                and row.start_timestamp <= ts
                and row.end_timestamp > ts
            ]
            return _scalars_result(active)
        if "zones" in sql:
            return _all_result(zone_rows)
        if "event_day_phases" in sql:
            return _scalars_result(day_phase_rows)
        if "event_days" in sql:
            return _all_result(day_rows)
        raise AssertionError(f"unexpected statement: {sql}")

    async def async_fake_execute(stmt, *args, **kwargs):
        return fake_execute(stmt, *args, **kwargs)

    session = MagicMock()
    session.execute = async_fake_execute
    session.captured_stmts = captured_stmts
    return session


def _default_zone_rows():
    return [
        _zone_row(ZONE_A, "comida", None, 100),
        _zone_row(ZONE_B, "servicios", "banos", 50),
        _zone_row(ZONE_C, "otro", None, 60),
    ]


def _default_zone_type_rows():
    return [
        SimpleNamespace(slug="comida", id=ZT_COMIDA),
        SimpleNamespace(slug="bano", id=ZT_BANO),
        SimpleNamespace(slug="otro", id=ZT_OTRO),
    ]


def _default_day_phase_rows():
    return [
        SimpleNamespace(
            event_day_id=EVENT_DAY_ID,
            operational_phase_id=OP_P1,
            start_min=600,
            end_min=720,
        ),
        SimpleNamespace(
            event_day_id=EVENT_DAY_ID,
            operational_phase_id=OP_P2,
            start_min=720,
            end_min=840,
        ),
        SimpleNamespace(
            event_day_id=EVENT_DAY_ID,
            operational_phase_id=OP_P3,
            start_min=840,
            end_min=960,
        ),
    ]


def _default_behavior_rows():
    return [
        SimpleNamespace(zone_type_id=ZT_COMIDA, operational_phase_id=OP_P2, density_factor=0.5),
        SimpleNamespace(zone_type_id=ZT_BANO, operational_phase_id=OP_P2, density_factor=0.8),
    ]


class TestImpactFormulas:
    def test_reduccion_capacidad(self) -> None:
        assert compute_impact("reduccion_capacidad", 40, 100, 0.5) == -20

    def test_cierre_total(self) -> None:
        assert compute_impact("cierre_total", None, 50, 0.8) == -40

    def test_aumento_demanda_uses_effect_value(self) -> None:
        assert compute_impact("aumento_demanda", 25, 100, 0.9) == 25

    def test_incidente_sin_impacto_is_zero(self) -> None:
        assert compute_impact("incidente_sin_impacto", None, 100, 0.9) == 0

    def test_unknown_effect_type_is_zero(self) -> None:
        assert compute_impact("otro_tipo", None, 100, 0.9) == 0

    def test_clamp_impact_lower_bound(self) -> None:
        assert clamp_impact(-500) == -100

    def test_clamp_impact_upper_bound(self) -> None:
        assert clamp_impact(250) == 100

    def test_clamp_impact_preserves_in_range(self) -> None:
        assert clamp_impact(-20) == -20
        assert clamp_impact(0) == 0
        assert clamp_impact(25) == 25


class TestResolutionHelpers:
    def test_minutes_in_local_day_same_day(self) -> None:
        ts = datetime(2026, 7, 15, 13, 0, tzinfo=AR)
        assert minutes_in_local_day(datetime(2026, 7, 15).date(), ts) == 780

    def test_minutes_in_local_day_cross_midnight(self) -> None:
        ts = datetime(2026, 7, 15, 1, 0, tzinfo=AR)
        assert minutes_in_local_day(datetime(2026, 7, 14).date(), ts) == 1500

    def test_resolve_active_phase_id_window(self) -> None:
        phases = _default_day_phase_rows()
        assert resolve_active_phase_id(phases, 780) == UUID(OP_P2)

    def test_resolve_active_phase_id_no_match(self) -> None:
        assert resolve_active_phase_id(_default_day_phase_rows(), 100) is None

    def test_resolve_zone_type_id_direct_slug(self) -> None:
        type_map = {"comida": UUID(ZT_COMIDA), "bano": UUID(ZT_BANO)}
        assert resolve_zone_type_id(type_map, "comida", None) == UUID(ZT_COMIDA)

    def test_resolve_zone_type_id_via_subtipo(self) -> None:
        type_map = {"bano": UUID(ZT_BANO)}
        assert resolve_zone_type_id(type_map, "servicios", "banos") == UUID(ZT_BANO)

    def test_resolve_zone_type_id_missing_returns_none(self) -> None:
        assert resolve_zone_type_id({}, "servicios", "banos") is None


class TestOperationalEventAdapter:
    async def test_no_events_returns_empty_sequence(self) -> None:
        adapter = OperationalEventAdapter(_make_session([]))
        events = await adapter.find_active_by_timestamp(TS)
        assert events == []
        assert isinstance(events, list)

    async def test_events_query_applies_window_and_is_active_filters(self) -> None:
        event_rows = [
            _event_row(
                "eeeeeeee-0000-0000-0000-000000000001",
                ZONE_A,
                "aumento_demanda",
                10,
            ),
        ]
        session = _make_session(
            event_rows,
            zone_rows=_default_zone_rows(),
            zone_type_rows=_default_zone_type_rows(),
            day_phase_rows=_default_day_phase_rows(),
        )
        adapter = OperationalEventAdapter(session)

        await adapter.find_active_by_timestamp(TS)

        events_sql = session.captured_stmts[0]
        assert "operational_events" in events_sql
        assert "operational_events.is_active" in events_sql
        assert "operational_events.start_timestamp <=" in events_sql
        assert "operational_events.end_timestamp >" in events_sql

    async def test_maps_formulas_density_and_skips(self) -> None:
        event_rows = [
            _event_row(
                "eeeeeeee-0000-0000-0000-000000000001",
                ZONE_A,
                "reduccion_capacidad",
                40,
                is_active=True,
            ),
            _event_row(
                "eeeeeeee-0000-0000-0000-000000000002",
                ZONE_B,
                "cierre_total",
                None,
                is_incident=True,
                is_active=True,
            ),
            _event_row(
                "eeeeeeee-0000-0000-0000-000000000003",
                ZONE_A,
                "aumento_demanda",
                25,
                is_active=True,
            ),
            _event_row(
                "eeeeeeee-0000-0000-0000-000000000004",
                ZONE_A,
                "incidente_sin_impacto",
                None,
                is_incident=True,
                is_active=True,
            ),
        ]
        session = _make_session(
            event_rows,
            zone_rows=_default_zone_rows(),
            zone_type_rows=_default_zone_type_rows(),
            day_phase_rows=_default_day_phase_rows(),
            behavior_rows=_default_behavior_rows(),
        )
        adapter = OperationalEventAdapter(session)

        events = await adapter.find_active_by_timestamp(TS)

        assert [e.impact_value for e in events] == [-20, -40, 25, 0]
        assert [e.target_zone_id for e in events] == [
            UUID(ZONE_A),
            UUID(ZONE_B),
            UUID(ZONE_A),
            UUID(ZONE_A),
        ]
        assert [e.is_incident for e in events] == [False, True, False, True]
        assert all(isinstance(e, OperationalEvent) for e in events)
        assert events[0].id == UUID("eeeeeeee-0000-0000-0000-000000000001")
        assert events[0].start_timestamp == datetime(2026, 7, 15, 12, 0, tzinfo=AR)
        assert events[0].end_timestamp == datetime(2026, 7, 15, 14, 0, tzinfo=AR)

    async def test_filters_inactive_expired_and_out_of_window(self) -> None:
        event_rows = [
            _event_row(
                "eeeeeeee-0000-0000-0000-000000000011",
                ZONE_A,
                "aumento_demanda",
                10,
                is_active=False,
            ),
            _event_row(
                "eeeeeeee-0000-0000-0000-000000000012",
                ZONE_A,
                "aumento_demanda",
                10,
                start_min=0,
                end_min=780,
            ),
            _event_row(
                "eeeeeeee-0000-0000-0000-000000000013",
                ZONE_A,
                "aumento_demanda",
                10,
                start_min=781,
                end_min=960,
            ),
        ]
        adapter = OperationalEventAdapter(
            _make_session(
                event_rows,
                zone_rows=_default_zone_rows(),
                zone_type_rows=_default_zone_type_rows(),
                day_phase_rows=_default_day_phase_rows(),
            )
        )

        events = await adapter.find_active_by_timestamp(TS)
        assert events == []

    async def test_skips_null_and_unknown_zone(self) -> None:
        event_rows = [
            _event_row(
                "eeeeeeee-0000-0000-0000-000000000021",
                None,
                "aumento_demanda",
                10,
            ),
            _event_row(
                "eeeeeeee-0000-0000-0000-000000000022",
                MISSING_ZONE,
                "aumento_demanda",
                10,
            ),
        ]
        adapter = OperationalEventAdapter(
            _make_session(
                event_rows,
                zone_rows=_default_zone_rows(),
                zone_type_rows=_default_zone_type_rows(),
                day_phase_rows=_default_day_phase_rows(),
            )
        )

        events = await adapter.find_active_by_timestamp(TS)
        assert events == []

    async def test_skips_zone_without_cataloged_zone_type(self) -> None:
        event_rows = [
            _event_row(
                "eeeeeeee-0000-0000-0000-000000000031",
                ZONE_A,
                "aumento_demanda",
                10,
            ),
        ]
        zone_type_rows = [
            SimpleNamespace(slug="bano", id=ZT_BANO),
        ]
        adapter = OperationalEventAdapter(
            _make_session(
                event_rows,
                zone_rows=_default_zone_rows(),
                zone_type_rows=zone_type_rows,
                day_phase_rows=_default_day_phase_rows(),
            )
        )

        events = await adapter.find_active_by_timestamp(TS)
        assert events == []

    async def test_default_density_when_no_zone_behavior(self) -> None:
        event_rows = [
            _event_row(
                "eeeeeeee-0000-0000-0000-000000000041",
                ZONE_C,
                "reduccion_capacidad",
                50,
            ),
        ]
        session = _make_session(
            event_rows,
            zone_rows=_default_zone_rows(),
            zone_type_rows=_default_zone_type_rows(),
            day_phase_rows=_default_day_phase_rows(),
            behavior_rows=_default_behavior_rows(),
        )
        adapter = OperationalEventAdapter(session)

        events = await adapter.find_active_by_timestamp(TS)
        assert [e.impact_value for e in events] == [-30]

    async def test_default_density_when_no_active_phase(self) -> None:
        event_rows = [
            _event_row(
                "eeeeeeee-0000-0000-0000-000000000051",
                ZONE_C,
                "reduccion_capacidad",
                50,
            ),
        ]
        day_phase_rows = [
            SimpleNamespace(
                event_day_id=EVENT_DAY_ID,
                operational_phase_id=OP_P1,
                start_min=1200,
                end_min=1440,
            )
        ]
        adapter = OperationalEventAdapter(
            _make_session(
                event_rows,
                zone_rows=_default_zone_rows(),
                zone_type_rows=_default_zone_type_rows(),
                day_phase_rows=day_phase_rows,
                behavior_rows=_default_behavior_rows(),
            )
        )

        events = await adapter.find_active_by_timestamp(TS)
        assert [e.impact_value for e in events] == [-30]

    async def test_impact_is_clamped_to_domain_range(self) -> None:
        event_rows = [
            _event_row(
                "eeeeeeee-0000-0000-0000-000000000061",
                ZONE_A,
                "cierre_total",
                None,
            ),
            _event_row(
                "eeeeeeee-0000-0000-0000-000000000062",
                ZONE_A,
                "aumento_demanda",
                250,
            ),
        ]
        behavior_rows = [
            SimpleNamespace(
                zone_type_id=ZT_COMIDA,
                operational_phase_id=OP_P2,
                density_factor=1.0,
            ),
        ]
        adapter = OperationalEventAdapter(
            _make_session(
                event_rows,
                zone_rows=_default_zone_rows(),
                zone_type_rows=_default_zone_type_rows(),
                day_phase_rows=_default_day_phase_rows(),
                behavior_rows=behavior_rows,
            )
        )

        events = await adapter.find_active_by_timestamp(TS)
        assert [e.impact_value for e in events] == [-100, 100]

    async def test_multiple_events_same_zone_accumulate(self) -> None:
        event_rows = [
            _event_row(
                "eeeeeeee-0000-0000-0000-000000000071",
                ZONE_A,
                "reduccion_capacidad",
                50,
            ),
            _event_row(
                "eeeeeeee-0000-0000-0000-000000000072",
                ZONE_A,
                "aumento_demanda",
                30,
            ),
        ]
        adapter = OperationalEventAdapter(
            _make_session(
                event_rows,
                zone_rows=_default_zone_rows(),
                zone_type_rows=_default_zone_type_rows(),
                day_phase_rows=_default_day_phase_rows(),
                behavior_rows=_default_behavior_rows(),
            )
        )

        events = await adapter.find_active_by_timestamp(TS)

        assert len(events) == 2
        assert [e.target_zone_id for e in events] == [UUID(ZONE_A), UUID(ZONE_A)]
        assert [e.impact_value for e in events] == [-25, 30]
        assert sum(e.impact_value for e in events) == 5

    async def test_latitude_longitude_do_not_affect_calculation(self) -> None:
        coordenadas = (-31.4201, -64.1888)
        event_rows = [
            _event_row(
                "eeeeeeee-0000-0000-0000-000000000081",
                ZONE_A,
                "reduccion_capacidad",
                40,
                latitude=coordenadas[0],
                longitude=coordenadas[1],
            ),
            _event_row(
                "eeeeeeee-0000-0000-0000-000000000082",
                ZONE_A,
                "reduccion_capacidad",
                40,
                latitude=None,
                longitude=None,
            ),
        ]
        adapter = OperationalEventAdapter(
            _make_session(
                event_rows,
                zone_rows=_default_zone_rows(),
                zone_type_rows=_default_zone_type_rows(),
                day_phase_rows=_default_day_phase_rows(),
                behavior_rows=_default_behavior_rows(),
            )
        )

        events = await adapter.find_active_by_timestamp(TS)

        assert len(events) == 2
        assert [e.impact_value for e in events] == [-20, -20]

    async def test_save_raises_not_implemented(self) -> None:
        adapter = OperationalEventAdapter(_make_session([]))
        with pytest.raises(NotImplementedError):
            await adapter.save(
                OperationalEvent(
                    target_zone_id=UUID(ZONE_A),
                    impact_value=-20,
                    is_incident=False,
                    start_timestamp=datetime(2026, 7, 15, 12, 0, tzinfo=AR),
                    end_timestamp=datetime(2026, 7, 15, 14, 0, tzinfo=AR),
                )
            )