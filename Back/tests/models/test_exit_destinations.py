# backend/tests/models/test_exit_destinations.py
# PARTE 1 (S1 - Salir V1): tabla exit_destinations.

import pytest
from sqlalchemy import UniqueConstraint, select
from sqlalchemy.exc import IntegrityError

from app.db.session import Base
from app.models.event import Event
from app.models.exit_destination import ExitDestination


class TestExitDestinationSchema:
    """Estructura del modelo: tabla, columnas, constraints."""

    def test_table_name(self) -> None:
        assert ExitDestination.__tablename__ == "exit_destinations"

    def test_inherits_base(self) -> None:
        assert issubclass(ExitDestination, Base)

    def test_registered_in_base_metadata(self) -> None:
        assert "exit_destinations" in Base.metadata.tables

    def test_id_is_primary_key_string36(self) -> None:
        col = ExitDestination.__table__.columns["id"]
        assert col.primary_key
        assert col.type.length == 36

    def test_event_id_fk_to_events_with_cascade(self) -> None:
        col = ExitDestination.__table__.columns["event_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert fks[0].target_fullname == "events.id"
        assert fks[0].ondelete == "CASCADE"

    def test_name_is_required_string100(self) -> None:
        col = ExitDestination.__table__.columns["name"]
        assert col.nullable is False
        assert col.type.length == 100

    def test_active_is_required_boolean(self) -> None:
        col = ExitDestination.__table__.columns["active"]
        assert col.nullable is False
        assert col.default is not None

    def test_has_timestamps(self) -> None:
        for name in ("created_at", "updated_at"):
            col = ExitDestination.__table__.columns[name]
            assert col.server_default is not None
            assert col.type.timezone is True

    def test_unique_constraint_event_name(self) -> None:
        uqs = [
            c for c in ExitDestination.__table__.constraints
            if isinstance(c, UniqueConstraint)
        ]
        matching = [
            u for u in uqs
            if {c.name for c in u.columns} == {"event_id", "name"}
        ]
        assert len(matching) == 1
        assert matching[0].name == "uq_exit_destinations_event_name"


class TestExitDestinationPersistence:
    """Comportamiento real contra Postgres (fixtures de conftest)."""

    def test_create_with_defaults(self, db_session, sample_event) -> None:
        dest = ExitDestination(event_id=sample_event.id, name="Córdoba")
        db_session.add(dest)
        db_session.flush()

        assert dest.id is not None
        assert len(dest.id) == 36
        assert dest.active is True
        assert dest.created_at is not None
        assert dest.updated_at is not None

    def test_duplicate_name_same_event_rejected(self, db_session, sample_event) -> None:
        db_session.add(ExitDestination(event_id=sample_event.id, name="Córdoba"))
        db_session.flush()

        db_session.add(ExitDestination(event_id=sample_event.id, name="Córdoba"))
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_same_name_across_different_events_allowed(self, db_session, sample_event) -> None:
        other = Event(id="test-event-exit-2", name="Otro Evento")
        db_session.add(other)
        db_session.flush()

        db_session.add(ExitDestination(event_id=sample_event.id, name="Córdoba"))
        db_session.add(ExitDestination(event_id=other.id, name="Córdoba"))
        db_session.flush()

        all_dests = db_session.execute(select(ExitDestination)).scalars().all()
        assert len(all_dests) == 2

    def test_cascade_delete_with_event(self, db_session, sample_event) -> None:
        db_session.add(ExitDestination(event_id=sample_event.id, name="Sierras Chicas"))
        db_session.add(ExitDestination(event_id=sample_event.id, name="Sinsacate"))
        db_session.flush()
        assert db_session.execute(select(ExitDestination)).scalars().all() != []

        db_session.delete(sample_event)
        db_session.flush()

        remaining = db_session.execute(select(ExitDestination)).scalars().all()
        assert remaining == []
