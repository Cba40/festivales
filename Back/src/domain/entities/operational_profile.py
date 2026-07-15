from uuid import UUID, uuid4

from src.domain.entities.operational_phase import OperationalPhase


class OperationalProfile:
    def __init__(
        self,
        name: str,
        phases: tuple[OperationalPhase, ...],
        id: UUID | None = None,
    ) -> None:
        resolved_id = id if id is not None else uuid4()
        self._validate(resolved_id, name, phases)
        self._id = resolved_id
        self._name = name.strip()
        self._phases = phases

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def phases(self) -> tuple[OperationalPhase, ...]:
        return self._phases

    @staticmethod
    def _validate(id: UUID, name: str, phases: tuple[OperationalPhase, ...]) -> None:
        if not isinstance(id, UUID):
            raise TypeError("id must be a UUID")
        if not name or not name.strip():
            raise ValueError("name must not be empty")
        if len(name) > 100:
            raise ValueError("name must not exceed 100 characters")
        if not isinstance(phases, tuple) or len(phases) == 0:
            raise ValueError("operational_profile must contain at least one phase")
        seen_orders: set[int] = set()
        previous_order: int | None = None
        for phase in phases:
            if not isinstance(phase, OperationalPhase):
                raise TypeError("each phase must be an OperationalPhase instance")
            order = phase.sequence_order
            if order in seen_orders:
                raise ValueError(
                    f"duplicate sequence_order {order} in operational_profile phases"
                )
            seen_orders.add(order)
            if previous_order is not None and order <= previous_order:
                raise ValueError(
                    "phases must be ordered by ascending sequence_order"
                )
            previous_order = order

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OperationalProfile):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return (
            f"OperationalProfile(id={self._id!r}, name={self._name!r}, "
            f"phases_count={len(self._phases)})"
        )
