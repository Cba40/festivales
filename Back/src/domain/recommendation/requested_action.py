from __future__ import annotations

from enum import Enum


class ActionType(Enum):
    SEEK_LOW_DENSITY = "SEEK_LOW_DENSITY"
    SEEK_EXIT = "SEEK_EXIT"
    SEEK_SERVICE = "SEEK_SERVICE"


class RequestedAction:
    def __init__(
        self,
        action_type: ActionType,
    ) -> None:
        self._action_type = action_type

    @property
    def action_type(self) -> ActionType:
        return self._action_type

    def __repr__(self) -> str:
        return f"RequestedAction(action_type={self._action_type!r})"
