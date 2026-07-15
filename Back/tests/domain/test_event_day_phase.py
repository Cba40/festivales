from uuid import UUID

import pytest

from src.domain.entities.event_day_phase import EventDayPhase


class TestEventDayPhaseCreation:
    def test_create_valid_phase(self) -> None:
        ed_id = UUID("00000000-0000-0000-0000-000000000001")
        op_id = UUID("00000000-0000-0000-0000-000000000002")
        edp = EventDayPhase(
            event_day_id=ed_id,
            operational_phase_id=op_id,
            start_min=480,
            end_min=720,
        )
        assert isinstance(edp.id, UUID)
        assert edp.event_day_id == ed_id
        assert edp.operational_phase_id == op_id
        assert edp.start_min == 480
        assert edp.end_min == 720

    def test_create_with_midnight_crossing(self) -> None:
        ed_id = UUID("00000000-0000-0000-0000-000000000001")
        op_id = UUID("00000000-0000-0000-0000-000000000002")
        edp = EventDayPhase(
            event_day_id=ed_id,
            operational_phase_id=op_id,
            start_min=1200,
            end_min=1740,
        )
        assert edp.start_min == 1200
        assert edp.end_min == 1740

    def test_create_with_custom_id(self) -> None:
        custom_id = UUID("12345678-1234-5678-1234-567812345678")
        ed_id = UUID("00000000-0000-0000-0000-000000000001")
        op_id = UUID("00000000-0000-0000-0000-000000000002")
        edp = EventDayPhase(
            event_day_id=ed_id,
            operational_phase_id=op_id,
            start_min=480,
            end_min=720,
            id=custom_id,
        )
        assert edp.id == custom_id

    def test_create_zero_start_min(self) -> None:
        ed_id = UUID("00000000-0000-0000-0000-000000000001")
        op_id = UUID("00000000-0000-0000-0000-000000000002")
        edp = EventDayPhase(
            event_day_id=ed_id,
            operational_phase_id=op_id,
            start_min=0,
            end_min=100,
        )
        assert edp.start_min == 0


class TestEventDayPhaseValidation:
    def test_invalid_id_type_raises_error(self) -> None:
        ed_id = UUID("00000000-0000-0000-0000-000000000001")
        op_id = UUID("00000000-0000-0000-0000-000000000002")
        with pytest.raises(TypeError, match="must be a UUID"):
            EventDayPhase(
                event_day_id=ed_id,
                operational_phase_id=op_id,
                start_min=480,
                end_min=720,
                id="not-a-uuid",  # type: ignore[arg-type]
            )

    def test_invalid_event_day_id_raises_error(self) -> None:
        op_id = UUID("00000000-0000-0000-0000-000000000002")
        with pytest.raises(TypeError, match="must be a UUID"):
            EventDayPhase(
                event_day_id="not-a-uuid",  # type: ignore[arg-type]
                operational_phase_id=op_id,
                start_min=480,
                end_min=720,
            )

    def test_invalid_operational_phase_id_raises_error(self) -> None:
        ed_id = UUID("00000000-0000-0000-0000-000000000001")
        with pytest.raises(TypeError, match="must be a UUID"):
            EventDayPhase(
                event_day_id=ed_id,
                operational_phase_id="not-a-uuid",  # type: ignore[arg-type]
                start_min=480,
                end_min=720,
            )

    def test_negative_start_min_raises_error(self) -> None:
        ed_id = UUID("00000000-0000-0000-0000-000000000001")
        op_id = UUID("00000000-0000-0000-0000-000000000002")
        with pytest.raises(ValueError, match="must be >= 0"):
            EventDayPhase(
                event_day_id=ed_id,
                operational_phase_id=op_id,
                start_min=-1,
                end_min=100,
            )

    def test_end_min_equal_to_start_min_raises_error(self) -> None:
        ed_id = UUID("00000000-0000-0000-0000-000000000001")
        op_id = UUID("00000000-0000-0000-0000-000000000002")
        with pytest.raises(ValueError, match="must be greater than"):
            EventDayPhase(
                event_day_id=ed_id,
                operational_phase_id=op_id,
                start_min=480,
                end_min=480,
            )

    def test_end_min_less_than_start_min_raises_error(self) -> None:
        ed_id = UUID("00000000-0000-0000-0000-000000000001")
        op_id = UUID("00000000-0000-0000-0000-000000000002")
        with pytest.raises(ValueError, match="must be greater than"):
            EventDayPhase(
                event_day_id=ed_id,
                operational_phase_id=op_id,
                start_min=600,
                end_min=300,
            )

    def test_start_min_as_bool_raises_error(self) -> None:
        ed_id = UUID("00000000-0000-0000-0000-000000000001")
        op_id = UUID("00000000-0000-0000-0000-000000000002")
        with pytest.raises(TypeError, match="must be an integer"):
            EventDayPhase(
                event_day_id=ed_id,
                operational_phase_id=op_id,
                start_min=True,  # type: ignore[arg-type]
                end_min=100,
            )

    def test_start_min_as_string_raises_error(self) -> None:
        ed_id = UUID("00000000-0000-0000-0000-000000000001")
        op_id = UUID("00000000-0000-0000-0000-000000000002")
        with pytest.raises(TypeError, match="must be an integer"):
            EventDayPhase(
                event_day_id=ed_id,
                operational_phase_id=op_id,
                start_min="480",  # type: ignore[arg-type]
                end_min=100,
            )

    def test_end_min_as_bool_raises_error(self) -> None:
        ed_id = UUID("00000000-0000-0000-0000-000000000001")
        op_id = UUID("00000000-0000-0000-0000-000000000002")
        with pytest.raises(TypeError, match="must be an integer"):
            EventDayPhase(
                event_day_id=ed_id,
                operational_phase_id=op_id,
                start_min=0,
                end_min=True,  # type: ignore[arg-type]
            )

    def test_end_min_as_string_raises_error(self) -> None:
        ed_id = UUID("00000000-0000-0000-0000-000000000001")
        op_id = UUID("00000000-0000-0000-0000-000000000002")
        with pytest.raises(TypeError, match="must be an integer"):
            EventDayPhase(
                event_day_id=ed_id,
                operational_phase_id=op_id,
                start_min=0,
                end_min="720",  # type: ignore[arg-type]
            )


class TestEventDayPhaseEquality:
    def test_same_id_are_equal(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        ed_id = UUID("00000000-0000-0000-0000-000000000010")
        op_id = UUID("00000000-0000-0000-0000-000000000020")
        edp1 = EventDayPhase(
            event_day_id=ed_id,
            operational_phase_id=op_id,
            start_min=480,
            end_min=720,
            id=id,
        )
        edp2 = EventDayPhase(
            event_day_id=ed_id,
            operational_phase_id=op_id,
            start_min=480,
            end_min=720,
            id=id,
        )
        assert edp1 == edp2

    def test_different_id_are_not_equal(self) -> None:
        ed_id = UUID("00000000-0000-0000-0000-000000000001")
        op_id = UUID("00000000-0000-0000-0000-000000000002")
        edp1 = EventDayPhase(
            event_day_id=ed_id,
            operational_phase_id=op_id,
            start_min=480,
            end_min=720,
        )
        edp2 = EventDayPhase(
            event_day_id=ed_id,
            operational_phase_id=op_id,
            start_min=720,
            end_min=960,
        )
        assert edp1 != edp2

    def test_equality_with_non_event_day_phase(self) -> None:
        ed_id = UUID("00000000-0000-0000-0000-000000000001")
        op_id = UUID("00000000-0000-0000-0000-000000000002")
        edp = EventDayPhase(
            event_day_id=ed_id,
            operational_phase_id=op_id,
            start_min=480,
            end_min=720,
        )
        assert (edp == "not-a-phase") is False

    def test_hash_consistency(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        ed_id = UUID("00000000-0000-0000-0000-000000000010")
        op_id = UUID("00000000-0000-0000-0000-000000000020")
        edp1 = EventDayPhase(
            event_day_id=ed_id,
            operational_phase_id=op_id,
            start_min=480,
            end_min=720,
            id=id,
        )
        edp2 = EventDayPhase(
            event_day_id=ed_id,
            operational_phase_id=op_id,
            start_min=480,
            end_min=720,
            id=id,
        )
        assert hash(edp1) == hash(edp2)

    def test_hash_set_membership(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        ed_id = UUID("00000000-0000-0000-0000-000000000010")
        op_id = UUID("00000000-0000-0000-0000-000000000020")
        edp = EventDayPhase(
            event_day_id=ed_id,
            operational_phase_id=op_id,
            start_min=480,
            end_min=720,
            id=id,
        )
        s = {edp}
        expected = EventDayPhase(
            event_day_id=ed_id,
            operational_phase_id=op_id,
            start_min=480,
            end_min=720,
            id=id,
        )
        assert expected in s


class TestEventDayPhaseImmutability:
    def test_id_is_readonly(self) -> None:
        ed_id = UUID("00000000-0000-0000-0000-000000000001")
        op_id = UUID("00000000-0000-0000-0000-000000000002")
        edp = EventDayPhase(
            event_day_id=ed_id,
            operational_phase_id=op_id,
            start_min=480,
            end_min=720,
        )
        with pytest.raises(AttributeError):
            edp.id = UUID("00000000-0000-0000-0000-000000000000")  # type: ignore[misc]

    def test_event_day_id_is_readonly(self) -> None:
        ed_id = UUID("00000000-0000-0000-0000-000000000001")
        op_id = UUID("00000000-0000-0000-0000-000000000002")
        edp = EventDayPhase(
            event_day_id=ed_id,
            operational_phase_id=op_id,
            start_min=480,
            end_min=720,
        )
        with pytest.raises(AttributeError):
            edp.event_day_id = UUID("00000000-0000-0000-0000-000000000010")  # type: ignore[misc]

    def test_operational_phase_id_is_readonly(self) -> None:
        ed_id = UUID("00000000-0000-0000-0000-000000000001")
        op_id = UUID("00000000-0000-0000-0000-000000000002")
        edp = EventDayPhase(
            event_day_id=ed_id,
            operational_phase_id=op_id,
            start_min=480,
            end_min=720,
        )
        with pytest.raises(AttributeError):
            edp.operational_phase_id = UUID("00000000-0000-0000-0000-000000000020")  # type: ignore[misc]

    def test_start_min_is_readonly(self) -> None:
        ed_id = UUID("00000000-0000-0000-0000-000000000001")
        op_id = UUID("00000000-0000-0000-0000-000000000002")
        edp = EventDayPhase(
            event_day_id=ed_id,
            operational_phase_id=op_id,
            start_min=480,
            end_min=720,
        )
        with pytest.raises(AttributeError):
            edp.start_min = 600  # type: ignore[misc]

    def test_end_min_is_readonly(self) -> None:
        ed_id = UUID("00000000-0000-0000-0000-000000000001")
        op_id = UUID("00000000-0000-0000-0000-000000000002")
        edp = EventDayPhase(
            event_day_id=ed_id,
            operational_phase_id=op_id,
            start_min=480,
            end_min=720,
        )
        with pytest.raises(AttributeError):
            edp.end_min = 960  # type: ignore[misc]


class TestEventDayPhaseRepresentation:
    def test_repr_contains_all_fields(self) -> None:
        id = UUID("12345678-1234-5678-1234-567812345678")
        ed_id = UUID("00000000-0000-0000-0000-000000000001")
        op_id = UUID("00000000-0000-0000-0000-000000000002")
        edp = EventDayPhase(
            event_day_id=ed_id,
            operational_phase_id=op_id,
            start_min=480,
            end_min=720,
            id=id,
        )
        repr_str = repr(edp)
        assert "EventDayPhase" in repr_str
        assert str(id) in repr_str
        assert "480" in repr_str
        assert "720" in repr_str
