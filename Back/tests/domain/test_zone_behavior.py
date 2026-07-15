from uuid import UUID

import pytest

from src.domain.entities.zone_behavior import FlowRestriction, ZoneBehavior


class TestZoneBehaviorCreation:
    def test_create_valid_zone_behavior(self) -> None:
        zb = ZoneBehavior(
            zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
            operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
            density_factor=0.5,
            flow_restriction=FlowRestriction.OPEN,
        )
        assert isinstance(zb.id, UUID)
        assert zb.density_factor == 0.5
        assert zb.flow_restriction == FlowRestriction.OPEN

    def test_create_with_custom_id(self) -> None:
        custom_id = UUID("12345678-1234-5678-1234-567812345678")
        zb = ZoneBehavior(
            zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
            operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
            density_factor=0.3,
            flow_restriction=FlowRestriction.REGULATED,
            id=custom_id,
        )
        assert zb.id == custom_id

    def test_create_with_open_restriction(self) -> None:
        zb = ZoneBehavior(
            zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
            operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
            density_factor=0.8,
            flow_restriction=FlowRestriction.OPEN,
        )
        assert zb.flow_restriction == FlowRestriction.OPEN

    def test_create_with_regulated_restriction(self) -> None:
        zb = ZoneBehavior(
            zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
            operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
            density_factor=0.5,
            flow_restriction=FlowRestriction.REGULATED,
        )
        assert zb.flow_restriction == FlowRestriction.REGULATED

    def test_create_with_closed_restriction(self) -> None:
        zb = ZoneBehavior(
            zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
            operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
            density_factor=0.2,
            flow_restriction=FlowRestriction.CLOSED,
        )
        assert zb.flow_restriction == FlowRestriction.CLOSED

    def test_create_with_minimum_density_factor(self) -> None:
        zb = ZoneBehavior(
            zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
            operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
            density_factor=0.0,
            flow_restriction=FlowRestriction.OPEN,
        )
        assert zb.density_factor == 0.0

    def test_create_with_maximum_density_factor(self) -> None:
        zb = ZoneBehavior(
            zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
            operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
            density_factor=1.0,
            flow_restriction=FlowRestriction.OPEN,
        )
        assert zb.density_factor == 1.0

    def test_create_with_int_density_factor(self) -> None:
        zb = ZoneBehavior(
            zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
            operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
            density_factor=0,
            flow_restriction=FlowRestriction.OPEN,
        )
        assert zb.density_factor == 0


class TestZoneBehaviorValidation:
    def test_invalid_zone_type_id_raises_error(self) -> None:
        with pytest.raises(TypeError, match="must be a UUID"):
            ZoneBehavior(
                zone_type_id="not-a-uuid",  # type: ignore[arg-type]
                operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
                density_factor=0.5,
                flow_restriction=FlowRestriction.OPEN,
            )

    def test_invalid_operational_phase_id_raises_error(self) -> None:
        with pytest.raises(TypeError, match="must be a UUID"):
            ZoneBehavior(
                zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
                operational_phase_id="not-a-uuid",  # type: ignore[arg-type]
                density_factor=0.5,
                flow_restriction=FlowRestriction.OPEN,
            )

    def test_invalid_id_type_raises_error(self) -> None:
        with pytest.raises(TypeError, match="must be a UUID"):
            ZoneBehavior(
                zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
                operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
                density_factor=0.5,
                flow_restriction=FlowRestriction.OPEN,
                id="not-a-uuid",  # type: ignore[arg-type]
            )

    def test_density_factor_below_zero_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            ZoneBehavior(
                zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
                operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
                density_factor=-0.1,
                flow_restriction=FlowRestriction.OPEN,
            )

    def test_density_factor_above_one_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            ZoneBehavior(
                zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
                operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
                density_factor=1.1,
                flow_restriction=FlowRestriction.OPEN,
            )

    def test_density_factor_as_bool_raises_error(self) -> None:
        with pytest.raises(TypeError, match="must be a number"):
            ZoneBehavior(
                zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
                operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
                density_factor=True,  # type: ignore[arg-type]
                flow_restriction=FlowRestriction.OPEN,
            )

    def test_density_factor_as_string_raises_error(self) -> None:
        with pytest.raises(TypeError, match="must be a number"):
            ZoneBehavior(
                zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
                operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
                density_factor="0.5",  # type: ignore[arg-type]
                flow_restriction=FlowRestriction.OPEN,
            )

    def test_invalid_flow_restriction_string_raises_error(self) -> None:
        with pytest.raises(TypeError, match="must be a FlowRestriction enum member"):
            ZoneBehavior(
                zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
                operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
                density_factor=0.5,
                flow_restriction="OPEN",  # type: ignore[arg-type]
            )

    def test_invalid_flow_restriction_wrong_enum_raises_error(self) -> None:
        with pytest.raises(TypeError, match="must be a FlowRestriction enum member"):
            ZoneBehavior(
                zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
                operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
                density_factor=0.5,
                flow_restriction=None,  # type: ignore[arg-type]
            )


class TestZoneBehaviorEquality:
    def test_same_id_are_equal(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        zb1 = ZoneBehavior(
            zone_type_id=UUID("00000000-0000-0000-0000-000000000010"),
            operational_phase_id=UUID("00000000-0000-0000-0000-000000000020"),
            density_factor=0.5,
            flow_restriction=FlowRestriction.OPEN,
            id=id,
        )
        zb2 = ZoneBehavior(
            zone_type_id=UUID("00000000-0000-0000-0000-000000000010"),
            operational_phase_id=UUID("00000000-0000-0000-0000-000000000020"),
            density_factor=0.5,
            flow_restriction=FlowRestriction.OPEN,
            id=id,
        )
        assert zb1 == zb2

    def test_different_id_are_not_equal(self) -> None:
        zb1 = ZoneBehavior(
            zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
            operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
            density_factor=0.5,
            flow_restriction=FlowRestriction.OPEN,
        )
        zb2 = ZoneBehavior(
            zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
            operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
            density_factor=0.8,
            flow_restriction=FlowRestriction.REGULATED,
        )
        assert zb1 != zb2

    def test_equality_with_non_zone_behavior(self) -> None:
        zb = ZoneBehavior(
            zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
            operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
            density_factor=0.5,
            flow_restriction=FlowRestriction.OPEN,
        )
        assert (zb == "not-a-behavior") is False

    def test_hash_consistency(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        zb1 = ZoneBehavior(
            zone_type_id=UUID("00000000-0000-0000-0000-000000000010"),
            operational_phase_id=UUID("00000000-0000-0000-0000-000000000020"),
            density_factor=0.5,
            flow_restriction=FlowRestriction.OPEN,
            id=id,
        )
        zb2 = ZoneBehavior(
            zone_type_id=UUID("00000000-0000-0000-0000-000000000010"),
            operational_phase_id=UUID("00000000-0000-0000-0000-000000000020"),
            density_factor=0.5,
            flow_restriction=FlowRestriction.OPEN,
            id=id,
        )
        assert hash(zb1) == hash(zb2)

    def test_hash_set_membership(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        zb = ZoneBehavior(
            zone_type_id=UUID("00000000-0000-0000-0000-000000000010"),
            operational_phase_id=UUID("00000000-0000-0000-0000-000000000020"),
            density_factor=0.5,
            flow_restriction=FlowRestriction.OPEN,
            id=id,
        )
        s = {zb}
        expected = ZoneBehavior(
            zone_type_id=UUID("00000000-0000-0000-0000-000000000010"),
            operational_phase_id=UUID("00000000-0000-0000-0000-000000000020"),
            density_factor=0.5,
            flow_restriction=FlowRestriction.OPEN,
            id=id,
        )
        assert expected in s


class TestZoneBehaviorImmutability:
    def test_id_is_readonly(self) -> None:
        zb = ZoneBehavior(
            zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
            operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
            density_factor=0.5,
            flow_restriction=FlowRestriction.OPEN,
        )
        with pytest.raises(AttributeError):
            zb.id = UUID("00000000-0000-0000-0000-000000000000")  # type: ignore[misc]

    def test_zone_type_id_is_readonly(self) -> None:
        zb = ZoneBehavior(
            zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
            operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
            density_factor=0.5,
            flow_restriction=FlowRestriction.OPEN,
        )
        with pytest.raises(AttributeError):
            zb.zone_type_id = UUID("00000000-0000-0000-0000-000000000010")  # type: ignore[misc]

    def test_operational_phase_id_is_readonly(self) -> None:
        zb = ZoneBehavior(
            zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
            operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
            density_factor=0.5,
            flow_restriction=FlowRestriction.OPEN,
        )
        with pytest.raises(AttributeError):
            zb.operational_phase_id = UUID("00000000-0000-0000-0000-000000000020")  # type: ignore[misc]

    def test_density_factor_is_readonly(self) -> None:
        zb = ZoneBehavior(
            zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
            operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
            density_factor=0.5,
            flow_restriction=FlowRestriction.OPEN,
        )
        with pytest.raises(AttributeError):
            zb.density_factor = 0.8  # type: ignore[misc]

    def test_flow_restriction_is_readonly(self) -> None:
        zb = ZoneBehavior(
            zone_type_id=UUID("00000000-0000-0000-0000-000000000001"),
            operational_phase_id=UUID("00000000-0000-0000-0000-000000000002"),
            density_factor=0.5,
            flow_restriction=FlowRestriction.OPEN,
        )
        with pytest.raises(AttributeError):
            zb.flow_restriction = FlowRestriction.CLOSED  # type: ignore[misc]


class TestZoneBehaviorRepresentation:
    def test_repr_contains_all_fields(self) -> None:
        zt_id = UUID("00000000-0000-0000-0000-000000000001")
        op_id = UUID("00000000-0000-0000-0000-000000000002")
        id = UUID("12345678-1234-5678-1234-567812345678")
        zb = ZoneBehavior(
            zone_type_id=zt_id,
            operational_phase_id=op_id,
            density_factor=0.75,
            flow_restriction=FlowRestriction.REGULATED,
            id=id,
        )
        repr_str = repr(zb)
        assert "ZoneBehavior" in repr_str
        assert str(id) in repr_str
        assert str(zt_id) in repr_str
        assert str(op_id) in repr_str
        assert "0.75" in repr_str
        assert "REGULATED" in repr_str
