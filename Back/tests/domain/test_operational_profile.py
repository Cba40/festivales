from uuid import UUID

import pytest

from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.operational_profile import OperationalProfile


class TestOperationalProfileCreation:
    def test_create_valid_profile(self) -> None:
        phase1 = OperationalPhase(name="Apertura", sequence_order=1)
        profile = OperationalProfile(name="Perfil Estándar", phases=(phase1,))
        assert isinstance(profile.id, UUID)
        assert profile.name == "Perfil Estándar"
        assert len(profile.phases) == 1
        assert profile.phases[0] is phase1

    def test_create_with_multiple_phases(self) -> None:
        phase1 = OperationalPhase(name="Apertura", sequence_order=1)
        phase2 = OperationalPhase(name="Pico", sequence_order=2)
        phase3 = OperationalPhase(name="Cierre", sequence_order=3)
        profile = OperationalProfile(
            name="Perfil Completo",
            phases=(phase1, phase2, phase3),
        )
        assert len(profile.phases) == 3
        assert profile.phases[0].name == "Apertura"
        assert profile.phases[1].name == "Pico"
        assert profile.phases[2].name == "Cierre"

    def test_create_with_custom_id(self) -> None:
        custom_id = UUID("12345678-1234-5678-1234-567812345678")
        phase1 = OperationalPhase(name="Única", sequence_order=1)
        profile = OperationalProfile(
            name="Personalizado",
            phases=(phase1,),
            id=custom_id,
        )
        assert profile.id == custom_id

    def test_create_strips_whitespace(self) -> None:
        phase1 = OperationalPhase(name="Fase", sequence_order=1)
        profile = OperationalProfile(name="  Perfil  ", phases=(phase1,))
        assert profile.name == "Perfil"

    def test_create_minimal_name(self) -> None:
        phase1 = OperationalPhase(name="Fase", sequence_order=1)
        profile = OperationalProfile(name="P", phases=(phase1,))
        assert profile.name == "P"


class TestOperationalProfileValidation:
    def test_empty_name_raises_error(self) -> None:
        phase1 = OperationalPhase(name="Fase", sequence_order=1)
        with pytest.raises(ValueError, match="must not be empty"):
            OperationalProfile(name="", phases=(phase1,))

    def test_blank_name_raises_error(self) -> None:
        phase1 = OperationalPhase(name="Fase", sequence_order=1)
        with pytest.raises(ValueError, match="must not be empty"):
            OperationalProfile(name="   ", phases=(phase1,))

    def test_name_exceeds_max_length_raises_error(self) -> None:
        phase1 = OperationalPhase(name="Fase", sequence_order=1)
        with pytest.raises(ValueError, match="must not exceed 100 characters"):
            OperationalProfile(name="A" * 101, phases=(phase1,))

    def test_name_at_max_length_is_valid(self) -> None:
        phase1 = OperationalPhase(name="Fase", sequence_order=1)
        name = "A" * 100
        profile = OperationalProfile(name=name, phases=(phase1,))
        assert profile.name == name

    def test_invalid_id_type_raises_error(self) -> None:
        phase1 = OperationalPhase(name="Fase", sequence_order=1)
        with pytest.raises(TypeError, match="must be a UUID"):
            OperationalProfile(name="Test", phases=(phase1,), id="not-a-uuid")  # type: ignore[arg-type]

    def test_empty_phases_raises_error(self) -> None:
        with pytest.raises(ValueError, match="must contain at least one phase"):
            OperationalProfile(name="Test", phases=())

    def test_non_tuple_phases_raises_error(self) -> None:
        phase1 = OperationalPhase(name="Fase", sequence_order=1)
        with pytest.raises(ValueError, match="must contain at least one phase"):
            OperationalProfile(name="Test", phases=None)  # type: ignore[arg-type]

    def test_duplicate_sequence_order_raises_error(self) -> None:
        phase1 = OperationalPhase(name="Primera", sequence_order=1)
        phase2 = OperationalPhase(name="Duplicada", sequence_order=1)
        with pytest.raises(ValueError, match="duplicate sequence_order"):
            OperationalProfile(name="Test", phases=(phase1, phase2))

    def test_out_of_order_phases_raises_error(self) -> None:
        phase1 = OperationalPhase(name="Segunda", sequence_order=2)
        phase2 = OperationalPhase(name="Primera", sequence_order=1)
        with pytest.raises(ValueError, match="must be ordered by ascending"):
            OperationalProfile(name="Test", phases=(phase1, phase2))

    def test_non_operational_phase_in_collection_raises_error(self) -> None:
        with pytest.raises(TypeError, match="must be an OperationalPhase instance"):
            OperationalProfile(
                name="Test",
                phases=(OperationalPhase(name="Real", sequence_order=1), "not-a-phase"),  # type: ignore[arg-type]
            )


class TestOperationalProfileOrder:
    def test_preserves_phase_order(self) -> None:
        phase1 = OperationalPhase(name="Primera", sequence_order=1)
        phase2 = OperationalPhase(name="Segunda", sequence_order=2)
        phase3 = OperationalPhase(name="Tercera", sequence_order=3)
        profile = OperationalProfile(
            name="Test",
            phases=(phase1, phase2, phase3),
        )
        orders = [p.sequence_order for p in profile.phases]
        assert orders == [1, 2, 3]
        names = [p.name for p in profile.phases]
        assert names == ["Primera", "Segunda", "Tercera"]

    def test_phases_tuple_is_immutable(self) -> None:
        phase1 = OperationalPhase(name="Única", sequence_order=1)
        profile = OperationalProfile(name="Test", phases=(phase1,))
        assert isinstance(profile.phases, tuple)


class TestOperationalProfileEquality:
    def test_same_id_are_equal(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        phase1 = OperationalPhase(name="Fase", sequence_order=1)
        p1 = OperationalProfile(name="Perfil A", phases=(phase1,), id=id)
        p2 = OperationalProfile(name="Perfil A", phases=(phase1,), id=id)
        assert p1 == p2

    def test_different_id_are_not_equal(self) -> None:
        phase1 = OperationalPhase(name="Fase", sequence_order=1)
        p1 = OperationalProfile(name="Perfil A", phases=(phase1,))
        p2 = OperationalProfile(name="Perfil B", phases=(phase1,))
        assert p1 != p2

    def test_equality_with_non_operational_profile(self) -> None:
        phase1 = OperationalPhase(name="Fase", sequence_order=1)
        profile = OperationalProfile(name="Test", phases=(phase1,))
        assert (profile == "not-a-profile") is False

    def test_hash_consistency(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        phase1 = OperationalPhase(name="Fase", sequence_order=1)
        p1 = OperationalProfile(name="Test", phases=(phase1,), id=id)
        p2 = OperationalProfile(name="Test", phases=(phase1,), id=id)
        assert hash(p1) == hash(p2)

    def test_hash_set_membership(self) -> None:
        id = UUID("00000000-0000-0000-0000-000000000001")
        phase1 = OperationalPhase(name="Fase", sequence_order=1)
        profile = OperationalProfile(name="Test", phases=(phase1,), id=id)
        s = {profile}
        assert OperationalProfile(name="Test", phases=(phase1,), id=id) in s


class TestOperationalProfileImmutability:
    def test_id_is_readonly(self) -> None:
        phase1 = OperationalPhase(name="Fase", sequence_order=1)
        profile = OperationalProfile(name="Test", phases=(phase1,))
        with pytest.raises(AttributeError):
            profile.id = UUID("00000000-0000-0000-0000-000000000000")  # type: ignore[misc]

    def test_name_is_readonly(self) -> None:
        phase1 = OperationalPhase(name="Fase", sequence_order=1)
        profile = OperationalProfile(name="Test", phases=(phase1,))
        with pytest.raises(AttributeError):
            profile.name = "NewName"  # type: ignore[misc]

    def test_phases_is_readonly(self) -> None:
        phase1 = OperationalPhase(name="Fase", sequence_order=1)
        profile = OperationalProfile(name="Test", phases=(phase1,))
        with pytest.raises(AttributeError):
            profile.phases = ()  # type: ignore[misc]


class TestOperationalProfileRepresentation:
    def test_repr_contains_id_name_and_phases_count(self) -> None:
        id = UUID("12345678-1234-5678-1234-567812345678")
        phase1 = OperationalPhase(name="Apertura", sequence_order=1)
        phase2 = OperationalPhase(name="Cierre", sequence_order=2)
        profile = OperationalProfile(
            name="Perfil Dual",
            phases=(phase1, phase2),
            id=id,
        )
        repr_str = repr(profile)
        assert "OperationalProfile" in repr_str
        assert str(id) in repr_str
        assert "Perfil Dual" in repr_str
        assert "phases_count=2" in repr_str
