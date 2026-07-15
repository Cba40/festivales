from uuid import UUID

import pytest

from src.domain.entities.attendance_level import AttendanceLevel


class TestAttendanceLevelCreation:
    def test_create_valid_attendance_level(self) -> None:
        al = AttendanceLevel(name="Bajo", multiplier=0.5)
        assert isinstance(al.id, UUID)
        assert al.name == "Bajo"
        assert al.multiplier == 0.5

    def test_create_with_custom_id(self) -> None:
        custom_id = UUID("12345678-1234-5678-1234-567812345678")
        al = AttendanceLevel(name="Alto", multiplier=1.5, id=custom_id)
        assert al.id == custom_id
        assert al.name == "Alto"
        assert al.multiplier == 1.5

    def test_create_strips_whitespace(self) -> None:
        al = AttendanceLevel(name="  Medio  ", multiplier=1.0)
        assert al.name == "Medio"

    def test_create_minimal_name(self) -> None:
        al = AttendanceLevel(name="A", multiplier=0.1)
        assert al.name == "A"

    def test_create_with_int_multiplier(self) -> None:
        al = AttendanceLevel(name="Test", multiplier=1)
        assert al.multiplier == 1

    def test_create_minimum_multiplier(self) -> None:
        al = AttendanceLevel(name="Mínimo", multiplier=0.1)
        assert al.multiplier == 0.1

    def test_create_maximum_multiplier(self) -> None:
        al = AttendanceLevel(name="Máximo", multiplier=2.0)
        assert al.multiplier == 2.0


class TestAttendanceLevelValidation:
    def test_empty_name_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            AttendanceLevel(name="", multiplier=1.0)

    def test_blank_name_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            AttendanceLevel(name="   ", multiplier=1.0)

    def test_name_exceeds_max_length_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must not exceed 50 characters"):
            AttendanceLevel(name="A" * 51, multiplier=1.0)

    def test_name_at_max_length_is_valid(self) -> None:
        name = "A" * 50
        al = AttendanceLevel(name=name, multiplier=1.0)
        assert al.name == name

    def test_invalid_id_type_raises_error(self) -> None:
        with pytest.raises(TypeError, match="must be a UUID"):
            AttendanceLevel(name="Test", multiplier=1.0, id="not-a-uuid")  # type: ignore[arg-type]

    def test_multiplier_below_minimum_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must be between 0.1 and 2.0"):
            AttendanceLevel(name="Test", multiplier=0.09)

    def test_multiplier_above_maximum_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must be between 0.1 and 2.0"):
            AttendanceLevel(name="Test", multiplier=2.1)

    def test_multiplier_as_bool_raises_error(self) -> None:
        with pytest.raises(TypeError, match="must be a number"):
            AttendanceLevel(name="Test", multiplier=True)  # type: ignore[arg-type]

    def test_multiplier_as_string_raises_error(self) -> None:
        with pytest.raises(TypeError, match="must be a number"):
            AttendanceLevel(name="Test", multiplier="1.0")  # type: ignore[arg-type]


class TestAttendanceLevelEquality:
    def test_same_id_are_equal(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        al1 = AttendanceLevel(name="Bajo", multiplier=0.5, id=id)
        al2 = AttendanceLevel(name="Bajo", multiplier=0.5, id=id)
        assert al1 == al2

    def test_different_id_are_not_equal(self) -> None:
        al1 = AttendanceLevel(name="Bajo", multiplier=0.5)
        al2 = AttendanceLevel(name="Alto", multiplier=1.5)
        assert al1 != al2

    def test_equality_with_non_attendance_level(self) -> None:
        al = AttendanceLevel(name="Bajo", multiplier=0.5)
        assert (al == "not-a-level") is False

    def test_hash_consistency(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        al1 = AttendanceLevel(name="Bajo", multiplier=0.5, id=id)
        al2 = AttendanceLevel(name="Bajo", multiplier=0.5, id=id)
        assert hash(al1) == hash(al2)

    def test_hash_set_membership(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        al = AttendanceLevel(name="Bajo", multiplier=0.5, id=id)
        s = {al}
        assert AttendanceLevel(name="Bajo", multiplier=0.5, id=id) in s


class TestAttendanceLevelImmutability:
    def test_id_is_readonly(self) -> None:
        al = AttendanceLevel(name="Test", multiplier=1.0)
        with pytest.raises(AttributeError):
            al.id = UUID("00000000-0000-0000-0000-000000000000")  # type: ignore[misc]

    def test_name_is_readonly(self) -> None:
        al = AttendanceLevel(name="Test", multiplier=1.0)
        with pytest.raises(AttributeError):
            al.name = "NewName"  # type: ignore[misc]

    def test_multiplier_is_readonly(self) -> None:
        al = AttendanceLevel(name="Test", multiplier=1.0)
        with pytest.raises(AttributeError):
            al.multiplier = 2.0  # type: ignore[misc]


class TestAttendanceLevelRepresentation:
    def test_repr_contains_all_fields(self) -> None:
        id = UUID("12345678-1234-5678-1234-567812345678")
        al = AttendanceLevel(name="Medio", multiplier=1.0, id=id)
        repr_str = repr(al)
        assert "AttendanceLevel" in repr_str
        assert str(id) in repr_str
        assert "Medio" in repr_str
        assert "1.0" in repr_str
