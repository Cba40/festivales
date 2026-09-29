"""CRUD operations for OperationalObservation (RFC-006)."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_day import EventDay
from app.models.zone import Zone
from app.schemas.operational_observation import (
    OperationalObservationCreate,
    OperationalObservationResponse,
    OperationalObservationUpdate,
)
from src.infrastructure.persistence.models import OperationalObservationModel

LOCAL_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

# ── Protocolo de muestreo ────────────────────────────────────────────────────
# Son conteos manuales, la lectura de una persona que camina hasta la zona.
# Estos umbrales existen para separar "la realidad cambió" de "se tipeó mal".
VARIATION_THRESHOLD_PCT = 200.0
CAPACITY_MULTIPLE_THRESHOLD = 3
MIN_INTERVAL_MINUTES = 15

WARNING_VARIATION = "variacion_extrema"
WARNING_TYPO = "posible_error_tipeo"

# Claves de `metadata` que escribe el sistema, no el operador. Se separan de las
# que sí edita el operador (notas, etc.) para que un PATCH de `metadata` nunca
# pueda dejar un warning viejo pegado, ni inventarse uno.
COMPUTED_METADATA_KEYS = frozenset(
    {
        "warnings",
        "variacion_pct",
        "densidad_anterior",
        "capacidad",
        "densidad_observada",
    }
)

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _is_valid_uuid(value: str) -> bool:
    return bool(_UUID_RE.match(value.strip()))


async def _find_observation_window(
    db: AsyncSession,
    *,
    zone_id: str,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 1,
    exclude_id: UUID | None = None,
) -> list[OperationalObservationModel]:
    """Observaciones de una zona dentro de una ventana temporal, más reciente primero."""
    conditions = [OperationalObservationModel.zone_id == zone_id]
    if since is not None:
        conditions.append(OperationalObservationModel.timestamp >= since)
    if until is not None:
        conditions.append(OperationalObservationModel.timestamp <= until)
    if exclude_id is not None:
        # En la corrección la fila editada cae dentro de su propia ventana
        # (`until == su timestamp`), así que sin esto "la observación previa"
        # sería la propia fila y toda variación daría 0%.
        conditions.append(OperationalObservationModel.id != exclude_id)
    result = await db.execute(
        select(OperationalObservationModel)
        .where(*conditions)
        .order_by(desc(OperationalObservationModel.timestamp))
        .limit(limit)
    )
    return list(result.scalars().all())


def _evaluate_quality(
    *,
    new_density: int,
    capacity: int,
    previous_density: int | None,
) -> dict:
    """Decide los warnings a partir de números. Función pura, sin I/O.

    Se separa del acceso a datos a propósito: los umbrales y sus bordes son la
    parte con reglas de negocio, y así se pueden testear sin base.

    Devuelve el diccionario a mergear en ``metadata`` (puede ir vacío).
    """
    metadata: dict = {}
    warnings: list[str] = []

    # Variación extrema contra la observación anterior. Con densidad previa 0 la
    # variación sería infinita, así que no se marca: 0 suele significar "no
    # había nadie" o "no se contó", no un salto real.
    if previous_density is not None and previous_density > 0:
        variacion = abs(new_density - previous_density) / previous_density * 100
        if variacion > VARIATION_THRESHOLD_PCT:
            warnings.append(WARNING_VARIATION)
            metadata["variacion_pct"] = round(variacion, 1)
            metadata["densidad_anterior"] = previous_density

    # Densidad 3x la capacidad declarada: casi siempre error de tipeo.
    # capacity <= 0 significa "capacidad no declarada": no se puede afirmar nada.
    if capacity > 0 and new_density > capacity * CAPACITY_MULTIPLE_THRESHOLD:
        warnings.append(WARNING_TYPO)
        metadata["capacidad"] = capacity
        metadata["densidad_observada"] = new_density

    if warnings:
        metadata["warnings"] = warnings
    return metadata


async def _collect_quality_warnings(
    db: AsyncSession,
    *,
    zone: Zone,
    new_density: int,
    new_timestamp: datetime,
    exclude_id: UUID | None = None,
) -> dict:
    """Warnings de calidad del muestreo. Nunca rechazan: solo informan.

    Se acumulan en ``metadata`` para que el Censo Operativo pueda marcar la
    observación en lugar de descartarla: un conteo dudoso sigue siendo mejor
    que un hueco, siempre que quede marcado.
    """
    # La referencia se acota con `until=new_timestamp` para que, al cargar una
    # observación retroactiva, sea una observación previa y no una futura.
    previous = await _find_observation_window(
        db, zone_id=zone.id, until=new_timestamp, limit=1, exclude_id=exclude_id
    )
    return _evaluate_quality(
        new_density=new_density,
        capacity=zone.capacity,
        previous_density=previous[0].observed_density if previous else None,
    )


def _to_current_min(event_date: date, timestamp: datetime) -> int:
    local_ts = timestamp.astimezone(LOCAL_TZ)
    days_diff = (local_ts.date() - event_date).days
    return days_diff * 1440 + local_ts.hour * 60 + local_ts.minute


def _is_within_event_day(event_day: EventDay, timestamp: datetime) -> bool:
    current_min = _to_current_min(event_day.date, timestamp)
    return event_day.operational_start_min <= current_min < event_day.operational_end_min


def _to_response(model: OperationalObservationModel) -> OperationalObservationResponse:
    return OperationalObservationResponse(
        id=str(model.id),
        event_day_id=model.event_day_id,
        zone_id=model.zone_id,
        timestamp=model.timestamp,
        observed_density=model.observed_density,
        observer_id=model.observer_id,
        source=model.source,
        metadata=model.metadata_,
        created_at=model.created_at,
        corrected_by=model.corrected_by,
        corrected_at=model.corrected_at,
    )


async def create_observation(
    db: AsyncSession,
    observation_in: OperationalObservationCreate,
) -> OperationalObservationResponse:
    event_day = await db.get(EventDay, observation_in.event_day_id)
    if not event_day:
        raise ValueError(f"EventDay with id '{observation_in.event_day_id}' not found")

    zone = await db.get(Zone, observation_in.zone_id)
    if not zone:
        raise ValueError(f"Zone with id '{observation_in.zone_id}' not found")

    timestamp = observation_in.timestamp
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")

    if not _is_within_event_day(event_day, timestamp):
        raise ValueError(
            f"timestamp {timestamp.isoformat()} is outside the operational range "
            f"of EventDay '{observation_in.event_day_id}'"
        )

    # 1) El observador tiene que identificarse. Se acepta un UUID o nada: sin
    #    observer_id el registro sigue siendo válido, pero con uno inválido no
    #    se puede atribuir el conteo a nadie.
    if observation_in.observer_id is not None and not _is_valid_uuid(
        observation_in.observer_id
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "observer_id inválido: debe ser un UUID de 36 caracteres "
                "o dejarse en blanco"
            ),
        )

    # 2) Anti-spam: no se admite dos conteos de la misma zona en la misma
    #    ventana. La ventana se ancla en el timestamp de la observación nueva
    #    (y no en "ahora") para no bloquear la carga retroactiva de un censo
    #    que el operador está completando.
    recent = await _find_observation_window(
        db,
        zone_id=zone.id,
        since=timestamp - timedelta(minutes=MIN_INTERVAL_MINUTES),
    )
    if recent:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Ya existe una observación reciente para esta zona "
                f"(menos de {MIN_INTERVAL_MINUTES} minutos)"
            ),
        )

    # 3) y 4) Warnings de calidad: informan, no rechazan. Se mergean con las
    #    notas que venga del formulario en lugar de reemplazarlas.
    quality = await _collect_quality_warnings(
        db,
        zone=zone,
        new_density=observation_in.observed_density,
        new_timestamp=timestamp,
    )
    metadata = dict(observation_in.metadata or {})
    metadata.update(quality)

    db_obj = OperationalObservationModel(
        event_day_id=observation_in.event_day_id,
        zone_id=observation_in.zone_id,
        timestamp=timestamp,
        observed_density=observation_in.observed_density,
        observer_id=observation_in.observer_id,
        source=observation_in.source,
        metadata_=metadata or None,
    )
    db.add(db_obj)
    await db.flush()
    await db.commit()
    await db.refresh(db_obj)
    return _to_response(db_obj)


async def get_observation(
    db: AsyncSession,
    observation_id: UUID,
) -> OperationalObservationResponse | None:
    model = await db.get(OperationalObservationModel, observation_id)
    if model is None:
        return None
    return _to_response(model)


async def find_all(
    db: AsyncSession,
    event_day_id: str | None = None,
    zone_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[OperationalObservationResponse]:
    stmt = select(OperationalObservationModel)
    if event_day_id is not None:
        stmt = stmt.where(OperationalObservationModel.event_day_id == event_day_id)
    if zone_id is not None:
        stmt = stmt.where(OperationalObservationModel.zone_id == zone_id)
    if start_date is not None:
        stmt = stmt.where(OperationalObservationModel.timestamp >= start_date)
    if end_date is not None:
        stmt = stmt.where(OperationalObservationModel.timestamp <= end_date)
    stmt = stmt.order_by(OperationalObservationModel.timestamp)

    result = await db.execute(stmt)
    models = result.scalars().all()
    return [_to_response(m) for m in models]


async def update_observation(
    db: AsyncSession,
    observation_id: UUID,
    observation_in: OperationalObservationUpdate,
    *,
    corrected_by: str,
) -> OperationalObservationResponse | None:
    """Corrige una observación in-place. Devuelve None si no existe.

    `timestamp`, `zone_id` y `event_day_id` no se tocan: son inmutables por
    decisión de diseño y además el schema de update los rechaza con 422, así que
    acá nunca llegan.

    Solo recalcula warnings si `observed_density` cambió de verdad. Si el
    operador corrige las notas o el observador, los warnings que ya estaban
    calculados siguen siendo válidos y se preservan tal cual: recomputarlos
    sin necesidad los dejaría distintos de cómo seilotaron en su momento, sin
    ganar nada.

    Lo que NO se recalcula es el warning de la observación *siguiente* de la
    misma zona, que usa a esta como referencia. Sigue siendo un hueco conocido
    del MVP: corregir la fila N deja obsoleto el `variacion_pct` de la fila N+1.
    """
    model = await db.get(OperationalObservationModel, observation_id)
    if model is None:
        return None

    if observation_in.observer_id is not None and not _is_valid_uuid(observation_in.observer_id):
        raise HTTPException(
            status_code=400,
            detail=(
                "observer_id inválido: debe ser un UUID de 36 caracteres "
                "o dejarse en blanco"
            ),
        )

    new_density = (
        observation_in.observed_density
        if observation_in.observed_density is not None
        else model.observed_density
    )
    density_changed = new_density != model.observed_density

    # `metadata` del body es la nueva base de las claves del operador; las
    # calculadas por el sistema se sacan y se vuelven a poner después, para que
    # un PATCH de notas no borre warnings ni pueda inyectarlos.
    previous_metadata = dict(model.metadata_ or {})
    base = dict(
        observation_in.metadata
        if observation_in.metadata is not None
        else previous_metadata
    )
    preserved_computed = {
        key: previous_metadata[key]
        for key in COMPUTED_METADATA_KEYS
        if key in previous_metadata
    }
    for key in COMPUTED_METADATA_KEYS:
        base.pop(key, None)

    if density_changed:
        zone = await db.get(Zone, model.zone_id)
        if zone is None:
            raise ValueError(f"Zone with id '{model.zone_id}' not found")
        base.update(
            await _collect_quality_warnings(
                db,
                zone=zone,
                new_density=new_density,
                new_timestamp=model.timestamp,
                exclude_id=model.id,
            )
        )
    else:
        base.update(preserved_computed)

    model.observed_density = new_density
    if observation_in.observer_id is not None:
        model.observer_id = observation_in.observer_id
    if observation_in.source is not None:
        model.source = observation_in.source
    model.metadata_ = base or None
    model.corrected_by = corrected_by
    model.corrected_at = datetime.now(timezone.utc)

    await db.flush()
    await db.commit()
    await db.refresh(model)
    return _to_response(model)