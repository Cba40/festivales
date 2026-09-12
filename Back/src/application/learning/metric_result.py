from dataclasses import dataclass


@dataclass
class MetricResult:
    name: str
    display_name: str
    status: str
    value: float | None
    reason: str
    data_points: int
    limitations: list[str]