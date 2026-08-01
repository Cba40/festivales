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
    SEEK_HYDRATION = "SEEK_HYDRATION"
    SEEK_HEALTH = "SEEK_HEALTH"


# Clasificación Operativa canónica (P3.0 §11.5): ActionType → (type, subtipo).
# type ∈ {estacionamiento, comida, servicios, transporte, hospedaje, salida, emergencia}
# subtipo ∈ {banos, hidratacion, descanso, salud} — solo cuando type == "servicios".
OPERATIONAL_CLASSIFICATION_BY_ACTION: dict[ActionType, tuple[str | None, str | None]] = {
    ActionType.SEEK_PARKING: ("estacionamiento", None),
    ActionType.SEEK_FOOD: ("comida", None),
    ActionType.SEEK_TRANSPORT: ("transporte", None),
    ActionType.SEEK_ACCOMMODATION: ("hospedaje", None),
    ActionType.SEEK_EXIT: ("salida", None),
    ActionType.SEEK_SECURITY: ("emergencia", None),
    ActionType.SEEK_BATHROOM: ("servicios", "banos"),
    ActionType.SEEK_HYDRATION: ("servicios", "hidratacion"),
    ActionType.SEEK_REST: ("servicios", "descanso"),
    ActionType.SEEK_HEALTH: ("servicios", "salud"),
    ActionType.SEEK_INFORMATION: (None, None),
    ActionType.SEEK_LOW_DENSITY: (None, None),
    ActionType.SEEK_SERVICE: (None, None),
}


class RequestedAction:
    def __init__(
        self,
        action_type: ActionType,
    ) -> None:
        self._action_type = action_type
        self._type, self._subtipo = OPERATIONAL_CLASSIFICATION_BY_ACTION.get(
            action_type, (None, None)
        )

    @property
    def action_type(self) -> ActionType:
        return self._action_type

    @property
    def type(self) -> str | None:
        return self._type

    @property
    def subtipo(self) -> str | None:
        return self._subtipo

    @property
    def zone_type(self) -> str | None:
        # Compatibilidad de lectura con adapters REST; expone la clasificación
        # operativa `type`. No constituye el mapping legacy.
        return self._type

    def __repr__(self) -> str:
        return (
            f"RequestedAction(action_type={self._action_type!r}, "
            f"type={self._type!r}, subtipo={self._subtipo!r})"
        )
