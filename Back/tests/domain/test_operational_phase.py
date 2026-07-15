from uuid import UUID

import pytest

from src.domain.entities.operational_phase import OperationalPhase


class TestOperationalPhaseCreation:
    def test_create_valid_phase(self) -> None:
        phase = OperationalPhase(name="Apertura", sequence_order=1)
        assert isinstance(phase.id, UUID)
        assert phase.name == "Apertura"
        assert phase.sequence_order == 1

    def test_create_with_custom_id(self) -> None:
        custom_id = UUID("12345678-1234-5678-1234-567812345678")
        phase = OperationalPhase(name="Pico", sequence_order=2, id=custom_id)
        assert phase.id == custom_id
        assert phase.name == "Pico"
        assert phase.sequence_order == 2

    def test_create_strips_whitespace(self) -> None:
        phase = OperationalPhase(name="  Cierre  ", sequence_order=3)
        assert phase.name == "Cierre"

    def test_create_minimal_name(self) -> None:
        phase = OperationalPhase(name="A", sequence_order=1)
        assert phase.name == "A"

    def test_create_minimum_sequence_order(self) -> None:
        phase = OperationalPhase(name="First", sequence_order=1)
        assert phase.sequence_order == 1

    def test_create_large_sequence_order(self) -> None:
        phase = OperationalPhase(name="Late", sequence_order=999)
        assert phase.sequence_order == 999


class TestOperationalPhaseValidation:
    def test_empty_name_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            OperationalPhase(name="", sequence_order=1)

    def test_blank_name_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            OperationalPhase(name="   ", sequence_order=1)

    def test_name_exceeds_max_length_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must not exceed 50 characters"):
            OperationalPhase(name="A" * 51, sequence_order=1)

    def test_name_at_max_length_is_valid(self) -> None:
        name = "A" * 50
        phase = OperationalPhase(name=name, sequence_order=1)
        assert phase.name == name

    def test_invalid_id_type_raises_error(self) -> None:
        with pytest.raises(TypeError, match="must be a UUID"):
            OperationalPhase(name="Test", sequence_order=1, id="not-a-uuid")  # type: ignore[arg-type]

    def test_zero_sequence_order_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must be a positive integer"):
            OperationalPhase(name="Test", sequence_order=0)

    def test_negative_sequence_order_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must be a positive integer"):
            OperationalPhase(name="Test", sequence_order=-1)

    def test_float_sequence_order_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must be a positive integer"):
            OperationalPhase(name="Test", sequence_order=1.5)  # type: ignore[arg-type]

    def test_bool_sequence_order_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must be a positive integer"):
            OperationalPhase(name="Test", sequence_order=True)  # type: ignore[arg-type]

    def test_string_sequence_order_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must be a positive integer"):
            OperationalPhase(name="Test", sequence_order="1")  # type: ignore[arg-type]


class TestOperationalPhaseEquality:
    def test_same_id_are_equal(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        phase1 = OperationalPhase(name="Apertura", sequence_order=1, id=id)
        phase2 = OperationalPhase(name="Apertura", sequence_order=1, id=id)
        assert phase1 == phase2

    def test_different_id_are_not_equal(self) -> None:
        phase1 = OperationalPhase(name="Phase A", sequence_order=1)
        phase2 = OperationalPhase(name="Phase B", sequence_order=2)
        assert phase1 != phase2

    def test_equality_with_non_operational_phase(self) -> None:
        phase = OperationalPhase(name="Test", sequence_order=1)
        assert (phase == "not-a-phase") is False

    def test_hash_consistency(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        phase1 = OperationalPhase(name="Test", sequence_order=1, id=id)
        phase2 = OperationalPhase(name="Test", sequence_order=1, id=id)
        assert hash(phase1) == hash(phase2)

    def test_hash_set_membership(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        phase = OperationalPhase(name="Test", sequence_order=1, id=id)
        s = {phase}
        assert OperationalPhase(name="Test", sequence_order=1, id=id) in s


class TestOperationalPhaseImmutability:
    def test_id_is_readonly(self) -> None:
        phase = OperationalPhase(name="Test", sequence_order=1)
        with pytest.raises(AttributeError):
            phase.id = UUID("00000000-0000-0000-0000-000000000000")  # type: ignore[misc]

    def test_name_is_readonly(self) -> None:
        phase = OperationalPhase(name="Test", sequence_order=1)
        with pytest.raises(AttributeError):
            phase.name = "NewName"  # type: ignore[misc]

    def test_sequence_order_is_readonly(self) -> None:
        phase = OperationalPhase(name="Test", sequence_order=1)
        with pytest.raises(AttributeError):
            phase.sequence_order = 2  # type: ignore[misc]


class TestOperationalPhaseRepresentation:
    def test_repr_contains_all_fields(self) -> None:
        id = UUID("12345678-1234-5678-1234-567812345678")
        phase = OperationalPhase(name="Pico Operativo", sequence_order=2, id=id)
        repr_str = repr(phase)
        assert "OperationalPhase" in repr_str
        assert str(id) in repr_str
        assert "Pico Operativo" in repr_str
        assert "2" in repr_str
