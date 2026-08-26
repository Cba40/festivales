# backend/tests/models/test_transport_line_stop.py
# S1 Transporte V1 - PARTE 2: tabla transport_line_stops.

import pytest
from sqlalchemy import UniqueConstraint, select
from sqlalchemy.exc import IntegrityError

from app.db.session import Base
from app.models.event import Event
from app.models.transport_line import TransportLine
from app.models.transport_line_stop import TransportLineStop
from app.models.zone import Zone


def _get_relationships(model):
    model.__mapper__.relationships
    return {rel.key: rel for rel in model.__mapper__.relationships}


class TestTransportLineStopSchema:
    """Estructura del modelo: tabla, columnas, constraints."""

    def test_table_name(self) -> None:
        assert TransportLineStop.__tablename__ == "transport_line_stops"

    def test_inherits_base(self) -> None:
        assert issubclass(TransportLineStop, Base)

    def test_registered_in_base_metadata(self) -> None:
        assert "transport_line_stops" in Base.metadata.tables

    def test_id_is_primary_key_string36(self) -> None:
        col = TransportLineStop.__table__.columns["id"]
        assert col.primary_key
        assert col.type.length == 36

    def test_line_id_fk_to_transport_lines_with_cascade(self) -> None:
        col = TransportLineStop.__table__.columns["line_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert fks[0].target_fullname == "transport_lines.id"
        assert fks[0].ondelete == "CASCADE"

    def test_zone_id_fk_to_zones_with_cascade(self) -> None:
        col = TransportLineStop.__table__.columns["zone_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert fks[0].target_fullname == "zones.id"
        assert fks[0].ondelete == "CASCADE"

    def test_stop_order_is_required_integer(self) -> None:
        col = TransportLineStop.__table__.columns["stop_order"]
        assert col.nullable is False

    def test_unique_constraint_line_zone(self) -> None:
        uqs = [
            c for c in TransportLineStop.__table__.constraints
            if isinstance(c, UniqueConstraint)
        ]
        matching = [
            u for u in uqs
            if {c.name for c in u.columns} == {"line_id", "zone_id"}
        ]
        assert len(matching) == 1
        assert matching[0].name == "uq_transport_line_stops_line_zone"

    def test_unique_constraint_line_order(self) -> None:
        uqs = [
            c for c in TransportLineStop.__table__.constraints
            if isinstance(c, UniqueConstraint)
        ]
        matching = [
            u for u in uqs
            if {c.name for c in u.columns} == {"line_id", "stop_order"}
        ]
        assert len(matching) == 1
        assert matching[0].name == "uq_transport_line_stops_line_order"

    def test_index_on_line_id(self) -> None:
        index_names = {idx.name for idx in TransportLineStop.__table__.indexes}
        assert "idx_tls_line" in index_names

    def test_index_on_zone_id(self) -> None:
        index_names = {idx.name for idx in TransportLineStop.__table__.indexes}
        assert "idx_tls_zone" in index_names


class TestRelationshipWiring:
    """Relaciones entre TransportLine, TransportLineStop y Zone."""

    def test_transport_line_has_stops_relationship(self) -> None:
        rels = _get_relationships(TransportLine)
        assert "stops" in rels

    def test_transport_line_stop_has_line_relationship(self) -> None:
        rels = _get_relationships(TransportLineStop)
        assert "line" in rels

    def test_transport_line_stop_has_zone_relationship(self) -> None:
        rels = _get_relationships(TransportLineStop)
        assert "zone" in rels

    def test_zone_has_transport_line_stops_relationship(self) -> None:
        rels = _get_relationships(Zone)
        assert "transport_line_stops" in rels

    def test_back_populates_line_stops(self) -> None:
        tl_rels = _get_relationships(TransportLine)
        tls_rels = _get_relationships(TransportLineStop)
        assert tl_rels["stops"].back_populates == "line"
        assert tls_rels["line"].back_populates == "stops"

    def test_back_populates_zone_stops(self) -> None:
        zone_rels = _get_relationships(Zone)
        tls_rels = _get_relationships(TransportLineStop)
        assert zone_rels["transport_line_stops"].back_populates == "zone"
        assert tls_rels["zone"].back_populates == "transport_line_stops"

    def test_relationship_targets(self) -> None:
        tls_rels = _get_relationships(TransportLineStop)
        assert tls_rels["line"].mapper.entity is TransportLine
        assert tls_rels["zone"].mapper.entity is Zone


class TestTransportLineStopPersistence:
    """Comportamiento real contra Postgres (fixtures de conftest)."""

    def _make_line(self, db_session, event_id: str = "test-event-1") -> TransportLine:
        line = TransportLine(
            event_id=event_id,
            name="Línea 100",
            type="urbano",
            company="Empresa A",
        )
        db_session.add(line)
        db_session.flush()
        return line

    def _make_zone(self, db_session, event_id: str = "test-event-1") -> Zone:
        zone = Zone(
            event_id=event_id,
            name="Parada Central",
            type="transporte",
            capacity=300,
        )
        db_session.add(zone)
        db_session.flush()
        return zone

    def test_create_with_defaults(self, db_session, sample_event) -> None:
        line = self._make_line(db_session, sample_event.id)
        zone = self._make_zone(db_session, sample_event.id)

        tls = TransportLineStop(line_id=line.id, zone_id=zone.id, stop_order=1)
        db_session.add(tls)
        db_session.flush()

        assert tls.id is not None
        assert len(tls.id) == 36
        assert tls.line_id == line.id
        assert tls.zone_id == zone.id
        assert tls.stop_order == 1

    def test_cascade_delete_with_line(self, db_session, sample_event) -> None:
        line = self._make_line(db_session, sample_event.id)
        zone1 = self._make_zone(db_session, sample_event.id)
        zone2 = self._make_zone(db_session, sample_event.id)
        # Rename zone2 to avoid unique name constraint
        zone2.name = "Parada Norte"

        db_session.add(TransportLineStop(line_id=line.id, zone_id=zone1.id, stop_order=1))
        db_session.add(TransportLineStop(line_id=line.id, zone_id=zone2.id, stop_order=2))
        db_session.flush()

        db_session.delete(line)
        db_session.flush()

        remaining = db_session.execute(
            select(TransportLineStop)
        ).scalars().all()
        assert remaining == []

    def test_cascade_delete_with_zone(self, db_session, sample_event) -> None:
        line = self._make_line(db_session, sample_event.id)
        zone = self._make_zone(db_session, sample_event.id)

        db_session.add(TransportLineStop(line_id=line.id, zone_id=zone.id, stop_order=1))
        db_session.flush()

        db_session.delete(zone)
        db_session.flush()

        remaining = db_session.execute(
            select(TransportLineStop)
        ).scalars().all()
        assert remaining == []

    def test_duplicate_line_zone_rejected(self, db_session, sample_event) -> None:
        line = self._make_line(db_session, sample_event.id)
        zone = self._make_zone(db_session, sample_event.id)

        db_session.add(TransportLineStop(line_id=line.id, zone_id=zone.id, stop_order=1))
        db_session.flush()

        db_session.add(TransportLineStop(line_id=line.id, zone_id=zone.id, stop_order=2))
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_duplicate_line_order_rejected(self, db_session, sample_event) -> None:
        line = self._make_line(db_session, sample_event.id)
        zone1 = self._make_zone(db_session, sample_event.id)
        zone2 = self._make_zone(db_session, sample_event.id)
        zone2.name = "Parada Norte"

        db_session.add(TransportLineStop(line_id=line.id, zone_id=zone1.id, stop_order=1))
        db_session.flush()

        db_session.add(TransportLineStop(line_id=line.id, zone_id=zone2.id, stop_order=1))
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_same_zone_in_multiple_lines_allowed(self, db_session, sample_event) -> None:
        line1 = TransportLine(
            event_id=sample_event.id, name="Línea A",
            type="urbano", company="Empresa A",
        )
        line2 = TransportLine(
            event_id=sample_event.id, name="Línea B",
            type="urbano", company="Empresa B",
        )
        db_session.add(line1)
        db_session.add(line2)
        db_session.flush()

        zone = self._make_zone(db_session, sample_event.id)

        db_session.add(TransportLineStop(line_id=line1.id, zone_id=zone.id, stop_order=1))
        db_session.add(TransportLineStop(line_id=line2.id, zone_id=zone.id, stop_order=1))
        db_session.flush()

        all_stops = db_session.execute(select(TransportLineStop)).scalars().all()
        assert len(all_stops) == 2

    def test_same_order_in_different_lines_allowed(self, db_session, sample_event) -> None:
        line1 = TransportLine(
            event_id=sample_event.id, name="Línea A",
            type="urbano", company="Empresa A",
        )
        line2 = TransportLine(
            event_id=sample_event.id, name="Línea B",
            type="urbano", company="Empresa B",
        )
        db_session.add(line1)
        db_session.add(line2)
        db_session.flush()

        zone1 = self._make_zone(db_session, sample_event.id)
        zone2 = self._make_zone(db_session, sample_event.id)
        zone2.name = "Parada Norte"

        db_session.add(TransportLineStop(line_id=line1.id, zone_id=zone1.id, stop_order=1))
        db_session.add(TransportLineStop(line_id=line2.id, zone_id=zone2.id, stop_order=1))
        db_session.flush()

        all_stops = db_session.execute(select(TransportLineStop)).scalars().all()
        assert len(all_stops) == 2
