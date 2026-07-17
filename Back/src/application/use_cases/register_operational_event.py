from __future__ import annotations

from datetime import datetime
from uuid import UUID

from src.application.context_engine.exceptions import InvalidConfiguration
from src.domain.entities.operational_event import OperationalEvent
from src.domain.ports import OperationalEventRepository, ZoneRepository


class RegisterOperationalEvent:
    def __init__(
        self,
        event_repo: OperationalEventRepository,
        zone_repo: ZoneRepository,
    ) -> None:
        self._event_repo = event_repo
        self._zone_repo = zone_repo

    async def execute(
        self,
        target_zone_id: UUID,
        impact_value: int,
        is_incident: bool,
        start_timestamp: datetime,
        end_timestamp: datetime,
    ) -> OperationalEvent:
        zone = await self._zone_repo.find_by_id(target_zone_id)
        if zone is None:
            raise InvalidConfiguration(
                f"Zone {target_zone_id} not found"
            )

        event = OperationalEvent(
            target_zone_id=target_zone_id,
            impact_value=impact_value,
            is_incident=is_incident,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
        )

        return await self._event_repo.save(event)
