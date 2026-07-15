from uuid import UUID

import pytest

from src.domain.entities.zone_type import ZoneType


class TestZoneTypeCreation:
    def test_create_valid_zone_type(self) -> None:
        zt = ZoneType(name="Parking")
        assert isinstance(zt.id, UUID)
        assert zt.name == "Parking"

    def test_create_with_custom_id(self) -> None:
        custom_id = UUID("12345678-1234-5678-1234-567812345678")
        zt = ZoneType(name="Gastronomy", id=custom_id)
        assert zt.id == custom_id
        assert zt.name == "Gastronomy"

    def test_create_strips_whitespace(self) -> None:
        zt = ZoneType(name="  Sanitary  ")
        assert zt.name == "Sanitary"

    def test_create_minimal_name(self) -> None:
        zt = ZoneType(name="A")
        assert zt.name == "A"


class TestZoneTypeValidation:
    def test_empty_name_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            ZoneType(name="")

    def test_blank_name_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            ZoneType(name="   ")

    def test_name_exceeds_max_length_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must not exceed 50 characters"):
            ZoneType(name="A" * 51)

    def test_name_at_max_length_is_valid(self) -> None:
        name = "A" * 50
        zt = ZoneType(name=name)
        assert zt.name == name

    def test_invalid_id_type_raises_error(self) -> None:
        with pytest.raises(TypeError, match="must be a UUID"):
            ZoneType(name="Test", id="not-a-uuid")  # type: ignore[arg-type]


class TestZoneTypeEquality:
    def test_same_id_are_equal(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        zt1 = ZoneType(name="Parking", id=id)
        zt2 = ZoneType(name="Parking", id=id)
        assert zt1 == zt2

    def test_different_id_are_not_equal(self) -> None:
        zt1 = ZoneType(name="Parking")
        zt2 = ZoneType(name="Gastronomy")
        assert zt1 != zt2

    def test_equality_with_non_zone_type(self) -> None:
        zt = ZoneType(name="Parking")
        assert (zt == "not-a-zone-type") is False

    def test_hash_consistency(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        zt1 = ZoneType(name="Parking", id=id)
        zt2 = ZoneType(name="Parking", id=id)
        assert hash(zt1) == hash(zt2)

    def test_hash_set_membership(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        zt = ZoneType(name="Parking", id=id)
        s = {zt}
        assert ZoneType(name="Parking", id=id) in s


class TestZoneTypeImmutability:
    def test_id_is_readonly(self) -> None:
        zt = ZoneType(name="Parking")
        with pytest.raises(AttributeError):
            zt.id = UUID("00000000-0000-0000-0000-000000000000")  # type: ignore[misc]

    def test_name_is_readonly(self) -> None:
        zt = ZoneType(name="Parking")
        with pytest.raises(AttributeError):
            zt.name = "NewName"  # type: ignore[misc]


class TestZoneTypeRepresentation:
    def test_repr_contains_id_and_name(self) -> None:
        id = UUID("12345678-1234-5678-1234-567812345678")
        zt = ZoneType(name="Transport", id=id)
        repr_str = repr(zt)
        assert "ZoneType" in repr_str
        assert str(id) in repr_str
        assert "Transport" in repr_str
