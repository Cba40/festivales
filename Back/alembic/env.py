from logging.config import fileConfig

from sqlalchemy import MetaData, engine_from_config
from sqlalchemy import pool

from alembic import context

from app.core.config import settings
from app.db.session import Base as AppBase
from src.infrastructure.db.base import Base as SrcBase

import app.models.event
import app.models.zone
import app.models.point
from app.models.operational_profile import OperationalProfile
from app.models.operational_phase import OperationalPhase
from app.models.zone_behavior import ZoneBehavior
from app.models.operational_event import OperationalEvent
from app.models.motor_config import RecommendationConfigModel, Stage4ConfigModel
import app.models.accommodation
import app.models.exit_destination
import app.models.transport_line
import app.models.transport_line_stop
import app.models.transport_schedule
import app.models.city
import app.models.emergency
import app.models.emergency_protocol
import app.models.transport_alert
import app.models.operator_message
import app.models.service_interaction_log
import app.models.zone_subtype

# La capa src/ registra sus modelos en su propio Base (src.infrastructure.db.base),
# no en app.db.session.Base. Sin importarlos aca, Alembic no los ve y los propone
# como tablas sobrantes -> op.drop_table sobre operational_observations,
# predictions, knowledge_model_versions y zone_recommendations.
from src.infrastructure.persistence.models import (
    AttendanceLevelModel,
    EventDayModel,
    EventDayPhaseModel,
    KnowledgeModelVersionModel,
    OperationalEventModel,
    OperationalObservationModel,
    OperationalPhaseModel,
    OperationalProfileModel,
    PredictionModel,
    ZoneBehaviorModel,
    ZoneModel,
    ZoneRecommendationModel,
    ZoneTypeModel,
)
from src.infrastructure.persistence.models.configuration_recommendation import (
    ConfigurationRecommendation,
)
from src.infrastructure.persistence.models.recommendation_audit_entry import (
    RecommendationAuditEntry,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata es un unico MetaData, pero el proyecto tiene dos bases de
# declarativos. Se fusionan en una copia nueva (no se muta app.db.session.Base)
# para que --autogenerate vea la union y no produzca drop_table de lo que no ve.
# Ante nombres compartidos (9 tablas presentes en ambas capas) gana la capa app:
# es la que describe el esquema que las migraciones de este arbol materializan.
target_metadata = MetaData()
for _table in AppBase.metadata.tables.values():
    _table.to_metadata(target_metadata)
for _table in SrcBase.metadata.tables.values():
    if _table.name not in target_metadata.tables:
        _table.to_metadata(target_metadata)


def include_object(obj, name, type_, reflected, compare_to):
    """Excluir tablas del sistema de PostGIS para no eliminarlas."""
    if type_ == "table" and name == "spatial_ref_sys":
        return False
    return True


def run_migrations_offline() -> None:
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.DATABASE_URL
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
