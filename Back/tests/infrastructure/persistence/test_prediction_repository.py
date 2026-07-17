from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from src.domain.entities.zone_behavior import FlowRestriction
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState
from src.infrastructure.persistence.models import PredictionModel
from src.infrastructure.persistence.repositories import SQLPredictionRepository

A_UUID = UUID("11111111-1111-1111-1111-111111111111")
B_UUID = UUID("22222222-2222-2222-2222-222222222222")
C_UUID = UUID("33333333-3333-3333-3333-333333333333")


def _make_prediction(
    timestamp: datetime | None = None,
) -> TerritorialPrediction:
    zone_states = [
        ZoneState(
            zone_id=A_UUID,
            operational_state="NORMAL",
            availability=1000,
            saturation_level=0.3,
            estimated_wait=5,
            confidence=0.9,
            reasoning_factors=["factor1"],
            active_restriction=FlowRestriction.OPEN,
        ),
        ZoneState(
            zone_id=B_UUID,
            operational_state="REGULATED",
            availability=500,
            saturation_level=0.7,
            estimated_wait=15,
            confidence=0.7,
            reasoning_factors=["factor2"],
            active_restriction=FlowRestriction.REGULATED,
        ),
    ]
    return TerritorialPrediction(
        timestamp=timestamp or datetime(2026, 7, 10, 10, 0, 0),
        zone_states=zone_states,
        active_phase_id=C_UUID,
        active_event_day_phase_id=A_UUID,
    )


def _make_prediction_model(
    timestamp: datetime | None = None,
) -> PredictionModel:
    model = PredictionModel(
        id=uuid4(),
        timestamp=timestamp or datetime(2026, 7, 10, 10, 0, 0),
        active_phase_id=C_UUID,
        active_event_day_phase_id=A_UUID,
        zone_states_data=[
            {
                "zone_id": str(A_UUID),
                "operational_state": "NORMAL",
                "availability": 1000,
                "saturation_level": 0.3,
                "estimated_wait": 5,
                "confidence": 0.9,
                "reasoning_factors": ["factor1"],
                "active_restriction": "OPEN",
            },
            {
                "zone_id": str(B_UUID),
                "operational_state": "REGULATED",
                "availability": 500,
                "saturation_level": 0.7,
                "estimated_wait": 15,
                "confidence": 0.7,
                "reasoning_factors": ["factor2"],
                "active_restriction": "REGULATED",
            },
        ],
    )
    return model


class TestSQLPredictionRepositorySave:
    async def test_save_creates_new_prediction(self) -> None:
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        prediction = _make_prediction()
        repo = SQLPredictionRepository(session)

        result = await repo.save(prediction)

        assert result.timestamp == prediction.timestamp
        assert len(result.zone_states) == 2
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    async def test_save_returns_domain_entity(self) -> None:
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        prediction = _make_prediction()
        repo = SQLPredictionRepository(session)

        result = await repo.save(prediction)

        assert isinstance(result, TerritorialPrediction)
        assert isinstance(result.zone_states[0], ZoneState)

    async def test_save_never_calls_commit(self) -> None:
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        prediction = _make_prediction()
        repo = SQLPredictionRepository(session)

        await repo.save(prediction)

        session.commit.assert_not_called()

    async def test_save_never_calls_rollback(self) -> None:
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        prediction = _make_prediction()
        repo = SQLPredictionRepository(session)

        await repo.save(prediction)

        session.rollback.assert_not_called()


class TestSQLPredictionRepositoryFind:
    async def test_find_by_timestamp_returns_prediction(self) -> None:
        session = AsyncMock()
        model = _make_prediction_model()

        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=model)
        session.execute = AsyncMock(return_value=scalar_result)

        repo = SQLPredictionRepository(session)

        result = await repo.find_by_timestamp(
            datetime(2026, 7, 10, 10, 0, 0)
        )

        assert result is not None
        assert isinstance(result, TerritorialPrediction)
        assert result.timestamp == datetime(2026, 7, 10, 10, 0, 0)
        assert len(result.zone_states) == 2
        assert result.active_phase_id == C_UUID

    async def test_find_by_timestamp_returns_none_when_not_found(
        self,
    ) -> None:
        session = AsyncMock()
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=scalar_result)

        repo = SQLPredictionRepository(session)

        result = await repo.find_by_timestamp(
            datetime(2026, 7, 11, 10, 0, 0)
        )

        assert result is None

    async def test_find_by_timestamp_uses_correct_filter(self) -> None:
        session = AsyncMock()
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=scalar_result)

        repo = SQLPredictionRepository(session)

        ts = datetime(2026, 7, 10, 10, 0, 0)
        await repo.find_by_timestamp(ts)

        call_args = session.execute.call_args[0][0]
        compiled = str(call_args.compile(compile_kwargs={"literal_binds": True}))
        assert "predictions" in compiled
        assert "2026-07-10 10:00:00" in compiled

    async def test_find_by_timestamp_uses_async_session_injected(
        self,
    ) -> None:
        session = AsyncMock()
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=scalar_result)

        repo = SQLPredictionRepository(session)

        await repo.find_by_timestamp(datetime(2026, 7, 10, 10, 0, 0))

        session.execute.assert_awaited_once()

    def test_implements_prediction_repository_port(self) -> None:
        from src.domain.ports.prediction_repository import PredictionRepository

        assert PredictionRepository.__name__ in [
            b.__name__ for b in SQLPredictionRepository.__mro__
        ], "SQLPredictionRepository does not inherit from PredictionRepository"
        assert hasattr(SQLPredictionRepository, "save")
        assert hasattr(SQLPredictionRepository, "find_by_timestamp")
