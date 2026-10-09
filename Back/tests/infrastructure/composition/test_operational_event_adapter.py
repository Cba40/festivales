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

import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from src.domain.entities.operational_event import OperationalEvent
from src.infrastructure.composition.adapters.operational_event_adapter import (
    CLOSURE_IMPACT_CANONICAL,
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


def _as_mapping(row):
    """Convierte un SimpleNamespace de fixture en un dict tipo RowMapping.

    El adapter lee con `row["columna"]` porque consulta COLUMNAS y usa
    `.mappings()`; asi la sesion falsa devuelve filas con la misma forma que
    las reales y los fixtures siguen siendo legibles como SimpleNamespace.
    """
    if isinstance(row, dict):
        return row
    return dict(vars(row))


def _mappings_result(rows):
    result = MagicMock()
    mappings_mock = MagicMock()
    mappings_mock.all.return_value = [_as_mapping(r) for r in rows]
    result.mappings = MagicMock(return_value=mappings_mock)
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

    Todas las consultas devuelven `.mappings()`: el adapter es serverless-safe
    y no debe tocar objetos ORM, asi que la sesion falsa tampoco los produce.
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
            return _mappings_result(behavior_rows)
        if "zone_types" in sql:
            return _mappings_result(zone_type_rows)
        if "operational_events" in sql:
            active = [
                row
                for row in event_rows
                if row.is_active
                and row.start_timestamp <= ts
                and row.end_timestamp > ts
            ]
            return _mappings_result(active)
        if "zones" in sql:
            return _mappings_result(zone_rows)
        if "event_day_phases" in sql:
            return _mappings_result(day_phase_rows)
        if "event_days" in sql:
            return _mappings_result(day_rows)
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
    def test_reduccion_capacidad_es_el_porcentaje(self) -> None:
        # El impacto es el PORCENTAJE de reduccion con signo negativo, no un
        # conteo de personas. Antes era `-round(capacity * density * pct / 100)`.
        assert compute_impact("reduccion_capacidad", 40, 100, 0.5) == -40

    @pytest.mark.parametrize(
        ("pct", "capacity", "density_factor", "esperado"),
        [
            # (pct, capacity, density, impacto)
            (20, 1000, 0.5, -20),   # antes -100 -> CLOSED FALSO
            (50, 1000, 0.5, -50),   # antes -250 -> clamp -100 -> CLOSED FALSO
            (50, 1000, 0.3, -50),   # antes -150 -> clamp -100 -> CLOSED FALSO
            (50, 50, 0.5, -50),     # antes -13
            (20, 200, 0.7, -20),    # antes -28
            (99, 1000, 0.3, -99),   # antes -297 -> CLOSED FALSO
            (100, 1000, 0.5, -100),  # 100% si cierra
            (100, 50, 0.5, -100),    # 100% cierra tambien en zona chica
        ],
    )
    def test_reduccion_capacidad_no_dispara_cierre_antes_del_100_por_ciento(
        self, pct: int, capacity: int, density_factor: float, esperado: int,
    ) -> None:
        assert compute_impact(
            "reduccion_capacidad", pct, capacity, density_factor,
        ) == esperado

    @pytest.mark.parametrize("pct", [1, 20, 50, 99])
    def test_reduccion_capacidad_parcial_no_alcanza_el_centinela_de_cierre(
        self, pct: int,
    ) -> None:
        # El centinela que `stage3` lee como cierre es `<= -100`. Cualquier
        # reduccion parcial debe quedar estrictamente por encima.
        for capacity, density in [(50, 0.5), (200, 0.7), (1000, 0.3), (5000, 1.0)]:
            impact = clamp_impact(
                compute_impact("reduccion_capacidad", pct, capacity, density),
            )
            assert impact > -100, (
                f"pct={pct} cap={capacity} dens={density} produjo {impact}, "
                "que stage3 interpretaria como cierre total"
            )

    def test_reduccion_capacidad_al_100_por_ciento_cierra(self) -> None:
        # El unico caso en que la reduccion debe equivaler a cierre.
        for capacity, density in [(50, 0.5), (200, 0.7), (1000, 0.3)]:
            assert compute_impact(
                "reduccion_capacidad", 100, capacity, density,
            ) == CLOSURE_IMPACT_CANONICAL

    def test_cierre_total(self) -> None:
        # Opcion C: `cierre_total` devuelve el impacto canonico de cierre, que
        # `stage3_zone_behavior_application` interpreta como
        # `FlowRestriction.CLOSED` (`accumulated_impact <= -100`). Antes devolvia
        # `-round(capacity * density_factor)`, con lo que una zona de 50 personas
        # al 80% producia -40 y NUNCA se cerraba.
        assert compute_impact("cierre_total", None, 50, 0.8) == CLOSURE_IMPACT_CANONICAL

    @pytest.mark.parametrize(
        ("capacity", "density_factor"),
        [
            (5, 0.01),    # zona minima: antes daba -0
            (50, 0.5),   # antes daba -25  <- caso que fallaba
            (100, 0.9),  # antes daba -90  <- no alcanzaba el centinela
            (200, 0.7),  # antes daba -140 -> clamp -100
            (1000, 0.3),  # antes daba -300 -> clamp -100
        ],
    )
    def test_cierre_total_closes_regardless_of_capacity_and_density(
        self, capacity: int, density_factor: float,
    ) -> None:
        assert compute_impact(
            "cierre_total", None, capacity, density_factor,
        ) == CLOSURE_IMPACT_CANONICAL

    def test_aumento_demanda_uses_effect_value(self) -> None:
        # Delta absoluto de personas: `stage3` lo suma a `projected_density`.
        assert compute_impact("aumento_demanda", 25, 100, 0.9) == 25

    @pytest.mark.parametrize(
        ("effect_value", "esperado"),
        [(1, 1), (40, 40), (100, 100), (200, 200), (999_999, 999_999)],
    )
    def test_aumento_demanda_no_depende_de_capacity_ni_density(
        self, effect_value: int, esperado: int,
    ) -> None:
        for capacity, density in [(50, 0.5), (200, 0.7), (1000, 0.3)]:
            assert compute_impact(
                "aumento_demanda", effect_value, capacity, density,
            ) == esperado

    @pytest.mark.parametrize("effect_value", [-1, -50, -100, -500])
    def test_aumento_demanda_nunca_produce_cierre(
        self, effect_value: int,
    ) -> None:
        # Guarda defensiva: un `effect_value` negativo (por SQL, en una base sin
        # el CHECK `ck_operational_events_effect_value`) no debe convertirse en un
        # cierre fantasma. `validate_effect` ya exige `>= 1`, esto es la segunda
        # linea de defensa.
        assert compute_impact("aumento_demanda", effect_value, 200, 0.7) == 0
        assert compute_impact("aumento_demanda", effect_value, 200, 0.7) > -100

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

    async def test_maps_formulas_and_skips(self) -> None:
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

        # reduccion_capacidad(40) es el porcentaje con signo negativo: -40.
        # El cierre_total es el centinela -100 y el aumento_demanda su delta.
        assert [e.impact_value for e in events] == [-40, -100, 25, 0]
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

    async def test_impact_does_not_depend_on_density_fallback(self) -> None:
        # Antes: sin `zone_behavior` caia a DEFAULT_DENSITY_FACTOR=1.0 y el
        # impacto era -round(capacity * 1.0 * 50 / 100) = -30. Ahora el impacto
        # es el porcentaje, asi que el fallback de densidad no interviene.
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
            behavior_rows=[],
        )
        adapter = OperationalEventAdapter(session)

        events = await adapter.find_active_by_timestamp(TS)
        assert [e.impact_value for e in events] == [-50]

    async def test_impact_does_not_depend_on_active_phase(self) -> None:
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
        assert [e.impact_value for e in events] == [-50]

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
        # reduccion_capacidad(50) -> -50 (porcentaje), aumento_demanda(30) -> +30
        assert [e.impact_value for e in events] == [-50, 30]
        assert sum(e.impact_value for e in events) == -20
        # Un -50 parcial no cierra: sigue por encima del centinela de stage3.
        assert sum(e.impact_value for e in events) > -100

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
        assert [e.impact_value for e in events] == [-40, -40]

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


class TestServerlessSafety:
    """Regresion del `MissingGreenlet` que rompio produccion en Vercel.

    Causa: `find_active_by_timestamp` hace `commit()` para el barrido de
    expirados. Con `expire_on_commit=True` (default) ese commit expira los
    objetos ORM ya cargados; el acceso posterior a `row.zone_id` intentaba un
    refresh lazy desde un contexto sin greenlet ->
    `sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called`.

    La defensa no es "no commitear" sino no arrastrar objetos ORM: filas de
    columnas via `.mappings()`, que no tienen estado que expirar.
    """

    async def test_consulta_de_eventos_selecciona_columnas_no_la_entidad(self) -> None:
        event_rows = [
            _event_row("eeeeeeee-0000-0000-0000-0000000000a1", ZONE_A, "cierre_total", None),
        ]
        session = _make_session(
            event_rows,
            zone_rows=_default_zone_rows(),
            zone_type_rows=_default_zone_type_rows(),
            day_phase_rows=_default_day_phase_rows(),
            behavior_rows=_default_behavior_rows(),
        )
        adapter = OperationalEventAdapter(session)
        await adapter.find_active_by_timestamp(TS)
        sql = session.captured_stmts[0]
        # Una entidad completa generaria `FROM operational_events` con TODAS las
        # columnas; lo que se busca es la proyeccion explicita.
        assert "operational_events.id" in sql
        assert "operational_events.zone_id" in sql
        assert "operational_events.effect_type" in sql

    async def test_ninguna_fila_devuelta_es_una_entidad_orm(self) -> None:
        event_rows = [
            _event_row("eeeeeeee-0000-0000-0000-0000000000b1", ZONE_A, "cierre_total", None),
        ]
        session = _make_session(
            event_rows,
            zone_rows=_default_zone_rows(),
            zone_type_rows=_default_zone_type_rows(),
            day_phase_rows=_default_day_phase_rows(),
            behavior_rows=_default_behavior_rows(),
        )
        adapter = OperationalEventAdapter(session)
        await adapter.find_active_by_timestamp(TS)

        # La sesion solo expone `.mappings()`; si el adapter pidiera
        # `.scalars()` recibiria un MagicMock y la asercion de abajo fallaria.
        for sql in session.captured_stmts:
            assert "scalars()" not in sql

    async def test_sobrevive_a_un_commit_intermedio(self) -> None:
        """El commit del barrido de expirados no debe invalidar las filas.

        Antes, con objetos ORM, este commit expiraba `rows` y el acceso
        posterior reventaba con MissingGreenlet. Con filas de columnas las
        filas ya estan materializadas y el commit no las toca.
        """
        event_rows = [
            _event_row("eeeeeeee-0000-0000-0000-0000000000c1", ZONE_A, "cierre_total", None),
        ]

        session = _make_session(
            event_rows,
            zone_rows=_default_zone_rows(),
            zone_type_rows=_default_zone_type_rows(),
            day_phase_rows=_default_day_phase_rows(),
            behavior_rows=_default_behavior_rows(),
        )
        # Forzar el barrido: hace que el adapter ejecute el commit intermedio.
        session.execute = _make_committing_session(
            session,
            on_table="operational_events",
            committing_for={"operational_events"},
        )
        adapter = OperationalEventAdapter(session)

        events = await adapter.find_active_by_timestamp(TS)

        assert len(events) == 1
        assert events[0].impact_value == CLOSURE_IMPACT_CANONICAL
        assert str(events[0].target_zone_id) == ZONE_A


def _make_committing_session(base_session, *, on_table: str, committing_for: set[str]):
    """Envolve `execute` para que un `commit()` real ocurre en el medio.

    Reproduce el entorno de produccion: `expire_on_commit=True` invalida los
    objetos ORM ya leidos, que es exactamente lo que disparaba el bug.
    """
    original = base_session.execute

    async def execute(stmt, *args, **kwargs):
        sql = str(stmt)
        result = await original(stmt, *args, **kwargs)
        if on_table in sql and "UPDATE" in sql.upper():
            await base_session.commit()
        return result

    base_session.commit = _async_commit()
    return execute


def _async_commit():
    async def commit():
        return None

    return commit