from __future__ import annotations

from enum import Enum


class ActionType(Enum):
    SEEK_PARKING = "SEEK_PARKING"
    SEEK_FOOD = "SEEK_FOOD"
    SEEK_BATHROOM = "SEEK_BATHROOM"
    SEEK_TRANSPORT = "SEEK_TRANSPORT"
    SEEK_ACCOMMODATION = "SEEK_ACCOMMODATION"
    SEEK_EXIT = "SEEK_EXIT"
    SEEK_REST = "SEEK_REST"
    SEEK_SECURITY = "SEEK_SECURITY"
    SEEK_INFORMATION = "SEEK_INFORMATION"
    SEEK_LOW_DENSITY = "SEEK_LOW_DENSITY"
    SEEK_SERVICE = "SEEK_SERVICE"


ZONE_TYPE_BY_ACTION: dict[ActionType, str | None] = {
    ActionType.SEEK_PARKING: "Parking",
    ActionType.SEEK_FOOD: "Gastronomy",
    ActionType.SEEK_BATHROOM: "Sanitary",
    ActionType.SEEK_TRANSPORT: "Transport",
    ActionType.SEEK_ACCOMMODATION: "Accommodation",
    ActionType.SEEK_EXIT: "Transport",
    ActionType.SEEK_REST: "RestArea",
    ActionType.SEEK_SECURITY: "Security",
    ActionType.SEEK_INFORMATION: "Information",
    ActionType.SEEK_LOW_DENSITY: None,
    ActionType.SEEK_SERVICE: None,
}


class RequestedAction:
    def __init__(
        self,
        action_type: ActionType,
        zone_type: str | None = None,
    ) -> None:
        self._action_type = action_type
        self._zone_type = zone_type if zone_type is not None else ZONE_TYPE_BY_ACTION.get(action_type)

    @property
    def action_type(self) -> ActionType:
        return self._action_type

    @property
    def zone_type(self) -> str | None:
        return self._zone_type

    def __repr__(self) -> str:
        return (
            f"RequestedAction(action_type={self._action_type!r}, "
            f"zone_type={self._zone_type!r})"
        )
