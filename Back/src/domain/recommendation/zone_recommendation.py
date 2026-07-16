from __future__ import annotations

from uuid import UUID


class ZoneRecommendation:
    def __init__(
        self,
        zone_id: UUID,
        score: float,
        reasoning: list[str],
    ) -> None:
        self._zone_id = zone_id
        self._score = score
        self._reasoning = list(reasoning)

    @property
    def zone_id(self) -> UUID:
        return self._zone_id

    @property
    def score(self) -> float:
        return self._score

    @property
    def reasoning(self) -> list[str]:
        return list(self._reasoning)

    def __repr__(self) -> str:
        return (
            f"ZoneRecommendation("
            f"zone_id={self._zone_id!r}, "
            f"score={self._score!r}, "
            f"reasoning={self._reasoning!r})"
        )
