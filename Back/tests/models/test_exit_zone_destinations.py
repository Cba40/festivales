# backend/tests/models/test_exit_zone_destinations.py
# PARTE 2 (S1 - Salir V1): relación N:N exit_zone_destinations.

from app.db.session import Base
from app.models.exit_destination import ExitDestination
from app.models.exit_zone_destination import exit_zone_destinations_table
from app.models.zone import Zone


def _get_relationships(model):
    # Fuerza la configuración de mappers: valida el grafo completo de
    # relaciones (secondary, back_populates) sin necesitar una BD.
    model.__mapper__.relationships
    return {rel.key: rel for rel in model.__mapper__.relationships}


class TestExitZoneDestinationsTable:
    """Estructura de la tabla de asociación en Base.metadata."""

    def test_registered_in_base_metadata(self) -> None:
        assert "exit_zone_destinations" in Base.metadata.tables

    def test_table_object_points_to_metadata_table(self) -> None:
        assert exit_zone_destinations_table is Base.metadata.tables["exit_zone_destinations"]

    def test_has_exactly_two_columns(self) -> None:
        cols = set(exit_zone_destinations_table.columns.keys())
        assert cols == {"exit_zone_id", "destination_id"}

    def test_composite_primary_key(self) -> None:
        pk_cols = [c.name for c in exit_zone_destinations_table.primary_key.columns]
        assert sorted(pk_cols) == ["destination_id", "exit_zone_id"]

    def test_ids_are_string36(self) -> None:
        for name in ("exit_zone_id", "destination_id"):
            col = exit_zone_destinations_table.columns[name]
            assert col.type.length == 36
            assert col.nullable is False

    def test_fk_to_zones_with_cascade(self) -> None:
        col = exit_zone_destinations_table.columns["exit_zone_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert fks[0].target_fullname == "zones.id"
        assert fks[0].ondelete == "CASCADE"

    def test_fk_to_exit_destinations_with_cascade(self) -> None:
        col = exit_zone_destinations_table.columns["destination_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert fks[0].target_fullname == "exit_destinations.id"
        assert fks[0].ondelete == "CASCADE"

    def test_indexes_created(self) -> None:
        index_names = {idx.name for idx in exit_zone_destinations_table.indexes}
        assert {"idx_ezd_zone", "idx_ezd_destination"} <= index_names


class TestManyToManyRelationshipWiring:
    """Relaciones Zone <-> ExitDestination vía secondary."""

    def test_zone_has_destinations_relationship(self) -> None:
        rels = _get_relationships(Zone)
        assert "destinations" in rels
        assert rels["destinations"].secondary.name == "exit_zone_destinations"

    def test_exit_destination_has_inverse_zones_relationship(self) -> None:
        rels = _get_relationships(ExitDestination)
        assert "zones" in rels
        assert rels["zones"].secondary.name == "exit_zone_destinations"

    def test_back_populates_wiring(self) -> None:
        zone_rels = _get_relationships(Zone)
        dest_rels = _get_relationships(ExitDestination)
        assert zone_rels["destinations"].back_populates == "zones"
        assert dest_rels["zones"].back_populates == "destinations"

    def test_relationship_targets(self) -> None:
        zone_rels = _get_relationships(Zone)
        dest_rels = _get_relationships(ExitDestination)
        assert zone_rels["destinations"].mapper.entity is ExitDestination
        assert dest_rels["zones"].mapper.entity is Zone

    def test_secondary_is_foreign_key_bound_table(self) -> None:
        # La tabla secundaria referencia a ambas entidades por FK.
        fks = {
            fk.target_fullname
            for fk_col in exit_zone_destinations_table.foreign_key_constraints
            for fk in fk_col.elements
        }
        assert {"zones.id", "exit_destinations.id"} <= fks
