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
#
# Antes este import traia tambien los 9 modelos fantasma de `src/`
# (AttendanceLevelModel, EventDayModel, EventDayPhaseModel, OperationalEventModel,
# OperationalPhaseModel, OperationalProfileModel, ZoneModel, ZoneBehaviorModel,
# ZoneTypeModel). Eran un diseno P3.0 abandonado que nunca llego a las
# migraciones, y por eso el merge de `target_metadata` (mas abajo) necesitaba una
# regla de desempate por nombre de tabla. Con la deuda saldada ya no hay
# solapamiento entre las dos capas y el merge es directo.
#
# Las dos tablas que quedan fuera de este import se traen por su modulo porque el
# barrel de models/ no las reexporta: son de dominios distintos (recomendaciones y
# auditoria) y sus repositorios las importan por ruta directa.
from src.infrastructure.persistence.models import (
    KnowledgeModelVersionModel,
    OperationalObservationModel,
    PredictionModel,
    ZoneRecommendationModel,
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
#
# Hoy las dos capas no comparten ninguna tabla: app/ aporta 26 y src/ aporta 6, y
# el conjunto es disjunto. Antes hubo 9 nombres compartidos y por eso hacia falta
# un desempate explicito; con la deuda saldada, copiar en cualquier orden daria lo
# mismo. El `if` se conserva como red de seguridad: si alguien reintrodujera una
# tabla duplicada, salta por encima en vez de romper el merge, y ademas
# tests/infrastructure/test_model_drift.py falla explicitamente. Que se avise en
# el log de Alembic y en el test es preferible a que el merge se rompa en silencio.
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
