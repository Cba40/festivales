"""Tests del endpoint POST /api/analytics/evaluate (ETAPA 2).

Todo el acceso a BD y al workflow es simulado: se valida el contrato HTTP
de la ruta y la lógica de anomalías/recomendaciones.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.db.session import get_async_db
from app.main import app
from src.application.learning.metric_result import MetricResult
from src.domain.entities.configuration_recommendation import ConfigurationRecommendation
from src.domain.entities.recommendation_enums import RecommendationStatus, RecommendationType

ENDPOINT = "/api/analytics/evaluate"
EVENT_DAY = "test-day-0001"
PHASE = "22222222-2222-2222-2222-222222222222"


def _metric(
    name: str,
    display_name: str,
    status: str,
    value: float | None,
    data_points: int = 0,
) -> MetricResult:
    return MetricResult(
        name=name,
        display_name=display_name,
        status=status,
        value=value,
        reason=f"reason-{name}",
        data_points=data_points,
        limitations=["limitación documentada"],
    )


def _results_all_blocked() -> list[MetricResult]:
    return [
        _metric("density_deviation", "Desviación de Densidad", "BLOCKED", None),
        _metric("incident_frequency", "Frecuencia de Incidentes", "BLOCKED", None),
        _metric("phase_transition_latency", "Latencia de Transición de Fase", "BLOCKED", None),
        _metric("zone_behavior_adherence", "Adherencia a ZoneBehavior", "BLOCKED", None),
    ]


def _results_no_anomalies() -> list[MetricResult]:
    return [
        _metric("density_deviation", "Desviación de Densidad", "ENABLED", 0.1, data_points=4),
        _metric("incident_frequency", "Frecuencia de Incidentes", "ENABLED", 0.3, data_points=2),
        _metric("phase_transition_latency", "Latencia de Transición de Fase", "BLOCKED", None),
        _metric("zone_behavior_adherence", "Adherencia a ZoneBehavior", "ENABLED", 0.95, data_points=4),
    ]


def _results_with_anomalies() -> list[MetricResult]:
    return [
        _metric("density_deviation", "Desviación de Densidad", "ENABLED", 0.45, data_points=4),
        _metric("incident_frequency", "Frecuencia de Incidentes", "ENABLED", 0.3, data_points=2),
        _metric("phase_transition_latency", "Latencia de Transición de Fase", "BLOCKED", None),
        _metric("zone_behavior_adherence", "Adherencia a ZoneBehavior", "ENABLED", 0.98, data_points=4),
    ]


def _results_two_anomalies() -> list[MetricResult]:
    return [
        _metric("density_deviation", "Desviación de Densidad", "ENABLED", 0.45, data_points=4),
        _metric("incident_frequency", "Frecuencia de Incidentes", "ENABLED", 0.3, data_points=2),
        _metric("phase_transition_latency", "Latencia de Transición de Fase", "BLOCKED", None),
        _metric("zone_behavior_adherence", "Adherencia a ZoneBehavior", "ENABLED", 0.2, data_points=4),
    ]


def _fake_recommendation(metric_name: str) -> ConfigurationRecommendation:
    return ConfigurationRecommendation(
        id=uuid4(),
        target_entity_type="event_day",
        target_entity_id=EVENT_DAY,
        proposed_change="acción sugerida",
        recommendation_type=RecommendationType.PARAMETER_ADJUSTMENT,
        supporting_metrics={"metric": metric_name},
        recommendation_confidence=0.9,
        status=RecommendationStatus.PENDING_REVIEW,
    )


@pytest.fixture(autouse=True)
def _clean_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _metric_service():
    with patch("app.api.routes.analytics.MetricService") as cls:
        calc_all = AsyncMock()
        cls.return_value.calculate_all = calc_all
        yield calc_all


@pytest.fixture(autouse=True)
def _workflow_service():
    svc = MagicMock()
    svc.create_recommendation = AsyncMock()
    with patch(
        "app.api.routes.analytics._get_workflow_service",
        new_callable=AsyncMock,
    ) as factory:
        factory.return_value = svc
        yield svc


@pytest.fixture
def auth_headers() -> dict[str, str]:
    expire = datetime.now(timezone.utc) + timedelta(hours=8)
    token = jwt.encode(
        {"sub": "admin", "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client() -> TestClient:
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def db_mock() -> AsyncMock:
    db = AsyncMock()
    found = MagicMock()
    found.scalar_one_or_none.return_value = object()
    db.execute.return_value = found

    async def override():
        yield db

    app.dependency_overrides[get_async_db] = override
    return db


class TestEvaluationEndpoint:
    def test_401_without_token(self, client: TestClient, db_mock: AsyncMock):
        resp = client.post(
            ENDPOINT,
            json={"event_day_id": EVENT_DAY, "phase_id": PHASE},
        )
        assert resp.status_code == 401

    def test_404_event_day_not_found(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        missing = MagicMock()
        missing.scalar_one_or_none.return_value = None
        db_mock.execute.return_value = missing

        resp = client.post(
            ENDPOINT,
            json={"event_day_id": EVENT_DAY, "phase_id": PHASE},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_404_phase_not_found(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        found = MagicMock()
        found.scalar_one_or_none.return_value = object()
        missing = MagicMock()
        missing.scalar_one_or_none.return_value = None
        db_mock.execute.side_effect = [found, missing]

        resp = client.post(
            ENDPOINT,
            json={"event_day_id": EVENT_DAY, "phase_id": PHASE},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_404_invalid_phase_uuid(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        found = MagicMock()
        found.scalar_one_or_none.return_value = object()
        db_mock.execute.return_value = found

        resp = client.post(
            ENDPOINT,
            json={"event_day_id": EVENT_DAY, "phase_id": "no-es-un-uuid"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_valid_data_no_anomalies_zero_recommendations(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
        _metric_service: AsyncMock,
        _workflow_service: MagicMock,
    ):
        _metric_service.return_value = _results_no_anomalies()

        resp = client.post(
            ENDPOINT,
            json={"event_day_id": EVENT_DAY, "phase_id": PHASE},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["metrics"]) == 4
        assert {m["name"] for m in body["metrics"]} == {
            "density_deviation",
            "incident_frequency",
            "phase_transition_latency",
            "zone_behavior_adherence",
        }
        assert all(m["is_provisional"] is True for m in body["metrics"])
        assert body["anomalies_detected"] == 0
        assert body["anomalies"] == []
        assert body["recommendations_created"] == []
        _workflow_service.create_recommendation.assert_not_awaited()

    def test_anomalies_creates_recommendations(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
        _metric_service: AsyncMock,
        _workflow_service: MagicMock,
    ):
        _metric_service.return_value = _results_with_anomalies()
        _workflow_service.create_recommendation.return_value = _fake_recommendation(
            "density_deviation"
        )

        resp = client.post(
            ENDPOINT,
            json={"event_day_id": EVENT_DAY, "phase_id": PHASE},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["anomalies_detected"] == 1
        assert body["anomalies"][0]["metric_name"] == "density_deviation"
        assert body["anomalies"][0]["severity"] == "high"
        assert body["anomalies"][0]["suggested_action"]
        assert body["anomalies"][0]["is_provisional"] is True
        assert body["metrics"][0]["is_provisional"] is True
        assert len(body["recommendations_created"]) == 1
        rec = body["recommendations_created"][0]
        assert rec["metric_name"] == "density_deviation"
        assert rec["status"] == "pending_review"
        assert rec["id"]
        _workflow_service.create_recommendation.assert_awaited_once()

    def test_blocked_metrics_no_recommendations(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
        _metric_service: AsyncMock,
        _workflow_service: MagicMock,
    ):
        _metric_service.return_value = _results_all_blocked()

        resp = client.post(
            ENDPOINT,
            json={"event_day_id": EVENT_DAY, "phase_id": PHASE},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["anomalies_detected"] == 0
        assert body["recommendations_created"] == []
        for metric in body["metrics"]:
            assert metric["status"] == "BLOCKED"
            assert metric["value"] is None
        _workflow_service.create_recommendation.assert_not_awaited()

    def test_workflow_error_does_not_break_flow(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
        _metric_service: AsyncMock,
        _workflow_service: MagicMock,
    ):
        _metric_service.return_value = _results_two_anomalies()
        second_fake = _fake_recommendation("zone_behavior_adherence")
        _workflow_service.create_recommendation.side_effect = [
            RuntimeError("fallo al persistir"),
            second_fake,
        ]

        resp = client.post(
            ENDPOINT,
            json={"event_day_id": EVENT_DAY, "phase_id": PHASE},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["anomalies_detected"] == 2
        assert body["recommendations_created"] == [
            {
                "id": str(second_fake.id),
                "status": "pending_review",
                "metric_name": "zone_behavior_adherence",
            }
        ]

    def test_500_when_metric_service_fails(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
        _metric_service: AsyncMock,
    ):
        _metric_service.side_effect = RuntimeError("motor caído")

        resp = client.post(
            ENDPOINT,
            json={"event_day_id": EVENT_DAY, "phase_id": PHASE},
            headers=auth_headers,
        )
        assert resp.status_code == 500


class TestAnomalyDetectorUnit:
    def test_enabled_within_thresholds_no_anomaly(self) -> None:
        from src.application.learning.anomaly_detector import AnomalyDetector

        results = _results_no_anomalies()
        assert AnomalyDetector().detect_all(results) == []

    def test_blocked_never_anomaly(self) -> None:
        from src.application.learning.anomaly_detector import AnomalyDetector

        results = _results_all_blocked()
        assert AnomalyDetector().detect_all(results) == []

    def test_density_deviation_over_threshold(self) -> None:
        from src.application.learning.anomaly_detector import AnomalyDetector

        anomaly = AnomalyDetector().detect(
            _metric("density_deviation", "Desviación de Densidad", "ENABLED", 0.45, data_points=4)
        )
        assert anomaly is not None
        assert anomaly.metric_name == "density_deviation"
        assert anomaly.severity == "high"
        assert anomaly.value == 0.45

    def test_adherence_below_threshold(self) -> None:
        from src.application.learning.anomaly_detector import AnomalyDetector

        anomaly = AnomalyDetector().detect(
            _metric("zone_behavior_adherence", "Adherencia a ZoneBehavior", "ENABLED", 0.2, data_points=4)
        )
        assert anomaly is not None
        assert anomaly.metric_name == "zone_behavior_adherence"
        assert anomaly.value == 0.2