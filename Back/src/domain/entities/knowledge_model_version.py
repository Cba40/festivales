from __future__ import annotations

from datetime import datetime
from uuid import UUID


class KnowledgeModelVersion:
    def __init__(
        self,
        id: UUID,
        version_number: int,
        snapshot_data: dict,
        created_at: datetime,
        created_by: str | None = None,
    ) -> None:
        self._id = id
        self._version_number = version_number
        self._snapshot_data = snapshot_data
        self._created_at = created_at
        self._created_by = created_by

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
    def created_by(self) -> str | None:
        return self._created_by

    def __repr__(self) -> str:
        return (
            f"KnowledgeModelVersion("
            f"id={self._id!r}, "
            f"version_number={self._version_number!r}, "
            f"created_at={self._created_at!r}, "
            f"created_by={self._created_by!r})"
        )