from uuid import UUID

import pytest

from src.application.context_engine.context_engine import ContextEngine
from src.application.context_engine.exceptions import (
    BehaviorNotDefined,
    ContextEngineError,
    DomainNotConfigured,
    InvalidConfiguration,
    InvalidPhaseContext,
    InvalidRuntimeContext,
)
from src.domain.ports import (
    EventDayRepository,
    ZoneBehaviorRepository,
)


class TestContextEngineCreation:
    def test_can_instantiate(self) -> None:
        engine = ContextEngine()
        assert isinstance(engine, ContextEngine)

    def test_predict_method_exists(self) -> None:
        engine = ContextEngine()
        assert hasattr(engine, "predict")
        assert callable(engine.predict)


class TestContextEngineExceptions:
    def test_context_engine_error_is_exception(self) -> None:
        assert issubclass(ContextEngineError, Exception)

    def test_domain_not_configured(self) -> None:
        err = DomainNotConfigured()
        assert "DOMAIN_NOT_CONFIGURED" in str(err)

    def test_invalid_phase_context(self) -> None:
        err = InvalidPhaseContext()
        assert "INVALID_PHASE_CONTEXT" in str(err)

    def test_behavior_not_defined(self) -> None:
        err = BehaviorNotDefined(
            UUID("00000000-0000-0000-0000-000000000001"),
            UUID("00000000-0000-0000-0000-000000000002"),
        )
        assert "BEHAVIOR_NOT_DEFINED" in str(err)

    def test_invalid_runtime_context(self) -> None:
        err = InvalidRuntimeContext()
        assert "INVALID_RUNTIME_CONTEXT" in str(err)

    def test_invalid_configuration(self) -> None:
        err = InvalidConfiguration()
        assert "INVALID_CONFIGURATION" in str(err)

    def test_all_errors_inherit_base(self) -> None:
        assert issubclass(DomainNotConfigured, ContextEngineError)
        assert issubclass(InvalidPhaseContext, ContextEngineError)
        assert issubclass(BehaviorNotDefined, ContextEngineError)
        assert issubclass(InvalidRuntimeContext, ContextEngineError)
        assert issubclass(InvalidConfiguration, ContextEngineError)


class TestInterfaces:
    def test_event_day_repository_protocol(self) -> None:
        assert hasattr(EventDayRepository, "find_by_date")

    def test_zone_behavior_repository_protocol(self) -> None:
        assert hasattr(ZoneBehaviorRepository, "find_by_zone_type_and_phase")



