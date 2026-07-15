from uuid import UUID

import pytest

from src.domain.entities.zone import Zone


class TestZoneCreation:
    def test_create_valid_zone(self) -> None:
        zone = Zone(name="Main Stage", zone_type_id=UUID("00000000-0000-0000-0000-000000000001"), capacity=5000)
        assert isinstance(zone.id, UUID)
        assert zone.name == "Main Stage"
        assert zone.capacity == 5000

    def test_create_with_custom_id(self) -> None:
        custom_id = UUID("12345678-1234-5678-1234-567812345678")
        zt_id = UUID("00000000-0000-0000-0000-000000000001")
        zone = Zone(name="VIP Area", zone_type_id=zt_id, capacity=200, id=custom_id)
        assert zone.id == custom_id
        assert zone.name == "VIP Area"
        assert zone.zone_type_id == zt_id
        assert zone.capacity == 200

    def test_create_strips_whitespace(self) -> None:
        zone = Zone(name="  Food Court  ", zone_type_id=UUID("00000000-0000-0000-0000-000000000001"), capacity=1000)
        assert zone.name == "Food Court"

    def test_create_minimal_name(self) -> None:
        zone = Zone(name="A", zone_type_id=UUID("00000000-0000-0000-0000-000000000001"), capacity=1)
        assert zone.name == "A"
        assert zone.capacity == 1

    def test_create_minimum_capacity(self) -> None:
        zone = Zone(name="Tiny Zone", zone_type_id=UUID("00000000-0000-0000-0000-000000000001"), capacity=1)
        assert zone.capacity == 1

    def test_create_large_capacity(self) -> None:
        zone = Zone(name="Huge Zone", zone_type_id=UUID("00000000-0000-0000-0000-000000000001"), capacity=100000)
        assert zone.capacity == 100000


class TestZoneValidation:
    def test_empty_name_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            Zone(name="", zone_type_id=UUID("00000000-0000-0000-0000-000000000001"), capacity=100)

    def test_blank_name_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            Zone(name="   ", zone_type_id=UUID("00000000-0000-0000-0000-000000000001"), capacity=100)

    def test_name_exceeds_max_length_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must not exceed 100 characters"):
            Zone(name="A" * 101, zone_type_id=UUID("00000000-0000-0000-0000-000000000001"), capacity=100)

    def test_name_at_max_length_is_valid(self) -> None:
        name = "A" * 100
        zone = Zone(name=name, zone_type_id=UUID("00000000-0000-0000-0000-000000000001"), capacity=100)
        assert zone.name == name

    def test_invalid_id_type_raises_error(self) -> None:
        with pytest.raises(TypeError, match="must be a UUID"):
            Zone(name="Test", zone_type_id=UUID("00000000-0000-0000-0000-000000000001"), capacity=100, id="not-a-uuid")  # type: ignore[arg-type]

    def test_invalid_zone_type_id_type_raises_error(self) -> None:
        with pytest.raises(TypeError, match="must be a UUID"):
            Zone(name="Test", zone_type_id="not-a-uuid", capacity=100)  # type: ignore[arg-type]

    def test_zero_capacity_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must be a positive integer"):
            Zone(name="Test", zone_type_id=UUID("00000000-0000-0000-0000-000000000001"), capacity=0)

    def test_negative_capacity_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must be a positive integer"):
            Zone(name="Test", zone_type_id=UUID("00000000-0000-0000-0000-000000000001"), capacity=-1)

    def test_float_capacity_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must be a positive integer"):
            Zone(name="Test", zone_type_id=UUID("00000000-0000-0000-0000-000000000001"), capacity=100.5)  # type: ignore[arg-type]

    def test_bool_capacity_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must be a positive integer"):
            Zone(name="Test", zone_type_id=UUID("00000000-0000-0000-0000-000000000001"), capacity=True)  # type: ignore[arg-type]

    def test_string_capacity_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must be a positive integer"):
            Zone(name="Test", zone_type_id=UUID("00000000-0000-0000-0000-000000000001"), capacity="500")  # type: ignore[arg-type]


class TestZoneEquality:
    def test_same_id_are_equal(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        zt_id = UUID("00000000-0000-0000-0000-000000000002")
        zone1 = Zone(name="Main Stage", zone_type_id=zt_id, capacity=5000, id=id)
        zone2 = Zone(name="Main Stage", zone_type_id=zt_id, capacity=5000, id=id)
        assert zone1 == zone2

    def test_different_id_are_not_equal(self) -> None:
        zt_id = UUID("00000000-0000-0000-0000-000000000001")
        zone1 = Zone(name="Zone A", zone_type_id=zt_id, capacity=100)
        zone2 = Zone(name="Zone B", zone_type_id=zt_id, capacity=200)
        assert zone1 != zone2

    def test_equality_with_non_zone(self) -> None:
        zt_id = UUID("00000000-0000-0000-0000-000000000001")
        zone = Zone(name="Test", zone_type_id=zt_id, capacity=100)
        assert (zone == "not-a-zone") is False

    def test_hash_consistency(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        zt_id = UUID("00000000-0000-0000-0000-000000000002")
        zone1 = Zone(name="Test", zone_type_id=zt_id, capacity=100, id=id)
        zone2 = Zone(name="Test", zone_type_id=zt_id, capacity=100, id=id)
        assert hash(zone1) == hash(zone2)

    def test_hash_set_membership(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        zt_id = UUID("00000000-0000-0000-0000-000000000002")
        zone = Zone(name="Test", zone_type_id=zt_id, capacity=100, id=id)
        s = {zone}
        assert Zone(name="Test", zone_type_id=zt_id, capacity=100, id=id) in s


class TestZoneImmutability:
    def test_id_is_readonly(self) -> None:
        zt_id = UUID("00000000-0000-0000-0000-000000000001")
        zone = Zone(name="Test", zone_type_id=zt_id, capacity=100)
        with pytest.raises(AttributeError):
            zone.id = UUID("00000000-0000-0000-0000-000000000000")  # type: ignore[misc]

    def test_name_is_readonly(self) -> None:
        zt_id = UUID("00000000-0000-0000-0000-000000000001")
        zone = Zone(name="Test", zone_type_id=zt_id, capacity=100)
        with pytest.raises(AttributeError):
            zone.name = "NewName"  # type: ignore[misc]

    def test_zone_type_id_is_readonly(self) -> None:
        zt_id = UUID("00000000-0000-0000-0000-000000000001")
        zone = Zone(name="Test", zone_type_id=zt_id, capacity=100)
        with pytest.raises(AttributeError):
            zone.zone_type_id = UUID("00000000-0000-0000-0000-000000000002")  # type: ignore[misc]

    def test_capacity_is_readonly(self) -> None:
        zt_id = UUID("00000000-0000-0000-0000-000000000001")
        zone = Zone(name="Test", zone_type_id=zt_id, capacity=100)
        with pytest.raises(AttributeError):
            zone.capacity = 200  # type: ignore[misc]


class TestZoneRepresentation:
    def test_repr_contains_all_fields(self) -> None:
        zt_id = UUID("00000000-0000-0000-0000-000000000042")
        id = UUID("12345678-1234-5678-1234-567812345678")
        zone = Zone(name="Entrance", zone_type_id=zt_id, capacity=3000, id=id)
        repr_str = repr(zone)
        assert "Zone" in repr_str
        assert str(id) in repr_str
        assert "Entrance" in repr_str
        assert str(zt_id) in repr_str
        assert "3000" in repr_str
