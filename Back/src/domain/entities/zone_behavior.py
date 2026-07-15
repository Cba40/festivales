from enum import Enum
from uuid import UUID, uuid4


class FlowRestriction(Enum):
    OPEN = "OPEN"
    REGULATED = "REGULATED"
    CLOSED = "CLOSED"


class ZoneBehavior:
    def __init__(
        self,
        zone_type_id: UUID,
        operational_phase_id: UUID,
        density_factor: float,
        flow_restriction: FlowRestriction,
        id: UUID | None = None,
    ) -> None:
        resolved_id = id if id is not None else uuid4()
        self._validate(resolved_id, zone_type_id, operational_phase_id, density_factor, flow_restriction)
        self._id = resolved_id
        self._zone_type_id = zone_type_id
        self._operational_phase_id = operational_phase_id
        self._density_factor = density_factor
        self._flow_restriction = flow_restriction

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def zone_type_id(self) -> UUID:
        return self._zone_type_id

    @property
    def operational_phase_id(self) -> UUID:
        return self._operational_phase_id

    @property
    def density_factor(self) -> float:
        return self._density_factor

    @property
    def flow_restriction(self) -> FlowRestriction:
        return self._flow_restriction

    @staticmethod
    def _validate(
        id: UUID,
        zone_type_id: UUID,
        operational_phase_id: UUID,
        density_factor: float,
        flow_restriction: FlowRestriction,
    ) -> None:
        if not isinstance(id, UUID):
            raise TypeError("id must be a UUID")
        if not isinstance(zone_type_id, UUID):
            raise TypeError("zone_type_id must be a UUID")
        if not isinstance(operational_phase_id, UUID):
            raise TypeError("operational_phase_id must be a UUID")
        if not isinstance(density_factor, (int, float)) or isinstance(density_factor, bool):
            raise TypeError("density_factor must be a number")
        if density_factor < 0.0 or density_factor > 1.0:
            raise ValueError("density_factor must be between 0.0 and 1.0")
        if not isinstance(flow_restriction, FlowRestriction):
            raise TypeError("flow_restriction must be a FlowRestriction enum member")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ZoneBehavior):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return (
            f"ZoneBehavior(id={self._id!r}, zone_type_id={self._zone_type_id!r}, "
            f"operational_phase_id={self._operational_phase_id!r}, "
            f"density_factor={self._density_factor!r}, "
            f"flow_restriction={self._flow_restriction!r})"
        )
