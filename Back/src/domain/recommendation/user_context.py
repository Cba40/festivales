from __future__ import annotations

from enum import Enum
from uuid import UUID


class AccessLevel(Enum):
    STANDARD = "STANDARD"
    VIP = "VIP"
    STAFF = "STAFF"


class UserContext:
    def __init__(
        self,
        user_id: UUID,
        access_level: AccessLevel,
    ) -> None:
        self._user_id = user_id
        self._access_level = access_level

    @property
    def user_id(self) -> UUID:
        return self._user_id

    @property
    def access_level(self) -> AccessLevel:
        return self._access_level

    def __repr__(self) -> str:
        return (
            f"UserContext("
            f"user_id={self._user_id!r}, "
            f"access_level={self._access_level!r})"
        )
