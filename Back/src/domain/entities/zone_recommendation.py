from __future__ import annotations

from datetime import datetime
from uuid import UUID


class ZoneRecommendation:
    def __init__(
        self,
        id: UUID,
        event_day_id: str,
        timestamp: datetime,
        zone_id: str,
        recommendation_type: str,
        score: float,
        ranking: int,
        reasoning: list[str],
        is_nearest: bool = False,
        metadata: dict | None = None,
    ) -> None:
        self._id = id
        self._event_day_id = event_day_id
        self._timestamp = timestamp
        self._zone_id = zone_id
        self._recommendation_type = recommendation_type
        self._score = score
        self._ranking = ranking
        self._reasoning = list(reasoning)
        self._is_nearest = is_nearest
        self._metadata = dict(metadata) if metadata is not None else None

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def event_day_id(self) -> str:
        return self._event_day_id

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def zone_id(self) -> str:
        return self._zone_id

    @property
    def recommendation_type(self) -> str:
        return self._recommendation_type

    @property
    def score(self) -> float:
        return self._score

    @property
    def ranking(self) -> int:
        return self._ranking

    @property
    def reasoning(self) -> list[str]:
        return list(self._reasoning)

    @property
    def is_nearest(self) -> bool:
        return self._is_nearest

    @property
    def metadata(self) -> dict | None:
        return dict(self._metadata) if self._metadata is not None else None

    def __repr__(self) -> str:
        return (
            f"ZoneRecommendation("
            f"id={self._id!r}, "
            f"zone_id={self._zone_id!r}, "
            f"recommendation_type={self._recommendation_type!r}, "
            f"score={self._score!r}, "
            f"ranking={self._ranking!r}, "
            f"timestamp={self._timestamp!r})"
        )