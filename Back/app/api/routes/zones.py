# backend/app/api/routes/zones.py

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.event import Event
from app.models.event_day import EventDay
from app.models.event_day_phase import EventDayPhase
from app.models.operational_phase import OperationalPhase
from app.models.zone import Zone
from app.models.zone_behavior import ZoneBehavior
from app.models.zone_type import ZoneType
from app.schemas.zone import (
    ZoneResponse,
    ZoneCreateRequest,
    ZoneUpdateRequest,
    ZoneConfigUpdateRequest,
)
from app.api.deps import verify_token

router = APIRouter(prefix="/api/events/{event_id}/zones", tags=["zones"])

# Tipo de zona para el que la modalidad de salida es obligatoria. Canónica
# RFC-EXIT-V1 / Parte 3: peatonal | vehicular | transporte.
TIPO_SALIDA = "salida"

MODALIDADES_SALIDA = ("peatonal", "vehicular", "transporte")


def _exigir_modalidad_si_salida(zona_type: str | None, transporte: str | None) -> None:
    """Rechaza con 422 una zona `salida` sin modalidad de transporte.

    El formulario del dashboard ya deshabilita el submit cuando `type` es
    `salida` y no se eligió modalidad, pero nada impedía crearla por API, seed o
    edición manual de la base. Esa fila se persistía y después reventaba
    `/products/exit` con un 500 para todo el evento. Se valida acá para que la
    restricción quede del lado del servidor.
    """
    if zona_type != TIPO_SALIDA:
        return
    if transporte is not None and str(transporte).strip():
        return
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=(
            "Una zona de tipo 'salida' requiere 'transporte' "
            f"({', '.join(MODALIDADES_SALIDA)}). Sin modalidad la salida no se "
            "puede consultar desde /products/exit."
        ),
    )


def _exigir_modalidad_si_salida(zona_type: str | None, transporte: str | None) -> None:
    """Rechaza con 422 una zona `salida` sin modalidad de transporte.

    El formulario del dashboard ya deshabilita el submit cuando `type` es
    `salida` y no se eligió modalidad, pero nada impedía crearla por API, seed o
    edición manual de la base. Esa fila se persistía y después reventaba
    `/products/exit` con un 500 para todo el evento. Se valida acá para que la
    restricción quede del lado del servidor.
    """
    if zona_type != TIPO_SALIDA:
        return
    if transporte is not None and str(transporte).strip():
        return
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=(
            "Una zona de tipo 'salida' requiere 'transporte' "
            f"({', '.join(MODALIDADES_SALIDA)}). Sin modalidad la salida no se "
            "puede consultar desde /products/exit."
        ),
    )


def _sync_zone_behavior_on_status_change(
    db: Session,
    event_id: str,
    zone_type: str,
    new_status: str,
    old_status: str | None = None,
) -> None:
    """Sincroniza `zone_behaviors.flow_restriction` con `zones.status` para 'cerrada'.

    Cuando una zona pasa a 'cerrada', pone `flow_restriction = 'CLOSED'` en todos
    los `zone_behaviors` que correspondan a su `zone_type_id` y a las fases
    operativas activas del evento.
    Cuando sale de 'cerrada', restablece a 'OPEN'.

    Solo afecta a `zone_behaviors` de la fase operativa activa del día actual
    (según `EventDayPhase` del `EventDay` activo). Si no hay día activo, no hace nada.
    """
    # Solo actuar si el cambio involucra 'cerrada'
    era_cerrada = (old_status or "").lower() == "cerrada"
    ahora_cerrada = new_status.lower() == "cerrada"
    if era_cerrada == ahora_cerrada:
        return  # no hay cambio relevante

    # Obtener el zone_type_id desde el slug (ej: 'salida')
    zt = db.query(ZoneType).filter(ZoneType.slug == zone_type).first()
    if not zt:
        return
    zone_type_id = zt.id

    # Buscar el EventDay activo del evento (is_active = true)
    today = datetime.now().date()
    event_day = (
        db.query(EventDay)
        .filter(EventDay.event_id == event_id, EventDay.is_active == True)
        .first()
    )
    if not event_day:
        return

    # Obtener las fases del día activo
    phase_ids = [
        p.operational_phase_id
        for p in db.query(EventDayPhase.operational_phase_id)
        .filter(EventDayPhase.event_day_id == event_day.id)
        .all()
    ]
    if not phase_ids:
        return

    # Flujo objetivo según el nuevo estado
    target_flow = "CLOSED" if ahora_cerrada else "OPEN"

    # Actualizar zone_behaviors que coincidan
    db.query(ZoneBehavior).filter(
        ZoneBehavior.operational_phase_id.in_(phase_ids),
        ZoneBehavior.zone_type_id == zone_type_id,
    ).update({ZoneBehavior.flow_restriction: target_flow}, synchronize_session=False)


@router.get("", response_model=list[ZoneResponse])
def list_zones(event_id: str, db: Session = Depends(get_db)):
    zones = db.query(Zone).filter(Zone.event_id == event_id).all()
    return zones


@router.post("", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
def create_zone(
    event_id: str,
    body: ZoneCreateRequest,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    zone_data = body.model_dump(exclude_unset=True)
    zone_data["event_id"] = event_id
    cap = zone_data.get("capacity", 0)
    zone_data["available_capacity"] = zone_data.get("available_capacity", cap)
    zone_data["saturation"] = Zone.calcular_saturation(cap, zone_data["available_capacity"])
    zone_data.setdefault("status", "activa")
    _exigir_modalidad_si_salida(zone_data.get("type"), zone_data.get("transporte"))
    zone = Zone(**zone_data)
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


@router.patch("/{zone_id}", response_model=ZoneResponse)
def update_zone(
    event_id: str,
    zone_id: str,
    body: ZoneUpdateRequest,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    zone = db.query(Zone).filter(Zone.id == zone_id, Zone.event_id == event_id).first()
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")

    update_data = body.model_dump(exclude_unset=True)
    print(f"[update_zone] PATCH recibido: {body.model_dump()}, update_data: {update_data}")

    # Solo se valida cuando el request toca `transporte`: una fila `salida` sin
    # modalidad que ya quedó en la base (creada antes de esta validación) debe
    # seguir siendo editable en otros campos sin quedar bloqueada.
    if "transporte" in update_data:
        _exigir_modalidad_si_salida(
            zone.type, update_data["transporte"]
        )

    for field, value in update_data.items():
        setattr(zone, field, value)

    # Sincronizar zone_behaviors si cambia el status
    if "status" in update_data:
        _sync_zone_behavior_on_status_change(
            db=db,
            event_id=event_id,
            zone_type=zone.type,
            new_status=update_data["status"],
            old_status=zone.status,
        )

    if "saturation" not in update_data:
        zone.saturation = Zone.calcular_saturation(zone.capacity, zone.available_capacity)
        print(f"[update_zone] saturation no enviado, recalculado: {zone.saturation}")
    else:
        print(f"[update_zone] saturation enviado explícitamente, NO recalcular")

    print(f"[update_zone] Guardando: sat={zone.saturation}, avail={zone.available_capacity}, cap={zone.capacity}")
    db.commit()
    db.refresh(zone)
    print(f"[update_zone] Post-commit: sat={zone.saturation}, avail={zone.available_capacity}, cap={zone.capacity}")
    return zone


@router.put("/{zone_id}/config", response_model=ZoneResponse)
def update_zone_config(
    event_id: str,
    zone_id: str,
    body: ZoneConfigUpdateRequest,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    zone = db.query(Zone).filter(Zone.id == zone_id, Zone.event_id == event_id).first()
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")

    update_data = body.model_dump(exclude_unset=True)
    if "latitude" in update_data:
        update_data["latitude"] = body.latitude
    if "longitude" in update_data:
        update_data["longitude"] = body.longitude

    # Este endpoint sí puede cambiar `type` (a diferencia del PATCH) pero no
    # acepta `transporte`, así que la modalidad se toma de la fila existente:
    # no se puede convertir una zona en `salida` si no tiene modalidad previa.
    if update_data.get("type") == TIPO_SALIDA:
        _exigir_modalidad_si_salida(TIPO_SALIDA, zone.transporte)

    old_status = zone.status
    for field, value in update_data.items():
        setattr(zone, field, value)

    # Sincronizar zone_behaviors si cambia el status
    if "status" in update_data:
        _sync_zone_behavior_on_status_change(
            db=db,
            event_id=event_id,
            zone_type=zone.type,
            new_status=update_data["status"],
            old_status=old_status,
        )

    if "saturation" not in update_data:
        zone.saturation = Zone.calcular_saturation(zone.capacity, zone.available_capacity)

    db.commit()
    db.refresh(zone)
    return zone


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_zone(
    event_id: str,
    zone_id: str,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    zone = db.query(Zone).filter(Zone.id == zone_id, Zone.event_id == event_id).first()
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")

    db.delete(zone)
    db.commit()
