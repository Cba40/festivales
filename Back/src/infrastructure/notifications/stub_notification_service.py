from __future__ import annotations

import logging

from src.domain.entities.configuration_recommendation import ConfigurationRecommendation
from src.domain.ports.notification_service import NotificationService


class StubNotificationService(NotificationService):
    """Implementación stub: solo registra en log."""

    def notify_new_recommendation(self, recommendation: ConfigurationRecommendation) -> None:
        logger = logging.getLogger(__name__)
        logger.info(
            f"Nueva recomendación pendiente: {recommendation.id} "
            f"(tipo: {recommendation.recommendation_type.value if recommendation.recommendation_type else 'N/A'}, "
            f"estado: {recommendation.status.value})"
        )