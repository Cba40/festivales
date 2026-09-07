from __future__ import annotations


class NotificationService:
    """Interfaz para notificación de nuevas recomendaciones."""

    def notify_new_recommendation(self, recommendation: "ConfigurationRecommendation") -> None:
        """Notifica a roles autorizados sobre nueva recomendación pendiente."""
        raise NotImplementedError()