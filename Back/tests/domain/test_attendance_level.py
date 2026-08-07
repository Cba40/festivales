from uuid import UUID

import pytest

from src.domain.entities.attendance_level import AttendanceLevel


class TestAttendanceLevelCreation:
    def test_create_valid_attendance_level(self) -> None:
        al = AttendanceLevel(name="Bajo", min_people=5000, max_people=10000)
        assert isinstance(al.id, UUID)
        assert al.name == "Bajo"
        assert al.min_people == 5000
        assert al.max_people == 10000

    def test_create_with_custom_id(self) -> None:
        custom_id = UUID("12345678-1234-5678-1234-567812345678")
        al = AttendanceLevel(name="Alto", min_people=25000, max_people=45000, id=custom_id)
        assert al.id == custom_id
        assert al.name == "Alto"
        assert al.min_people == 25000
        assert al.max_people == 45000

    def test_create_without_max_people(self) -> None:
        al = AttendanceLevel(name="Muy Alto", min_people=45000)
        assert al.min_people == 45000
        assert al.max_people is None

    def test_create_strips_whitespace(self) -> None:
        al = AttendanceLevel(name="  Medio  ", min_people=10000, max_people=25000)
        assert al.name == "Medio"

    def test_create_minimal_name(self) -> None:
        al = AttendanceLevel(name="A", min_people=0, max_people=1000)
        assert al.name == "A"


class TestAttendanceLevelValidation:
    def test_empty_name_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            AttendanceLevel(name="", min_people=0, max_people=1000)

    def test_blank_name_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            AttendanceLevel(name="   ", min_people=0, max_people=1000)

    def test_name_exceeds_max_length_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must not exceed 50 characters"):
            AttendanceLevel(name="A" * 51, min_people=0, max_people=1000)

    def test_name_at_max_length_is_valid(self) -> None:
        name = "A" * 50
        al = AttendanceLevel(name=name, min_people=0, max_people=1000)
        assert al.name == name

    def test_invalid_id_type_raises_error(self) -> None:
        with pytest.raises(TypeError, match="must be a UUID"):
            AttendanceLevel(name="Test", min_people=0, max_people=1000, id="not-a-uuid")  # type: ignore[arg-type]

    def test_min_people_negative_raises_error(self) -> None:
        with pytest.raises(ValueError, match="min_people must be >= 0"):
            AttendanceLevel(name="Test", min_people=-1, max_people=1000)

    def test_min_people_bool_raises_error(self) -> None:
        with pytest.raises(TypeError, match="min_people must be an integer"):
            AttendanceLevel(name="Test", min_people=True, max_people=1000)  # type: ignore[arg-type]

    def test_min_people_string_raises_error(self) -> None:
        with pytest.raises(TypeError, match="min_people must be an integer"):
            AttendanceLevel(name="Test", min_people="1", max_people=1000)  # type: ignore[arg-type]

    def test_max_people_not_greater_than_min_raises_error(self) -> None:
        with pytest.raises(ValueError, match="max_people must be greater than min_people"):
            AttendanceLevel(name="Test", min_people=1000, max_people=1000)

    def test_max_people_lower_than_min_raises_error(self) -> None:
        with pytest.raises(ValueError, match="max_people must be greater than min_people"):
            AttendanceLevel(name="Test", min_people=1000, max_people=500)


class TestAttendanceLevelEquality:
    def test_same_id_are_equal(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        al1 = AttendanceLevel(name="Bajo", min_people=0, max_people=5000, id=id)
        al2 = AttendanceLevel(name="Bajo", min_people=0, max_people=5000, id=id)
        assert al1 == al2

    def test_different_id_are_not_equal(self) -> None:
        al1 = AttendanceLevel(name="Bajo", min_people=0, max_people=5000)
        al2 = AttendanceLevel(name="Alto", min_people=25000, max_people=45000)
        assert al1 != al2

    def test_equality_with_non_attendance_level(self) -> None:
        al = AttendanceLevel(name="Bajo", min_people=0, max_people=5000)
        assert (al == "not-a-level") is False

    def test_hash_consistency(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        al1 = AttendanceLevel(name="Bajo", min_people=0, max_people=5000, id=id)
        al2 = AttendanceLevel(name="Bajo", min_people=0, max_people=5000, id=id)
        assert hash(al1) == hash(al2)

    def test_hash_set_membership(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        al = AttendanceLevel(name="Bajo", min_people=0, max_people=5000, id=id)
        s = {al}
        assert AttendanceLevel(name="Bajo", min_people=0, max_people=5000, id=id) in s


class TestAttendanceLevelImmutability:
    def test_id_is_readonly(self) -> None:
        al = AttendanceLevel(name="Test", min_people=0, max_people=5000)
        with pytest.raises(AttributeError):
            al.id = UUID("00000000-0000-0000-0000-000000000000")  # type: ignore[misc]

    def test_name_is_readonly(self) -> None:
        al = AttendanceLevel(name="Test", min_people=0, max_people=5000)
        with pytest.raises(AttributeError):
            al.name = "NewName"  # type: ignore[misc]

    def test_min_people_is_readonly(self) -> None:
        al = AttendanceLevel(name="Test", min_people=0, max_people=5000)
        with pytest.raises(AttributeError):
            al.min_people = 5000  # type: ignore[misc]


class TestAttendanceLevelRepresentation:
    def test_repr_contains_all_fields(self) -> None:
        id = UUID("12345678-1234-5678-1234-567812345678")
        al = AttendanceLevel(name="Medio", min_people=10000, max_people=25000, id=id)
        repr_str = repr(al)
        assert "AttendanceLevel" in repr_str
        assert str(id) in repr_str
        assert "Medio" in repr_str
        assert "10000" in repr_str
        assert "25000" in repr_str