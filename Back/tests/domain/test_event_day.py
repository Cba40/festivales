from datetime import date
from uuid import UUID

import pytest

from src.domain.entities.event_day import EventDay


class TestEventDayCreation:
    def test_create_valid_event_day(self) -> None:
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        ed = EventDay(
            event_date=d,
            operational_profile_id=op_id,
            attendance_level_id=al_id,
            operational_start_min=480,
            operational_end_min=1320,
        )
        assert isinstance(ed.id, UUID)
        assert ed.event_date == d
        assert ed.operational_profile_id == op_id
        assert ed.attendance_level_id == al_id
        assert ed.operational_start_min == 480
        assert ed.operational_end_min == 1320

    def test_create_with_midnight_crossing(self) -> None:
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        ed = EventDay(
            event_date=d,
            operational_profile_id=op_id,
            attendance_level_id=al_id,
            operational_start_min=1200,
            operational_end_min=1740,
        )
        assert ed.operational_end_min == 1740

    def test_create_with_custom_id(self) -> None:
        custom_id = UUID("12345678-1234-5678-1234-567812345678")
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        ed = EventDay(
            event_date=d,
            operational_profile_id=op_id,
            attendance_level_id=al_id,
            operational_start_min=480,
            operational_end_min=1320,
            id=custom_id,
        )
        assert ed.id == custom_id

    def test_create_zero_start_min(self) -> None:
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        ed = EventDay(
            event_date=d,
            operational_profile_id=op_id,
            attendance_level_id=al_id,
            operational_start_min=0,
            operational_end_min=100,
        )
        assert ed.operational_start_min == 0

    def test_create_non_zero_start_min(self) -> None:
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        ed = EventDay(
            event_date=d,
            operational_profile_id=op_id,
            attendance_level_id=al_id,
            operational_start_min=600,
            operational_end_min=1200,
        )
        assert ed.operational_start_min == 600


class TestEventDayValidation:
    def test_invalid_id_type_raises_error(self) -> None:
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        with pytest.raises(TypeError, match="must be a UUID"):
            EventDay(
                event_date=d,
                operational_profile_id=op_id,
                attendance_level_id=al_id,
                operational_start_min=480,
                operational_end_min=1320,
                id="not-a-uuid",  # type: ignore[arg-type]
            )

    def test_invalid_event_date_type_raises_error(self) -> None:
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        with pytest.raises(TypeError, match="must be a date"):
            EventDay(
                event_date="2026-07-15",  # type: ignore[arg-type]
                operational_profile_id=op_id,
                attendance_level_id=al_id,
                operational_start_min=480,
                operational_end_min=1320,
            )

    def test_invalid_operational_profile_id_raises_error(self) -> None:
        d = date(2026, 7, 15)
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        with pytest.raises(TypeError, match="must be a UUID"):
            EventDay(
                event_date=d,
                operational_profile_id="not-a-uuid",  # type: ignore[arg-type]
                attendance_level_id=al_id,
                operational_start_min=480,
                operational_end_min=1320,
            )

    def test_invalid_attendance_level_id_raises_error(self) -> None:
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        with pytest.raises(TypeError, match="must be a UUID"):
            EventDay(
                event_date=d,
                operational_profile_id=op_id,
                attendance_level_id="not-a-uuid",  # type: ignore[arg-type]
                operational_start_min=480,
                operational_end_min=1320,
            )

    def test_negative_start_min_raises_error(self) -> None:
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        with pytest.raises(ValueError, match="must be >= 0"):
            EventDay(
                event_date=d,
                operational_profile_id=op_id,
                attendance_level_id=al_id,
                operational_start_min=-1,
                operational_end_min=100,
            )

    def test_end_min_equal_to_start_min_raises_error(self) -> None:
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        with pytest.raises(ValueError, match="must be greater than"):
            EventDay(
                event_date=d,
                operational_profile_id=op_id,
                attendance_level_id=al_id,
                operational_start_min=480,
                operational_end_min=480,
            )

    def test_end_min_less_than_start_min_raises_error(self) -> None:
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        with pytest.raises(ValueError, match="must be greater than"):
            EventDay(
                event_date=d,
                operational_profile_id=op_id,
                attendance_level_id=al_id,
                operational_start_min=600,
                operational_end_min=300,
            )

    def test_start_min_as_bool_raises_error(self) -> None:
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        with pytest.raises(TypeError, match="must be an integer"):
            EventDay(
                event_date=d,
                operational_profile_id=op_id,
                attendance_level_id=al_id,
                operational_start_min=True,  # type: ignore[arg-type]
                operational_end_min=100,
            )

    def test_start_min_as_string_raises_error(self) -> None:
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        with pytest.raises(TypeError, match="must be an integer"):
            EventDay(
                event_date=d,
                operational_profile_id=op_id,
                attendance_level_id=al_id,
                operational_start_min="480",  # type: ignore[arg-type]
                operational_end_min=100,
            )

    def test_end_min_as_bool_raises_error(self) -> None:
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        with pytest.raises(TypeError, match="must be an integer"):
            EventDay(
                event_date=d,
                operational_profile_id=op_id,
                attendance_level_id=al_id,
                operational_start_min=0,
                operational_end_min=True,  # type: ignore[arg-type]
            )


class TestEventDayEquality:
    def test_same_id_are_equal(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000010")
        al_id = UUID("00000000-0000-0000-0000-000000000020")
        ed1 = EventDay(
            event_date=d,
            operational_profile_id=op_id,
            attendance_level_id=al_id,
            operational_start_min=480,
            operational_end_min=1320,
            id=id,
        )
        ed2 = EventDay(
            event_date=d,
            operational_profile_id=op_id,
            attendance_level_id=al_id,
            operational_start_min=480,
            operational_end_min=1320,
            id=id,
        )
        assert ed1 == ed2

    def test_different_id_are_not_equal(self) -> None:
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        ed1 = EventDay(
            event_date=d,
            operational_profile_id=op_id,
            attendance_level_id=al_id,
            operational_start_min=480,
            operational_end_min=1320,
        )
        ed2 = EventDay(
            event_date=d,
            operational_profile_id=op_id,
            attendance_level_id=al_id,
            operational_start_min=480,
            operational_end_min=1320,
        )
        assert ed1 != ed2

    def test_equality_with_non_event_day(self) -> None:
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        ed = EventDay(
            event_date=d,
            operational_profile_id=op_id,
            attendance_level_id=al_id,
            operational_start_min=480,
            operational_end_min=1320,
        )
        assert (ed == "not-an-event-day") is False

    def test_hash_consistency(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000010")
        al_id = UUID("00000000-0000-0000-0000-000000000020")
        ed1 = EventDay(
            event_date=d,
            operational_profile_id=op_id,
            attendance_level_id=al_id,
            operational_start_min=480,
            operational_end_min=1320,
            id=id,
        )
        ed2 = EventDay(
            event_date=d,
            operational_profile_id=op_id,
            attendance_level_id=al_id,
            operational_start_min=480,
            operational_end_min=1320,
            id=id,
        )
        assert hash(ed1) == hash(ed2)

    def test_hash_set_membership(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000010")
        al_id = UUID("00000000-0000-0000-0000-000000000020")
        ed = EventDay(
            event_date=d,
            operational_profile_id=op_id,
            attendance_level_id=al_id,
            operational_start_min=480,
            operational_end_min=1320,
            id=id,
        )
        s = {ed}
        expected = EventDay(
            event_date=d,
            operational_profile_id=op_id,
            attendance_level_id=al_id,
            operational_start_min=480,
            operational_end_min=1320,
            id=id,
        )
        assert expected in s


class TestEventDayImmutability:
    def test_id_is_readonly(self) -> None:
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        ed = EventDay(
            event_date=d,
            operational_profile_id=op_id,
            attendance_level_id=al_id,
            operational_start_min=480,
            operational_end_min=1320,
        )
        with pytest.raises(AttributeError):
            ed.id = UUID("00000000-0000-0000-0000-000000000000")  # type: ignore[misc]

    def test_event_date_is_readonly(self) -> None:
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        ed = EventDay(
            event_date=d,
            operational_profile_id=op_id,
            attendance_level_id=al_id,
            operational_start_min=480,
            operational_end_min=1320,
        )
        with pytest.raises(AttributeError):
            ed.event_date = date(2026, 7, 16)  # type: ignore[misc]

    def test_operational_profile_id_is_readonly(self) -> None:
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        ed = EventDay(
            event_date=d,
            operational_profile_id=op_id,
            attendance_level_id=al_id,
            operational_start_min=480,
            operational_end_min=1320,
        )
        with pytest.raises(AttributeError):
            ed.operational_profile_id = UUID("00000000-0000-0000-0000-000000000010")  # type: ignore[misc]

    def test_attendance_level_id_is_readonly(self) -> None:
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        ed = EventDay(
            event_date=d,
            operational_profile_id=op_id,
            attendance_level_id=al_id,
            operational_start_min=480,
            operational_end_min=1320,
        )
        with pytest.raises(AttributeError):
            ed.attendance_level_id = UUID("00000000-0000-0000-0000-000000000020")  # type: ignore[misc]

    def test_operational_start_min_is_readonly(self) -> None:
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        ed = EventDay(
            event_date=d,
            operational_profile_id=op_id,
            attendance_level_id=al_id,
            operational_start_min=480,
            operational_end_min=1320,
        )
        with pytest.raises(AttributeError):
            ed.operational_start_min = 600  # type: ignore[misc]

    def test_operational_end_min_is_readonly(self) -> None:
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        ed = EventDay(
            event_date=d,
            operational_profile_id=op_id,
            attendance_level_id=al_id,
            operational_start_min=480,
            operational_end_min=1320,
        )
        with pytest.raises(AttributeError):
            ed.operational_end_min = 1400  # type: ignore[misc]


class TestEventDayRepresentation:
    def test_repr_contains_all_fields(self) -> None:
        id = UUID("12345678-1234-5678-1234-567812345678")
        d = date(2026, 7, 15)
        op_id = UUID("00000000-0000-0000-0000-000000000001")
        al_id = UUID("00000000-0000-0000-0000-000000000002")
        ed = EventDay(
            event_date=d,
            operational_profile_id=op_id,
            attendance_level_id=al_id,
            operational_start_min=480,
            operational_end_min=1320,
            id=id,
        )
        repr_str = repr(ed)
        assert "EventDay" in repr_str
        assert str(id) in repr_str
        assert repr(d) in repr_str
        assert "480" in repr_str
        assert "1320" in repr_str
