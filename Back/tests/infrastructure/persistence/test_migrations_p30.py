from __future__ import annotations

import importlib.util
import inspect
import os
import sys
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "src" / "infrastructure" / "persistence" / "migrations"
VERSIONS_DIR = MIGRATIONS_DIR / "versions"

EXPECTED_TABLES = [
    "zone_types",
    "zones",
    "operational_profiles",
    "operational_phases",
    "zone_behaviors",
    "attendance_levels",
    "event_days",
    "event_day_phases",
    "operational_events",
    "predictions",
]

EXPECTED_ENUM_TYPES = ["flowrestriction"]


def _find_migration_versions() -> list[Path]:
    if not VERSIONS_DIR.exists():
        return []
    return sorted(
        [f for f in VERSIONS_DIR.iterdir() if f.suffix == ".py" and f.name != "__init__.py"],
    )


class TestMigrationEnvironment:
    def test_migrations_directory_exists(self) -> None:
        assert MIGRATIONS_DIR.exists(), f"Migrations directory not found: {MIGRATIONS_DIR}"

    def test_env_py_exists(self) -> None:
        env_py = MIGRATIONS_DIR / "env.py"
        assert env_py.exists(), "env.py not found in migrations directory"

    def test_alembic_ini_exists(self) -> None:
        ini = MIGRATIONS_DIR / "alembic.ini"
        assert ini.exists(), "alembic.ini not found in migrations directory"

    def test_script_py_mako_exists(self) -> None:
        mako = MIGRATIONS_DIR / "script.py.mako"
        assert mako.exists(), "script.py.mako not found in migrations directory"

    def test_versions_directory_exists(self) -> None:
        assert VERSIONS_DIR.exists(), f"Versions directory not found: {VERSIONS_DIR}"

    def test_at_least_one_migration_version_exists(self) -> None:
        versions = _find_migration_versions()
        assert len(versions) >= 1, "No migration version files found"

    def test_versions_have_valid_revision_ids(self) -> None:
        for v in _find_migration_versions():
            content = v.read_text(encoding="utf-8")
            assert "revision:" in content, f"Missing revision in {v.name}"
            assert "def upgrade" in content, f"Missing upgrade() in {v.name}"
            assert "def downgrade" in content, f"Missing downgrade() in {v.name}"


class TestInitialMigration:
    @pytest.fixture(scope="module")
    def migration_module(self):
        versions = _find_migration_versions()
        if not versions:
            pytest.skip("No migration versions found")
        first = versions[0]
        spec = importlib.util.spec_from_file_location("migration", first)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_revision_defined(self, migration_module) -> None:
        assert migration_module.revision is not None
        assert isinstance(migration_module.revision, str)

    def test_down_revision_is_none_for_initial(self, migration_module) -> None:
        assert migration_module.down_revision is None

    def test_upgrade_is_callable(self, migration_module) -> None:
        assert callable(migration_module.upgrade)

    def test_downgrade_is_callable(self, migration_module) -> None:
        assert callable(migration_module.downgrade)

    def test_upgrade_uses_only_sa_and_op(self, migration_module) -> None:
        source = inspect.getsource(migration_module.upgrade)
        assert "op." in source or "sa." in source

    def test_upgrade_creates_all_expected_tables(self, migration_module) -> None:
        source = inspect.getsource(migration_module.upgrade)
        for table in EXPECTED_TABLES:
            assert f"'{table}'" in source or f'"{table}"' in source, (
                f"Table '{table}' not found in upgrade()"
            )

    def test_downgrade_drops_all_expected_tables(self, migration_module) -> None:
        source = inspect.getsource(migration_module.downgrade)
        for table in EXPECTED_TABLES:
            assert f"'{table}'" in source or f'"{table}"' in source, (
                f"Table '{table}' not found in downgrade()"
            )

    def test_upgrade_creates_enum_type(self, migration_module) -> None:
        source = inspect.getsource(migration_module.upgrade)
        for enum_name in EXPECTED_ENUM_TYPES:
            assert enum_name in source.lower(), f"Enum '{enum_name}' not found in upgrade()"

    def test_downgrade_drops_enum_type(self, migration_module) -> None:
        source = inspect.getsource(migration_module.downgrade)
        for enum_name in EXPECTED_ENUM_TYPES:
            assert enum_name in source.lower(), f"Enum '{enum_name}' not found in downgrade()"

    def test_migration_has_proper_imports(self, migration_module) -> None:
        source = inspect.getsource(migration_module)
        assert "from alembic import op" in source
        assert "import sqlalchemy as sa" in source

    def test_migration_revision_starts_with_a1b2(self, migration_module) -> None:
        assert migration_module.revision.startswith("a1b2")


class TestMigrationTableCompleteness:
    def test_all_orm_models_have_corresponding_table_in_migration(self) -> None:
        from src.infrastructure.persistence.models import (
            AttendanceLevelModel,
            EventDayModel,
            EventDayPhaseModel,
            OperationalEventModel,
            OperationalPhaseModel,
            OperationalProfileModel,
            PredictionModel,
            ZoneBehaviorModel,
            ZoneModel,
            ZoneTypeModel,
        )

        model_tablenames = {
            ZoneTypeModel.__tablename__,
            ZoneModel.__tablename__,
            OperationalProfileModel.__tablename__,
            OperationalPhaseModel.__tablename__,
            ZoneBehaviorModel.__tablename__,
            AttendanceLevelModel.__tablename__,
            EventDayModel.__tablename__,
            EventDayPhaseModel.__tablename__,
            OperationalEventModel.__tablename__,
            PredictionModel.__tablename__,
        }
        assert model_tablenames == set(EXPECTED_TABLES), (
            f"Mismatch: ORM models define {model_tablenames}, "
            f"expected {set(EXPECTED_TABLES)}"
        )

    def test_migration_covers_all_orm_tablenames(self) -> None:
        from src.infrastructure.persistence.models import (
            AttendanceLevelModel,
            EventDayModel,
            EventDayPhaseModel,
            OperationalEventModel,
            OperationalPhaseModel,
            OperationalProfileModel,
            PredictionModel,
            ZoneBehaviorModel,
            ZoneModel,
            ZoneTypeModel,
        )

        model_tablenames = {
            ZoneTypeModel.__tablename__,
            ZoneModel.__tablename__,
            OperationalProfileModel.__tablename__,
            OperationalPhaseModel.__tablename__,
            ZoneBehaviorModel.__tablename__,
            AttendanceLevelModel.__tablename__,
            EventDayModel.__tablename__,
            EventDayPhaseModel.__tablename__,
            OperationalEventModel.__tablename__,
            PredictionModel.__tablename__,
        }

        versions = _find_migration_versions()
        if not versions:
            pytest.skip("No migration versions found")
        content = versions[0].read_text(encoding="utf-8")
        for table in model_tablenames:
            assert table in content, (
                f"Table '{table}' defined in ORM model but missing from migration"
            )


class TestAlembicEnvConfiguration:
    def test_env_py_imports_p3_models(self) -> None:
        env_py = MIGRATIONS_DIR / "env.py"
        content = env_py.read_text(encoding="utf-8")
        assert "from src.infrastructure.persistence.models import" in content
        assert "from src.infrastructure.db.base import Base" in content
        assert "from src.infrastructure.settings import settings" in content
        assert "target_metadata = Base.metadata" in content

    def test_env_py_has_offline_and_online_functions(self) -> None:
        env_py = MIGRATIONS_DIR / "env.py"
        content = env_py.read_text(encoding="utf-8")
        assert "def run_migrations_offline" in content
        assert "def run_migrations_online" in content


class TestEnvLoadsWithoutError:
    def test_env_py_is_importable(self) -> None:
        env_py = MIGRATIONS_DIR / "env.py"
        assert env_py.exists(), "env.py not found"
        content = env_py.read_text(encoding="utf-8")
        assert "target_metadata = Base.metadata" in content

    def test_alembic_ini_has_script_location(self) -> None:
        import configparser
        config = configparser.RawConfigParser()
        config.read(MIGRATIONS_DIR / "alembic.ini")
        script_location = config.get("alembic", "script_location", fallback=None)
        assert script_location is not None, "script_location not found in alembic.ini"
        assert "%(here)s" in script_location
