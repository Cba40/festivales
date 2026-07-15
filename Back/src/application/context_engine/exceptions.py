class ContextEngineError(Exception):
    pass


class DomainNotConfigured(ContextEngineError):
    def __init__(self, message: str = "No EventDay configured for the given timestamp") -> None:
        super().__init__(f"DOMAIN_NOT_CONFIGURED: {message}")


class InvalidPhaseContext(ContextEngineError):
    def __init__(self, message: str = "No active EventDayPhase for the evaluated instant") -> None:
        super().__init__(f"INVALID_PHASE_CONTEXT: {message}")


class BehaviorNotDefined(ContextEngineError):
    def __init__(self, zone_type_id: object, phase_id: object) -> None:
        super().__init__(
            f"BEHAVIOR_NOT_DEFINED: No ZoneBehavior for zone_type_id={zone_type_id} "
            f"and operational_phase_id={phase_id}"
        )


class InvalidRuntimeContext(ContextEngineError):
    def __init__(self, message: str = "RuntimeContext is invalid or missing required fields") -> None:
        super().__init__(f"INVALID_RUNTIME_CONTEXT: {message}")


class InvalidConfiguration(ContextEngineError):
    def __init__(self, message: str = "Knowledge Model contains inconsistent or incomplete data") -> None:
        super().__init__(f"INVALID_CONFIGURATION: {message}")
