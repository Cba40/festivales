from __future__ import annotations

from datetime import date
from uuid import UUID

from src.application.context_engine.exceptions import InvalidConfiguration
from src.domain.entities.event_day import EventDay
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.ports import EventDayRepository, OperationalProfileRepository


class CreateEventDay:
    def __init__(
        self,
        event_day_repo: EventDayRepository,
        operational_profile_repo: OperationalProfileRepository,
    ) -> None:
        self._event_day_repo = event_day_repo
        self._operational_profile_repo = operational_profile_repo

    async def execute(
        self,
        event_date: date,
        operational_profile_id: UUID,
        attendance_level_id: UUID,
        operational_start_min: int,
        operational_end_min: int,
        phases: tuple[EventDayPhase, ...],
    ) -> EventDay:
        profile = await self._operational_profile_repo.find_by_id(
            operational_profile_id,
        )
        if profile is None:
            raise InvalidConfiguration(
                f"OperationalProfile {operational_profile_id} not found"
            )

        self._validate_no_overlap(phases)
        self._validate_full_coverage(
            phases,
            operational_start_min,
            operational_end_min,
        )
        self._validate_phase_order(phases, profile)

        event_day = EventDay(
            event_date=event_date,
            operational_profile_id=operational_profile_id,
            attendance_level_id=attendance_level_id,
            operational_start_min=operational_start_min,
            operational_end_min=operational_end_min,
            phases=phases,
        )

        return await self._event_day_repo.save(event_day)

    @staticmethod
    def _validate_no_overlap(phases: tuple[EventDayPhase, ...]) -> None:
        sorted_phases = sorted(phases, key=lambda p: p.start_min)
        for i in range(len(sorted_phases) - 1):
            current = sorted_phases[i]
            next_phase = sorted_phases[i + 1]
            if next_phase.start_min < current.end_min:
                raise InvalidConfiguration(
                    f"EventDayPhase {next_phase.id} overlaps with "
                    f"EventDayPhase {current.id}: "
                    f"{next_phase.start_min} < {current.end_min}"
                )

    @staticmethod
    def _validate_full_coverage(
        phases: tuple[EventDayPhase, ...],
        operational_start_min: int,
        operational_end_min: int,
    ) -> None:
        sorted_phases = sorted(phases, key=lambda p: p.start_min)
        expected_start = operational_start_min
        for phase in sorted_phases:
            if phase.start_min != expected_start:
                raise InvalidConfiguration(
                    f"Coverage gap before EventDayPhase {phase.id}: "
                    f"expected start {expected_start}, got {phase.start_min}"
                )
            expected_start = phase.end_min
        if expected_start != operational_end_min:
            raise InvalidConfiguration(
                f"Coverage gap after last phase: "
                f"expected end {operational_end_min}, "
                f"last phase ends at {expected_start}"
            )

    @staticmethod
    def _validate_phase_order(
        phases: tuple[EventDayPhase, ...],
        profile: object,
    ) -> None:
        profile_phase_ids = [p.id for p in profile.phases]
        sorted_phases = sorted(phases, key=lambda p: p.start_min)
        for i, phase in enumerate(sorted_phases):
            if i >= len(profile_phase_ids):
                raise InvalidConfiguration(
                    f"EventDayPhase {phase.id} references "
                    f"operational_phase_id {phase.operational_phase_id} "
                    f"but profile has only {len(profile_phase_ids)} phases"
                )
            expected_id = profile_phase_ids[i]
            if phase.operational_phase_id != expected_id:
                raise InvalidConfiguration(
                    f"EventDayPhase {phase.id} has "
                    f"operational_phase_id {phase.operational_phase_id}, "
                    f"expected {expected_id} at position {i}"
                )
