# backend/tests/models/test_transport_line.py
# S1 Transporte V1 - PARTE 1: tabla transport_lines.

import pytest
from sqlalchemy import UniqueConstraint, select
from sqlalchemy.exc import IntegrityError

from app.db.session import Base
from app.models.event import Event
from app.models.transport_line import TransportLine


class TestTransportLineSchema:
    """Estructura del modelo: tabla, columnas, constraints."""

    def test_table_name(self) -> None:
        assert TransportLine.__tablename__ == "transport_lines"

    def test_inherits_base(self) -> None:
        assert issubclass(TransportLine, Base)

    def test_registered_in_base_metadata(self) -> None:
        assert "transport_lines" in Base.metadata.tables

    def test_id_is_primary_key_string36(self) -> None:
        col = TransportLine.__table__.columns["id"]
        assert col.primary_key
        assert col.type.length == 36

    def test_event_id_fk_to_events_with_cascade(self) -> None:
        col = TransportLine.__table__.columns["event_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert fks[0].target_fullname == "events.id"
        assert fks[0].ondelete == "CASCADE"

    def test_name_is_required_string100(self) -> None:
        col = TransportLine.__table__.columns["name"]
        assert col.nullable is False
        assert col.type.length == 100

    def test_type_is_required_string20(self) -> None:
        col = TransportLine.__table__.columns["type"]
        assert col.nullable is False
        assert col.type.length == 20

    def test_company_is_required_string100(self) -> None:
        col = TransportLine.__table__.columns["company"]
        assert col.nullable is False
        assert col.type.length == 100

    def test_color_is_nullable_string7(self) -> None:
        col = TransportLine.__table__.columns["color"]
        assert col.nullable is True
        assert col.type.length == 7

    def test_active_is_required_boolean(self) -> None:
        col = TransportLine.__table__.columns["active"]
        assert col.nullable is False
        assert col.default is not None

    def test_has_timestamps(self) -> None:
        for name in ("created_at", "updated_at"):
            col = TransportLine.__table__.columns[name]
            assert col.server_default is not None
            assert col.type.timezone is True

    def test_unique_constraint_event_name(self) -> None:
        uqs = [
            c for c in TransportLine.__table__.constraints
            if isinstance(c, UniqueConstraint)
        ]
        matching = [
            u for u in uqs
            if {c.name for c in u.columns} == {"event_id", "name"}
        ]
        assert len(matching) == 1
        assert matching[0].name == "uq_transport_lines_event_name"

    def test_index_on_event_id(self) -> None:
        index_names = {idx.name for idx in TransportLine.__table__.indexes}
        assert "idx_transport_lines_event" in index_names


class TestTransportLinePersistence:
    """Comportamiento real contra Postgres (fixtures de conftest)."""

    def test_create_with_defaults(self, db_session, sample_event) -> None:
        line = TransportLine(
            event_id=sample_event.id,
            name="Línea 100",
            type="interurbano",
            company="Empresa Ejemplo SRL",
        )
        db_session.add(line)
        db_session.flush()

        assert line.id is not None
        assert len(line.id) == 36
        assert line.active is True
        assert line.color is None
        assert line.created_at is not None
        assert line.updated_at is not None

    def test_create_with_color(self, db_session, sample_event) -> None:
        line = TransportLine(
            event_id=sample_event.id,
            name="Línea 200",
            type="urbano",
            company="Transporte Urbano SA",
            color="#3498DB",
        )
        db_session.add(line)
        db_session.flush()

        assert line.color == "#3498DB"

    def test_duplicate_name_same_event_rejected(self, db_session, sample_event) -> None:
        db_session.add(TransportLine(
            event_id=sample_event.id,
            name="Línea 100",
            type="urbano",
            company="Empresa A",
        ))
        db_session.flush()

        db_session.add(TransportLine(
            event_id=sample_event.id,
            name="Línea 100",
            type="interurbano",
            company="Empresa B",
        ))
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_same_name_across_different_events_allowed(self, db_session, sample_event) -> None:
        other = Event(id="test-event-tl-2", name="Otro Evento")
        db_session.add(other)
        db_session.flush()

        db_session.add(TransportLine(
            event_id=sample_event.id,
            name="Línea 100",
            type="urbano",
            company="Empresa A",
        ))
        db_session.add(TransportLine(
            event_id=other.id,
            name="Línea 100",
            type="urbano",
            company="Empresa A",
        ))
        db_session.flush()

        all_lines = db_session.execute(select(TransportLine)).scalars().all()
        assert len(all_lines) == 2

    def test_cascade_delete_with_event(self, db_session, sample_event) -> None:
        db_session.add(TransportLine(
            event_id=sample_event.id,
            name="Línea A",
            type="urbano",
            company="Empresa A",
        ))
        db_session.add(TransportLine(
            event_id=sample_event.id,
            name="Línea B",
            type="interurbano",
            company="Empresa B",
        ))
        db_session.flush()
        assert db_session.execute(select(TransportLine)).scalars().all() != []

        db_session.delete(sample_event)
        db_session.flush()

        remaining = db_session.execute(select(TransportLine)).scalars().all()
        assert remaining == []
