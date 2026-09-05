from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.domain.entities.knowledge_model_version import KnowledgeModelVersion
from src.domain.entities.zone import Zone
from src.domain.entities.zone_type import ZoneType
from src.domain.entities.zone_behavior import ZoneBehavior
from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.event_day import EventDay
from src.domain.entities.event_day_phase import EventDayPhase
from src.infrastructure.persistence.repositories.event_day_repository import SQLEventDayRepository
from src.infrastructure.persistence.repositories.zone_repository import SQLZoneRepository
from src.infrastructure.persistence.repositories.zone_type_repository import SQLZoneTypeRepository
from src.infrastructure.persistence.repositories.zone_behavior_repository import SQLZoneBehaviorRepository
from src.infrastructure.persistence.repositories.attendance_level_repository import SQLAttendanceLevelRepository
from src.infrastructure.persistence.repositories.operational_phase_repository import SQLOperationalPhaseRepository
from src.infrastructure.persistence.repositories.event_day_phase_repository import SQLEventDayPhaseRepository
from src.infrastructure.persistence.repositories.knowledge_model_version_repository import SQLKnowledgeModelVersionRepository


class KnowledgeModelSnapshotService:
    """Servicio para crear y obtener snapshots del Knowledge Model.

    RFC-006 §9: Toda TerritorialPrediction histórica DEBE mantener una referencia
    inmutable a la versión exacta del Knowledge Model utilizada para su cálculo,
    permitiendo reproducibilidad analítica futura.
    """

    def __init__(
        self,
        zone_repo: SQLZoneRepository,
        zone_behavior_repo: SQLZoneBehaviorRepository,
        zone_type_repo: SQLZoneTypeRepository,
        attendance_level_repo: SQLAttendanceLevelRepository,
        operational_phase_repo: SQLOperationalPhaseRepository,
        event_day_repo: SQLEventDayRepository,
        event_day_phase_repo: SQLEventDayPhaseRepository,
        km_version_repo: SQLKnowledgeModelVersionRepository,
    ) -> None:
        self._zone_repo = zone_repo
        self._zone_behavior_repo = zone_behavior_repo
        self._zone_type_repo = zone_type_repo
        self._attendance_level_repo = attendance_level_repo
        self._operational_phase_repo = operational_phase_repo
        self._event_day_repo = event_day_repo
        self._event_day_phase_repo = event_day_phase_repo
        self._km_version_repo = km_version_repo

    async def create_snapshot(self, created_by: UUID | None = None) -> KnowledgeModelVersion:
        """Crea un nuevo snapshot del Knowledge Model con el estado actual.

        Se obtienen todas las entidades del KM según RFC-006 §9 para garantizar
        la reproducibilidad analítica futura de las TerritorialPrediction generadas.
        """
        # 1. Obtener todas las entidades del KM
        zones = await self._zone_repo.find_all()
        zone_behaviors = await self._zone_behavior_repo.find_all()
        zone_types = await self._zone_type_repo.find_all()
        attendance_levels = await self._attendance_level_repo.find_all()
        operational_phases = await self._operational_phase_repo.find_all()
        event_days = await self._event_day_repo.find_by_date(datetime.now(timezone.utc).date())
        event_day_phases = await self._event_day_phase_repo.find_all()

        # 2. Construir snapshot_data con TODAS las entidades requeridas por RFC-006 §9
        snapshot_data = {
            "zones": [
                {
                    "id": str(z.id),
                    "name": z.name,
                    "capacity": z.capacity,
                    "type": z.type,
                    "subtipo": z.subtipo,
                }
                for z in zones
            ],
            "zone_types": [
                {
                    "id": str(zt.id),
                    "name": zt.name,
                }
                for zt in zone_types
            ],
            "zone_behaviors": [
                {
                    "id": str(zb.id),
                    "density_factor": zb.density_factor,
                    "flow_restriction": zb.flow_restriction.value,
                }
                for zb in zone_behaviors
            ],
            "attendance_levels": [
                {
                    "id": str(al.id),
                    "name": al.name,
                    "multiplier": al.multiplier,
                }
                for al in attendance_levels
            ],
            "operational_phases": [
                {
                    "id": str(op.id),
                    "name": op.name,
                    "sequence_order": op.sequence_order,
                }
                for op in operational_phases
            ],
            "event_days": [
                {
                    "id": str(ed.id),
                    "date": ed.event_date.isoformat() if ed.event_date else None,
                    "operational_start_min": ed.operational_start_min,
                    "operational_end_min": ed.operational_end_min,
                }
                for ed in event_days
            ],
            "event_day_phases": [
                {
                    "id": str(edp.id),
                    "event_day_id": str(edp.event_day_id),
                    "operational_phase_id": str(edp.operational_phase_id),
                    "start_min": edp.start_min,
                    "end_min": edp.end_min,
                }
                for edp in event_day_phases
            ],
        }

        # 2. Obtener próximo número de versión
        next_version = await self._km_version_repo.get_next_version_number()

        # 3. Crear versión con ID basado en UUID v4
        version_id = uuid4()

        version = KnowledgeModelVersion(
            id=version_id,
            version_number=next_version,
            snapshot_data=snapshot_data,
            created_at=datetime.now(timezone.utc),
            created_by=created_by,
        )

        # 3. Guardar versión en repositorio
        return await self._km_version_repo.save(version)

    async def get_or_create_current_version(self, created_by: UUID | None = None) -> KnowledgeModelVersion:
        """Obtiene la versión actual o la crea si no existe."""
        latest = await self._km_version_repo.find_latest()
        if latest is not None:
            return latest
        return await self.create_snapshot(created_by=created_by)