"""Tests del modelo y schemas de OperationalEvent V1 (RFC-OPERATIONAL-EVENTS-V1)."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import CheckConstraint, Index
from sqlalchemy.exc import IntegrityError

from app.models.operational_event import EFFECT_TYPES, EVENT_TYPES, OperationalEvent
from app.schemas.operational_event import (
    EffectType,
    EventType,
    OperationalEventCreate,
    OperationalEventUpdate,
    OperationalEventResponse,
)

VALID_DATA = {
    "event_day_id": "test-day-1",
    "zone_id": "zone-comida-1",
    "event_type": "accidente",
    "description": "Accidente en acceso norte",
    "effect_type": "reduccion_capacidad",
    "effect_value": 50,
    "is_incident": True,
    "start_timestamp": datetime(2026, 8, 30, 20, 0, tzinfo=timezone.utc),
    "end_timestamp": datetime(2026, 8, 30, 22, 0, tzinfo=timezone.utc),
    "latitude": -31.4201,
    "longitude": -64.1888,
}


def make_event(**overrides):
    data = dict(VALID_DATA)
    data.update(overrides)
    return data


class TestOperationalEventSchema:
    """Estructura del modelo: tabla, columnas, constraints, índices."""

    def test_enum_catalogues(self) -> None:
        assert len(EVENT_TYPES) == 11
        assert len(EFFECT_TYPES) == 4

    def test_table_name(self) -> None:
        assert OperationalEvent.__tablename__ == "operational_events"

    def test_columns_exist(self) -> None:
        cols = OperationalEvent.__table__.columns
        for name in (
            "id", "event_day_id", "zone_id", "event_type", "description",
            "effect_type", "effect_value", "is_incident",
            "start_timestamp", "end_timestamp", "is_active",
            "latitude", "longitude",
            "created_at", "updated_at",
        ):
            assert name in cols

    def test_legacy_min_columns_removed(self) -> None:
        cols = OperationalEvent.__table__.columns
        assert "start_min" not in cols
        assert "end_min" not in cols

    def test_new_columns_nullability(self) -> None:
        cols = OperationalEvent.__table__.columns
        assert cols["effect_type"].nullable is False
        assert cols["is_incident"].nullable is False
        assert cols["start_timestamp"].nullable is False
        assert cols["end_timestamp"].nullable is False
        assert cols["effect_value"].nullable is True
        assert cols["description"].nullable is True
        assert cols["zone_id"].nullable is False

    def test_geolocation_columns_nullability_and_type(self) -> None:
        cols = OperationalEvent.__table__.columns
        assert cols["latitude"].nullable is True
        assert cols["longitude"].nullable is True
        assert cols["latitude"].type.precision == 10
        assert cols["latitude"].type.scale == 8
        assert cols["longitude"].type.precision == 11
        assert cols["longitude"].type.scale == 8

    def test_geolocation_check_constraints(self) -> None:
        checks = {
            c.name: c for c in OperationalEvent.__table__.constraints
            if isinstance(c, CheckConstraint)
        }
        assert "ck_operational_events_latitude" in checks
        assert "latitude IS NULL OR (latitude BETWEEN -90 AND 90)" in checks["ck_operational_events_latitude"].sqltext.text
        assert "ck_operational_events_longitude" in checks
        assert "longitude IS NULL OR (longitude BETWEEN -180 AND 180)" in checks["ck_operational_events_longitude"].sqltext.text

    def test_timestamp_columns_have_timezone(self) -> None:
        cols = OperationalEvent.__table__.columns
        for name in ("start_timestamp", "end_timestamp", "created_at", "updated_at"):
            assert cols[name].type.timezone is True

    def test_is_incident_has_server_default(self) -> None:
        col = OperationalEvent.__table__.columns["is_incident"]
        assert col.server_default is not None

    def test_temporal_check_constraint(self) -> None:
        checks = [
            c for c in OperationalEvent.__table__.constraints
            if isinstance(c, CheckConstraint) and c.name == "ck_operational_events_temporal"
        ]
        assert len(checks) == 1
        assert "end_timestamp > start_timestamp" in checks[0].sqltext.text

    def test_effect_value_check_constraint(self) -> None:
        checks = [
            c for c in OperationalEvent.__table__.constraints
            if isinstance(c, CheckConstraint) and c.name == "ck_operational_events_effect_value"
        ]
        assert len(checks) == 1
        text_ = checks[0].sqltext.text
        assert "reduccion_capacidad" in text_
        assert "cierre_total" in text_
        assert "aumento_demanda" in text_
        assert "incidente_sin_impacto" in text_

    def test_indexes_exist(self) -> None:
        names = {idx.name for idx in OperationalEvent.__table__.indexes}
        assert "ix_operational_events_event_day_id" in names
        assert "ix_operational_events_zone_id" in names
        assert "ix_operational_events_active_window" in names

    def test_active_window_index_configuration(self) -> None:
        idx = next(
            i for i in OperationalEvent.__table__.indexes
            if i.name == "ix_operational_events_active_window"
        )
        cols = [c.name for c in idx.columns]
        assert cols == ["is_active", "start_timestamp", "end_timestamp"]
        assert idx.dialect_options["postgresql"]["where"] is not None

    def test_relationships_preserved(self) -> None:
        assert "event_day" in OperationalEvent.__mapper__.relationships
        assert "zone" in OperationalEvent.__mapper__.relationships


class TestOperationalEventPersistence:
    """Comportamiento real contra la base de datos."""

    @pytest.mark.parametrize("effect_type,effect_value", [
        ("reduccion_capacidad", 50),
        ("cierre_total", None),
        ("aumento_demanda", 200),
        ("incidente_sin_impacto", None),
    ])
    def test_create_valid_each_effect(
        self, db_session, sample_event_day,
        effect_type: str, effect_value,
    ) -> None:
        data = make_event(effect_type=effect_type, effect_value=effect_value)
        event = OperationalEvent(**data)
        db_session.add(event)
        db_session.flush()

        assert event.id is not None
        assert event.effect_type == effect_type
        assert event.effect_value == effect_value
        assert event.is_incident is True
        assert event.is_active is True

    def test_temporal_constraint_rejects_end_before_start(self, db_session, sample_event_day) -> None:
        start = datetime(2026, 8, 30, 22, 0, tzinfo=timezone.utc)
        end = datetime(2026, 8, 30, 20, 0, tzinfo=timezone.utc)
        event = OperationalEvent(**make_event(start_timestamp=start, end_timestamp=end))
        db_session.add(event)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_temporal_constraint_rejects_equal_timestamps(self, db_session, sample_event_day) -> None:
        ts = datetime(2026, 8, 30, 20, 0, tzinfo=timezone.utc)
        event = OperationalEvent(**make_event(start_timestamp=ts, end_timestamp=ts))
        db_session.add(event)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    @pytest.mark.parametrize("effect_type,effect_value,expected_ok", [
        ("reduccion_capacidad", 50, True),
        ("reduccion_capacidad", 0, False),
        ("reduccion_capacidad", 101, False),
        ("reduccion_capacidad", None, False),
        ("cierre_total", None, True),
        ("cierre_total", 50, False),
        ("aumento_demanda", 200, True),
        ("aumento_demanda", 0, False),
        ("aumento_demanda", None, False),
        ("incidente_sin_impacto", None, True),
        ("incidente_sin_impacto", 1, False),
    ])
    def test_effect_value_constraint(
        self, db_session, sample_event_day,
        effect_type: str, effect_value, expected_ok: bool,
    ) -> None:
        event = OperationalEvent(**make_event(effect_type=effect_type, effect_value=effect_value))
        db_session.add(event)
        if expected_ok:
            db_session.flush()
            assert event.effect_value == effect_value
        else:
            with pytest.raises(IntegrityError):
                db_session.flush()
            db_session.rollback()

    @pytest.mark.parametrize("latitude,expected_ok", [
        (45.5, True),
        (-90, True),
        (90, True),
        (91, False),
        (-91, False),
        (None, True),
    ])
    def test_latitude_constraint(
        self, db_session, sample_event_day,
        latitude, expected_ok: bool,
    ) -> None:
        event = OperationalEvent(**make_event(latitude=latitude))
        db_session.add(event)
        if expected_ok:
            db_session.flush()
            assert event.latitude == latitude
        else:
            with pytest.raises(IntegrityError):
                db_session.flush()
            db_session.rollback()

    @pytest.mark.parametrize("longitude,expected_ok", [
        (120.5, True),
        (-180, True),
        (180, True),
        (181, False),
        (-181, False),
        (None, True),
    ])
    def test_longitude_constraint(
        self, db_session, sample_event_day,
        longitude, expected_ok: bool,
    ) -> None:
        event = OperationalEvent(**make_event(longitude=longitude))
        db_session.add(event)
        if expected_ok:
            db_session.flush()
            assert event.longitude == longitude
        else:
            with pytest.raises(IntegrityError):
                db_session.flush()
            db_session.rollback()

    def test_persists_coordinates(
        self, db_session, sample_event_day,
    ) -> None:
        event = OperationalEvent(**make_event())
        db_session.add(event)
        db_session.flush()
        assert event.latitude == -31.4201
        assert event.longitude == -64.1888


class TestOperationalEventSchemas:
    """Validación Pydantic."""

    def test_create_valid(self) -> None:
        schema = OperationalEventCreate(**VALID_DATA)
        assert schema.effect_type == "reduccion_capacidad"
        assert schema.end_timestamp > schema.start_timestamp

    def test_create_rejects_end_before_start(self) -> None:
        data = make_event(
            start_timestamp=datetime(2026, 8, 30, 22, 0, tzinfo=timezone.utc),
            end_timestamp=datetime(2026, 8, 30, 20, 0, tzinfo=timezone.utc),
        )
        with pytest.raises(ValueError):
            OperationalEventCreate(**data)

    def test_create_rejects_unknown_event_type(self) -> None:
        with pytest.raises(ValueError):
            OperationalEventCreate(**make_event(event_type="terremoto"))

    def test_create_rejects_unknown_effect_type(self) -> None:
        with pytest.raises(ValueError):
            OperationalEventCreate(**make_event(effect_type="cierre_parcial"))

    @pytest.mark.parametrize("effect_type,effect_value", [
        ("reduccion_capacidad", None),
        ("reduccion_capacidad", 0),
        ("reduccion_capacidad", 101),
        ("cierre_total", 50),
        ("aumento_demanda", 0),
        ("aumento_demanda", None),
        ("incidente_sin_impacto", 1),
    ])
    def test_create_rejects_invalid_effect_value(self, effect_type: str, effect_value) -> None:
        with pytest.raises(ValueError):
            OperationalEventCreate(**make_event(effect_type=effect_type, effect_value=effect_value))

    def test_update_allows_partial(self) -> None:
        schema = OperationalEventUpdate(description="Nuevo detalle", is_incident=False)
        assert schema.description == "Nuevo detalle"
        assert schema.event_type is None

    def test_update_rejects_end_before_start_when_both_set(self) -> None:
        with pytest.raises(ValueError):
            OperationalEventUpdate(
                start_timestamp=datetime(2026, 8, 30, 22, 0, tzinfo=timezone.utc),
                end_timestamp=datetime(2026, 8, 30, 20, 0, tzinfo=timezone.utc),
            )

    def test_update_rejects_invalid_effect_value(self) -> None:
        with pytest.raises(ValueError):
            OperationalEventUpdate(effect_type="reduccion_capacidad", effect_value=0)

    @pytest.mark.parametrize("latitude", [45.5, -90.0, 90.0, None])
    def test_create_accepts_valid_latitude(self, latitude) -> None:
        schema = OperationalEventCreate(**make_event(latitude=latitude))
        assert schema.latitude == latitude

    @pytest.mark.parametrize("latitude", [91.0, -91.0])
    def test_create_rejects_out_of_range_latitude(self, latitude) -> None:
        with pytest.raises(ValueError):
            OperationalEventCreate(**make_event(latitude=latitude))

    @pytest.mark.parametrize("longitude", [120.5, -180.0, 180.0, None])
    def test_create_accepts_valid_longitude(self, longitude) -> None:
        schema = OperationalEventCreate(**make_event(longitude=longitude))
        assert schema.longitude == longitude

    @pytest.mark.parametrize("longitude", [181.0, -181.0])
    def test_create_rejects_out_of_range_longitude(self, longitude) -> None:
        with pytest.raises(ValueError):
            OperationalEventCreate(**make_event(longitude=longitude))

    def test_update_accepts_coordinates(self) -> None:
        schema = OperationalEventUpdate(latitude=45.5, longitude=-64.1888)
        assert schema.latitude == 45.5
        assert schema.longitude == -64.1888

    def test_update_rejects_out_of_range_coordinates(self) -> None:
        with pytest.raises(ValueError):
            OperationalEventUpdate(latitude=95.0)
        with pytest.raises(ValueError):
            OperationalEventUpdate(longitude=200.0)

    def test_response_from_attributes(self, db_session, sample_event_day) -> None:
        event = OperationalEvent(**make_event())
        db_session.add(event)
        db_session.flush()
        response = OperationalEventResponse.model_validate(event)
        assert response.id == event.id
        assert response.effect_type == "reduccion_capacidad"
        assert response.latitude == event.latitude
        assert response.longitude == event.longitude


VALID_EVENT_TYPES: list = list(EventType.__args__)
VALID_EFFECT_TYPES: list = list(EffectType.__args__)


class TestOperationalEventEnums:
    """Los catálogos cerrados coinciden con el RFC (11 + 4 valores)."""

    def test_event_type_literal_catalog(self) -> None:
        assert set(VALID_EVENT_TYPES) == set(EVENT_TYPES)

    def test_effect_type_literal_catalog(self) -> None:
        assert set(VALID_EFFECT_TYPES) == set(EFFECT_TYPES)

    def test_event_type_catalog_is_closed(self) -> None:
        for value in VALID_EVENT_TYPES:
            assert value in EVENT_TYPES

    def test_all_event_types_are_storable(self, db_session, sample_event_day) -> None:
        for event_type in VALID_EVENT_TYPES:
            event = OperationalEvent(**make_event(event_type=event_type))
            db_session.add(event)
            db_session.flush()