from __future__ import annotations

from src.infrastructure.persistence.repositories.event_day_repository import (
    SQLEventDayRepository,
)
from src.infrastructure.persistence.repositories.operational_event_repository import (
    SQLOperationalEventRepository,
)
from src.infrastructure.persistence.repositories.configuration_recommendation_repository import (
    SQLConfigurationRecommendationRepository,
)
from src.infrastructure.persistence.repositories.recommendation_audit_entry_repository import (
    SQLRecommendationAuditEntryRepository,
)
from src.infrastructure.persistence.repositories.zone_recommendation_repository import (
    SQLZoneRecommendationRepository,
)