from __future__ import annotations

from datetime import datetime
from uuid import UUID


class KnowledgeModelVersion:
    """Snapshot inmutable del Knowledge Model en un momento dado.

    RFC-006 §9: Toda TerritorialPrediction histórica DEBE mantener una referencia
    inmutable a la versión exacta del Knowledge Model utilizada para su cálculo,
    permitiendo reproducibilidad analítica futura.
    """

    def __init__(
        self,
        id: UUID,
        version_number: int,
        snapshot_data: dict,
        created_at: datetime,
        created_by: UUID | None = None,
    ) -> None:
        self._id = id
        self._version_number = version_number
        self._snapshot_data = snapshot_data
        self._created_at = created_at
        self._created_by = created_by

    # Properties readonly (inmutables)

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def version_number(self) -> int:
        return self._version_number

    @property
    def snapshot_data(self) -> dict:
        return self._snapshot_data

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def created_by(self) -> UUID | None:
        return self._created_by

    def __repr__(self) -> str:
        return (
            f"KnowledgeModelVersion("
            f"id={self._id!r}, "
            f"version_number={self._version_number!r}, "
            f"created_at={self._created_at!r}, "
            f"created_by={self._created_by!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, KnowledgeModelVersion):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)