from __future__ import annotations

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy import Enum as SAEnum

from src.infrastructure.db.base import Base
from src.infrastructure.persistence.models import (
    AttendanceLevelModel,
    EventDayModel,
    EventDayPhaseModel,
    OperationalEventModel,
    OperationalPhaseModel,
    OperationalProfileModel,
    ZoneBehaviorModel,
    ZoneModel,
    ZoneTypeModel,
)


class TestZoneTypeModel:
    def test_table_name(self) -> None:
        assert ZoneTypeModel.__tablename__ == "zone_types"

    def test_has_id_column(self) -> None:
        assert "id" in ZoneTypeModel.__table__.columns
        assert ZoneTypeModel.__table__.columns["id"].primary_key

    def test_has_name_column(self) -> None:
        assert "name" in ZoneTypeModel.__table__.columns

    def test_has_timestamps(self) -> None:
        assert "created_at" in ZoneTypeModel.__table__.columns
        assert "updated_at" in ZoneTypeModel.__table__.columns

    def test_inherits_base(self) -> None:
        assert issubclass(ZoneTypeModel, Base)


class TestZoneModel:
    def test_table_name(self) -> None:
        assert ZoneModel.__tablename__ == "zones"

    def test_has_capacity_column(self) -> None:
        assert "capacity" in ZoneModel.__table__.columns

    def test_has_zone_type_fk(self) -> None:
        col = ZoneModel.__table__.columns["zone_type_id"]
        assert len(col.foreign_keys) > 0

    def test_inherits_base(self) -> None:
        assert issubclass(ZoneModel, Base)


class TestAttendanceLevelModel:
    def test_table_name(self) -> None:
        assert AttendanceLevelModel.__tablename__ == "attendance_levels"

    def test_has_multiplier_column(self) -> None:
        assert "multiplier" in AttendanceLevelModel.__table__.columns

    def test_inherits_base(self) -> None:
        assert issubclass(AttendanceLevelModel, Base)


class TestOperationalProfileModel:
    def test_table_name(self) -> None:
        assert OperationalProfileModel.__tablename__ == "operational_profiles"

    def test_inherits_base(self) -> None:
        assert issubclass(OperationalProfileModel, Base)


class TestOperationalPhaseModel:
    def test_table_name(self) -> None:
        assert OperationalPhaseModel.__tablename__ == "operational_phases"

    def test_has_unique_constraint(self) -> None:
        uq = [
            c for c in OperationalPhaseModel.__table__.constraints
            if isinstance(c, UniqueConstraint)
        ]
        cols = {col.name for c in uq for col in c.columns}
        assert "operational_profile_id" in cols
        assert "sequence_order" in cols

    def test_has_profile_fk(self) -> None:
        col = OperationalPhaseModel.__table__.columns["operational_profile_id"]
        assert len(col.foreign_keys) > 0

    def test_inherits_base(self) -> None:
        assert issubclass(OperationalPhaseModel, Base)


class TestZoneBehaviorModel:
    def test_table_name(self) -> None:
        assert ZoneBehaviorModel.__tablename__ == "zone_behaviors"

    def test_has_flow_restriction_column(self) -> None:
        col = ZoneBehaviorModel.__table__.columns["flow_restriction"]
        assert isinstance(col.type, SAEnum)

    def test_has_density_factor_column(self) -> None:
        assert "density_factor" in ZoneBehaviorModel.__table__.columns

    def test_has_unique_constraint(self) -> None:
        uq = [
            c for c in ZoneBehaviorModel.__table__.constraints
            if isinstance(c, UniqueConstraint)
        ]
        cols = {col.name for c in uq for col in c.columns}
        assert "operational_phase_id" in cols
        assert "zone_type_id" in cols

    def test_inherits_base(self) -> None:
        assert issubclass(ZoneBehaviorModel, Base)


class TestEventDayModel:
    def test_table_name(self) -> None:
        assert EventDayModel.__tablename__ == "event_days"

    def test_has_date_column(self) -> None:
        assert "event_date" in EventDayModel.__table__.columns

    def test_has_profile_fk(self) -> None:
        col = EventDayModel.__table__.columns["operational_profile_id"]
        assert len(col.foreign_keys) > 0

    def test_has_attendance_fk(self) -> None:
        col = EventDayModel.__table__.columns["attendance_level_id"]
        assert len(col.foreign_keys) > 0

    def test_inherits_base(self) -> None:
        assert issubclass(EventDayModel, Base)


class TestEventDayPhaseModel:
    def test_table_name(self) -> None:
        assert EventDayPhaseModel.__tablename__ == "event_day_phases"

    def test_has_event_day_fk(self) -> None:
        col = EventDayPhaseModel.__table__.columns["event_day_id"]
        assert len(col.foreign_keys) > 0

    def test_has_phase_fk(self) -> None:
        col = EventDayPhaseModel.__table__.columns["operational_phase_id"]
        assert len(col.foreign_keys) > 0

    def test_inherits_base(self) -> None:
        assert issubclass(EventDayPhaseModel, Base)


class TestOperationalEventModel:
    def test_table_name(self) -> None:
        assert OperationalEventModel.__tablename__ == "operational_events"

    def test_has_impact_column(self) -> None:
        assert "impact_value" in OperationalEventModel.__table__.columns

    def test_has_is_incident_column(self) -> None:
        assert "is_incident" in OperationalEventModel.__table__.columns

    def test_has_timestamps(self) -> None:
        assert "start_timestamp" in OperationalEventModel.__table__.columns
        assert "end_timestamp" in OperationalEventModel.__table__.columns

    def test_inherits_base(self) -> None:
        assert issubclass(OperationalEventModel, Base)
