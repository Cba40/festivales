"""P3.1B — Sincronización automática e idempotente de ZoneBehavior.

Garantiza la invariante: toda OperationalPhase posee un ZoneBehavior por cada
ZoneType existente. Nunca modifica los ZoneBehavior ya existentes y nunca crea
duplicados.

La función central `sync_zone_behaviors` acepta una sesión síncrona de
SQLAlchemy y puede ejecutarse:
  - tras crear una OperationalPhase (phase_ids=[nueva_fase])
  - tras crear un ZoneType (zone_type_ids=[nuevo_tipo])
  - sobre toda la base existente (sin argumentos)
"""
from collections.abc import Iterable
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.operational_phase import OperationalPhase
from app.models.zone_behavior import ZoneBehavior
from app.models.zone_type import ZoneType

# Valores por defecto coherentes con los defaults del modelo y del schema
# (flujo "OPEN", densidad 0.5 y factores neutros 1.0, como en §11 / seeds).
DEFAULT_SATURATION_FACTOR = Decimal("1.0")
DEFAULT_AVAILABILITY_FACTOR = Decimal("1.0")
DEFAULT_RESOURCE_FACTOR = Decimal("1.0")
DEFAULT_PRIORITY_WEIGHT = Decimal("1.0")
DEFAULT_DENSITY_FACTOR = 0.5
DEFAULT_FLOW_RESTRICTION = "OPEN"


def default_behavior(phase_id: UUID, zone_type_id: str) -> ZoneBehavior:
    """Construye un ZoneBehavior con valores por defecto para (phase, zone_type)."""
    return ZoneBehavior(
        operational_phase_id=phase_id,
        zone_type_id=zone_type_id,
        saturation_factor=DEFAULT_SATURATION_FACTOR,
        availability_factor=DEFAULT_AVAILABILITY_FACTOR,
        resource_factor=DEFAULT_RESOURCE_FACTOR,
        priority_weight=DEFAULT_PRIORITY_WEIGHT,
        density_factor=DEFAULT_DENSITY_FACTOR,
        flow_restriction=DEFAULT_FLOW_RESTRICTION,
    )


def _existing_combos(session: Session) -> set[tuple[UUID, str]]:
    rows = session.execute(
        select(ZoneBehavior.operational_phase_id, ZoneBehavior.zone_type_id)
    ).all()
    return {(row[0], row[1]) for row in rows}


def sync_zone_behaviors(
    session: Session,
    *,
    phase_ids: Iterable[UUID] | None = None,
    zone_type_ids: Iterable[str] | None = None,
) -> int:
    """Crea los ZoneBehavior faltantes para cada combinación (phase, zone_type).

    - Idempotente: si una combinación ya existe, NO la modifica ni la reemplaza.
    - No crea duplicados: usa (operational_phase_id, zone_type_id) como criterio.
    - Retorna la cantidad de ZoneBehavior creados.
    """
    if phase_ids is None:
        phase_ids = list(session.execute(select(OperationalPhase.id)).scalars().all())
    else:
        phase_ids = list(phase_ids)

    if zone_type_ids is None:
        zone_type_ids = list(session.execute(select(ZoneType.id)).scalars().all())
    else:
        zone_type_ids = list(zone_type_ids)

    if not phase_ids or not zone_type_ids:
        return 0

    existing = _existing_combos(session)
    created = 0
    for phase_id in phase_ids:
        for zone_type_id in zone_type_ids:
            if (phase_id, zone_type_id) in existing:
                continue
            session.add(default_behavior(phase_id, zone_type_id))
            created += 1

    if created:
        session.flush()
    return created


def sync_zone_behaviors_for_phase(session: Session, phase_id: UUID) -> int:
    """Completa los ZoneBehavior faltantes de una OperationalPhase."""
    return sync_zone_behaviors(session, phase_ids=[phase_id])


def sync_zone_behaviors_for_zone_type(session: Session, zone_type_id: str) -> int:
    """Completa los ZoneBehavior faltantes de un ZoneType."""
    return sync_zone_behaviors(session, zone_type_ids=[zone_type_id])


def sync_all_zone_behaviors(session: Session) -> int:
    """Sincroniza la matriz completa fase × zone_type de la base existente."""
    return sync_zone_behaviors(session)
