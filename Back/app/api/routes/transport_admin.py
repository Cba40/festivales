# backend/app/api/routes/transport_admin.py
# Gestión administrativa de Transporte V1 (Dashboard > Infraestructura > Transporte).
# Patrón idéntico a exit_admin.py: prefijo /api/events/{event_id}, lecturas
# públicas y escrituras con verify_token, PUT de paradas/horarios como
# reemplazo completo e idempotente.
#
# Modelo de datos:
#   transport_lines          -> líneas (name único por evento)
#   transport_line_stops     -> paradas = zonas existentes type='transporte'
#   transport_schedules      -> horarios asociados a line_stop_id (destino en
#                               la propia columna destination, sin tabla aparte).

import csv
import io
import re
from datetime import time
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import verify_token
from app.db.session import get_db
from app.models.event import Event
from app.models.transport_line import TransportLine
from app.models.transport_line_stop import TransportLineStop
from app.models.transport_schedule import TransportSchedule
from app.models.zone import Zone
from app.schemas.transport_admin import (
    CsvImportResponse,
    LineStopResponse,
    LineStopsUpdate,
    ScheduleCreate,
    ScheduleResponse,
    SchedulesUpdate,
    TransportLineCreate,
    TransportLineResponse,
    TransportLineUpdate,
)

router = APIRouter(prefix="/api/events/{event_id}", tags=["Transport Admin"])

_DAY_TYPES = {"weekday", "saturday", "sunday_holiday"}
_LINE_TYPES = {"urbano", "interurbano"}
_TIME_RE = re.compile(r"^\d{2}:\d{2}$")


def _evento_existe(db: Session, event_id: str) -> bool:
    # Chequeo por columna para evitar cargar la entidad completa (events/zone
    # tienen una columna geometry con dependencia PostGIS innecesaria aquí).
    return db.query(Event.id).filter(Event.id == event_id).first() is not None


def _require_event(db: Session, event_id: str) -> None:
    if not _evento_existe(db, event_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")


def _get_line_or_404(db: Session, event_id: str, line_id: str) -> TransportLine:
    line = (
        db.query(TransportLine)
        .filter(TransportLine.id == line_id, TransportLine.event_id == event_id)
        .first()
    )
    if not line:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transport line not found")
    return line


def _time_str(value: time) -> str:
    return value.strftime("%H:%M")


def _parse_time(value: str) -> time:
    if not _TIME_RE.match(value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"departure_time must be in HH:MM format, got: {value!r}",
        )
    try:
        return time(int(value[:2]), int(value[3:]))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"departure_time must be a valid HH:MM time, got: {value!r}",
        )


def _validate_stop_zones(db: Session, event_id: str, stops: list) -> None:
    """Validate every stop: zone exists, type='transporte' and belongs to event."""
    if not stops:
        return
    zone_ids = list(dict.fromkeys(s.zone_id for s in stops))
    rows = (
        db.query(Zone.id, Zone.type)
        .filter(
            Zone.event_id == event_id,
            Zone.id.in_(zone_ids),
            Zone.type == "transporte",
        )
        .all()
    )
    found = {row.id for row in rows}
    missing = [z for z in zone_ids if z not in found]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Zones must exist, belong to the event and be type='transporte': {missing}",
        )

    orders = [s.stop_order for s in stops]
    if len(orders) != len(set(orders)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="stop_order must be unique within the line",
        )


def _validate_schedule_line_stops(db: Session, event_id: str, line_id: str, schedules: list) -> None:
    """Validate every schedule: line_stop_id belongs to the line, time + day_type valid."""
    if not schedules:
        return
    ls_ids = list(dict.fromkeys(s.line_stop_id for s in schedules))
    owned = (
        db.query(TransportLineStop.id)
        .join(TransportLine, TransportLine.id == TransportLineStop.line_id)
        .filter(
            TransportLineStop.id.in_(ls_ids),
            TransportLine.event_id == event_id,
            TransportLineStop.line_id == line_id,
        )
        .all()
    )
    owned_ids = {row.id for row in owned}
    missing = [ls for ls in ls_ids if ls not in owned_ids]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"line_stop_id must belong to the line: {missing}",
        )

    for s in schedules:
        if s.day_type not in _DAY_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid day_type: {s.day_type!r}",
            )
        _parse_time(s.departure_time)


# --------------------------------------------------------------------------
# Líneas
# --------------------------------------------------------------------------


@router.get("/transport-lines", response_model=list[TransportLineResponse])
def list_transport_lines(event_id: str, db: Session = Depends(get_db)):
    _require_event(db, event_id)
    return (
        db.query(TransportLine)
        .filter(TransportLine.event_id == event_id)
        .order_by(TransportLine.name)
        .all()
    )


@router.post("/transport-lines", response_model=TransportLineResponse, status_code=status.HTTP_201_CREATED)
def create_transport_line(
    event_id: str,
    body: TransportLineCreate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    _require_event(db, event_id)

    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Name must not be empty")

    exists = (
        db.query(TransportLine)
        .filter(TransportLine.event_id == event_id, TransportLine.name == name)
        .first()
    )
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transport line already exists for this event",
        )

    line = TransportLine(
        event_id=event_id,
        name=name,
        type=body.type,
        company=body.company.strip() or name,
        color=body.color,
        active=body.active,
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


@router.put("/transport-lines/{line_id}", response_model=TransportLineResponse)
def update_transport_line(
    event_id: str,
    line_id: str,
    body: TransportLineUpdate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    line = _get_line_or_404(db, event_id, line_id)

    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Name must not be empty"
            )
        if name != line.name:
            conflict = (
                db.query(TransportLine)
                .filter(
                    TransportLine.event_id == event_id,
                    TransportLine.name == name,
                    TransportLine.id != line_id,
                )
                .first()
            )
            if conflict:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Transport line already exists for this event",
                )
            line.name = name

    if body.type is not None:
        line.type = body.type
    if body.company is not None:
        line.company = body.company.strip() or line.company
    if body.color is not None:
        line.color = body.color
    if body.active is not None:
        line.active = body.active

    db.commit()
    db.refresh(line)
    return line


@router.delete("/transport-lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transport_line(
    event_id: str,
    line_id: str,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    line = _get_line_or_404(db, event_id, line_id)
    # Borra las paradas explícitamente (los horarios se limpian por CASCADE a
    # nivel BD). Evita que el cascade del ORM sobre relationship() intente
    # null-ear la FK antes de que corra el CASCADE de la BD.
    db.query(TransportLineStop).filter(TransportLineStop.line_id == line_id).delete(
        synchronize_session=False
    )
    db.expire_all()
    db.delete(line)
    db.commit()


# --------------------------------------------------------------------------
# Paradas por línea
# --------------------------------------------------------------------------


def _list_stops(db: Session, line_id: str) -> list[LineStopResponse]:
    rows = (
        db.query(TransportLineStop, Zone.name)
        .join(Zone, Zone.id == TransportLineStop.zone_id)
        .filter(TransportLineStop.line_id == line_id)
        .order_by(TransportLineStop.stop_order)
        .all()
    )
    return [
        LineStopResponse(
            id=tls.id,
            line_id=tls.line_id,
            zone_id=tls.zone_id,
            zone_name=name or "",
            stop_order=tls.stop_order,
        )
        for tls, name in rows
    ]


@router.get("/transport-lines/{line_id}/stops", response_model=list[LineStopResponse])
def get_line_stops(event_id: str, line_id: str, db: Session = Depends(get_db)):
    _get_line_or_404(db, event_id, line_id)
    return _list_stops(db, line_id)


@router.put("/transport-lines/{line_id}/stops", response_model=list[LineStopResponse])
def update_line_stops(
    event_id: str,
    line_id: str,
    body: LineStopsUpdate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    _get_line_or_404(db, event_id, line_id)
    _validate_stop_zones(db, event_id, body.stops)

    db.query(TransportLineStop).filter(TransportLineStop.line_id == line_id).delete()
    for stop in body.stops:
        db.add(TransportLineStop(line_id=line_id, zone_id=stop.zone_id, stop_order=stop.stop_order))
    db.commit()

    return _list_stops(db, line_id)


# --------------------------------------------------------------------------
# Horarios por línea
# --------------------------------------------------------------------------


def _list_schedules(db: Session, line_id: str) -> list[ScheduleResponse]:
    row_ids = (
        db.query(TransportLineStop.id)
        .filter(TransportLineStop.line_id == line_id)
        .all()
    )
    ls_ids = [r.id for r in row_ids]
    if not ls_ids:
        return []

    rows = (
        db.query(TransportSchedule)
        .filter(TransportSchedule.line_stop_id.in_(ls_ids))
        .order_by(TransportSchedule.day_type, TransportSchedule.departure_time)
        .all()
    )
    return [
        ScheduleResponse(
            id=s.id,
            line_stop_id=s.line_stop_id,
            day_type=s.day_type,
            departure_time=_time_str(s.departure_time),
            destination=s.destination,
        )
        for s in rows
    ]


@router.get("/transport-lines/{line_id}/schedules", response_model=list[ScheduleResponse])
def get_line_schedules(event_id: str, line_id: str, db: Session = Depends(get_db)):
    _get_line_or_404(db, event_id, line_id)
    return _list_schedules(db, line_id)


@router.put("/transport-lines/{line_id}/schedules", response_model=list[ScheduleResponse])
def update_line_schedules(
    event_id: str,
    line_id: str,
    body: SchedulesUpdate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    line = _get_line_or_404(db, event_id, line_id)
    _validate_schedule_line_stops(db, event_id, line.id, body.schedules)

    line_stop_ids = [r.id for r in db.query(TransportLineStop.id).filter(TransportLineStop.line_id == line.id).all()]
    if line_stop_ids:
        db.query(TransportSchedule).filter(TransportSchedule.line_stop_id.in_(line_stop_ids)).delete()

    for sched in body.schedules:
        db.add(
            TransportSchedule(
                line_stop_id=sched.line_stop_id,
                day_type=sched.day_type,
                departure_time=_parse_time(sched.departure_time),
                destination=sched.destination.strip() or sched.destination,
            )
        )
    db.commit()

    return _list_schedules(db, line.id)


# --------------------------------------------------------------------------
# Importación masiva CSV (idempotente)
# --------------------------------------------------------------------------


def _zone_by_name(db: Session, event_id: str) -> dict[str, str]:
    rows = (
        db.query(Zone.name, Zone.id)
        .filter(Zone.event_id == event_id, Zone.type == "transporte")
        .all()
    )
    return {name.strip().lower(): zid for name, zid in rows if name}


def _line_by_name(db: Session, event_id: str) -> dict[str, TransportLine]:
    lines = db.query(TransportLine).filter(TransportLine.event_id == event_id).all()
    return {line.name.strip().lower(): line for line in lines if line.name}


@router.post("/transport/import-csv", response_model=CsvImportResponse)
async def import_transport_csv(
    event_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    _require_event(db, event_id)

    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    required = {
        "line_name", "line_type", "company", "stop_name",
        "stop_order", "day_type", "departure_time", "destination",
    }
    if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
        missing = required - set(reader.fieldnames or [])
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"CSV must contain columns: {sorted(missing)}",
        )

    lines_created = 0
    lines_updated = 0
    stops_created = 0
    schedules_created = 0
    errors: list[str] = []

    zones_by_name = _zone_by_name(db, event_id)
    lines_by_name = _line_by_name(db, event_id)

    for row_number, row in enumerate(reader, start=2):
        try:
            line_name = (row.get("line_name") or "").strip()
            line_type = (row.get("line_type") or "").strip().lower()
            company = (row.get("company") or "").strip()
            stop_name = (row.get("stop_name") or "").strip()
            stop_order_raw = (row.get("stop_order") or "").strip()
            day_type = (row.get("day_type") or "").strip().lower()
            departure_raw = (row.get("departure_time") or "").strip()
            destination = (row.get("destination") or "").strip()

            if not line_name:
                errors.append(f"Fila {row_number}: line_name vacío")
                continue
            if line_type not in _LINE_TYPES:
                errors.append(f"Fila {row_number}: line_type inválido '{line_type}'")
                continue
            if day_type not in _DAY_TYPES:
                errors.append(f"Fila {row_number}: day_type inválido '{day_type}'")
                continue
            if not _TIME_RE.match(departure_raw):
                errors.append(f"Fila {row_number}: departure_time inválido '{departure_raw}'")
                continue

            # --- Línea (idempotente por event_id + name) ---
            key = line_name.lower()
            line = lines_by_name.get(key)
            if line is None:
                line = TransportLine(
                    event_id=event_id,
                    name=line_name,
                    type=line_type,
                    company=company or line_name,
                    color=None,
                    active=True,
                )
                db.add(line)
                db.flush()
                lines_by_name[key] = line
                lines_created += 1
            elif line.type != line_type:
                line.type = line_type
                lines_updated += 1

            # --- Parada: vincular a zona existente por nombre ---
            if stop_name:
                zone_key = stop_name.lower()
                zone_id = zones_by_name.get(zone_key)
                if zone_id is None:
                    errors.append(f"Fila {row_number}: sin zona 'transporte' llamada '{stop_name}'")
                    continue
                try:
                    stop_order = int(stop_order_raw)
                except ValueError:
                    errors.append(f"Fila {row_number}: stop_order inválido '{stop_order_raw}'")
                    continue

                existing_stop = (
                    db.query(TransportLineStop)
                    .filter(TransportLineStop.line_id == line.id, TransportLineStop.zone_id == zone_id)
                    .first()
                )
                if existing_stop is None:
                    db.add(TransportLineStop(line_id=line.id, zone_id=zone_id, stop_order=stop_order))
                    db.flush()
                    stops_created += 1
                line_stop_id = (
                    db.query(TransportLineStop.id)
                    .filter(TransportLineStop.line_id == line.id, TransportLineStop.zone_id == zone_id)
                    .first()
                ).id
            else:
                errors.append(f"Fila {row_number}: stop_name vacío")
                continue

            # --- Horario (idempotente por UNIQUE line_stop/day/type/time/dest) ---
            dep_time = _parse_time(departure_raw)
            if destination:
                dup = (
                    db.query(TransportSchedule)
                    .filter(
                        TransportSchedule.line_stop_id == line_stop_id,
                        TransportSchedule.day_type == day_type,
                        TransportSchedule.departure_time == dep_time,
                        TransportSchedule.destination == destination,
                    )
                    .first()
                )
                if dup is None:
                    db.add(
                        TransportSchedule(
                            line_stop_id=line_stop_id,
                            day_type=day_type,
                            departure_time=dep_time,
                            destination=destination,
                        )
                    )
                    schedules_created += 1
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001 - registro granulado por fila
            errors.append(f"Fila {row_number}: error inesperado ({exc})")

    db.commit()

    return CsvImportResponse(
        lines_created=lines_created,
        lines_updated=lines_updated,
        stops_created=stops_created,
        schedules_created=schedules_created,
        errors=errors,
    )


# --------------------------------------------------------------------------
# Plantilla CSV (descarga de referencia para el importador)
# --------------------------------------------------------------------------


@router.get("/transport/csv-template")
def get_transport_csv_template():
    """Descargar plantilla CSV para importación de transporte.

    Devuelve un archivo con los headers exactos que espera
    ``import_transport_csv`` y una fila de ejemplo con datos realistas.
    """
    headers = [
        "line_name",
        "line_type",
        "company",
        "stop_name",
        "stop_order",
        "day_type",
        "departure_time",
        "destination",
    ]

    example_row = {
        "line_name": "Línea 100",
        "line_type": "interurbano",
        "company": "Empresa Ejemplo SRL",
        "stop_name": "Parada Centro",
        "stop_order": 1,
        "day_type": "weekday",
        "departure_time": "10:15",
        "destination": "Córdoba",
    }

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerow(example_row)

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=plantilla-transporte.csv"
        },
    )
