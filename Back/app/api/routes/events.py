# backend/app/api/routes/events.py

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.event import Event
from app.models.event_day import EventDay
from app.schemas.event import (
    ActiveEventResponse,
    EventCreate,
    EventResponse,
    EventUpdate,
)
from app.api.deps import verify_token

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("", response_model=list[EventResponse])
def list_events(db: Session = Depends(get_db), _=Depends(verify_token)):
    events = db.query(Event).all()
    return events


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    body: EventCreate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    event_data = body.model_dump(exclude_unset=True)
    event = Event(**event_data)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/active", response_model=ActiveEventResponse)
def get_active_event(db: Session = Depends(get_db)):
    """Evento de la jornada activa que el operador configuró desde el dashboard.

    Sin autenticación a propósito, y no por descuido: el frente público
    (mapa de zonas, estado del evento) consulta este endpoint antes de que exista
    sesión. Si exigiera token, `ZoneList` y `EventStatusBar` arrancarían sin
    `event_id` justamente en el caso de uso abierto.

    Se declara **antes** de `/{event_id}` a propósito. FastAPI resuelve las rutas en
    orden de registro, así que si esta viviera después, `GET /api/events/active`
    entraría por `/{event_id}` con `event_id="active"` y devolvería 404. Es el
    mismo motivo por el que hoy `event-days/today` precede a `event-days/{day_id}`.

    Criterio de selección, en este orden:

    1. `date = hoy AND is_active = true`. Es lo que el operador marca y es lo que
       espera la app.
    2. Si no hay jornada para hoy, la activa más reciente. Sirve para las pantallas
       que se consultan fuera del día de evento (preparación, rehearsal) y evita
       que la app quede inservible un día entre jornadas.

    Con más de una candidata gana la de fecha más reciente; el desempate por `id`
    existe solo para que dos filas con la misma fecha devuelvan siempre la misma y
    la app no oscile entre dos-request.

    404 cuando no hay ninguna jornada activa: es información accionable ("configurá
    una jornada"), no un error transitorio, y un fallback hardcodeado sería
    justamente el bug que este endpoint viene a eliminar.
    """
    today = date.today()

    day = (
        db.query(EventDay)
        .filter(EventDay.date == today, EventDay.is_active.is_(True))
        .order_by(EventDay.id)
        .first()
    )

    if day is None:
        day = (
            db.query(EventDay)
            .filter(EventDay.is_active.is_(True))
            .order_by(EventDay.date.desc(), EventDay.id)
            .first()
        )

    if day is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay evento activo configurado",
        )

    # El nombre es informativo: la UI lo muestra como título y la identidad real la
    # sigue siendo `event_id`. Se hace la consulta aparte porque `EventDay.event` es
    # `lazy="selectin"` y el evento puede no estar en la sesión cacheada.
    event_name = db.query(Event.name).filter(Event.id == day.event_id).scalar()

    return {
        "event_id": day.event_id,
        "event_day_id": day.id,
        "event_name": event_name,
        "date": day.date,
    }


@router.get("/{event_id}", response_model=EventResponse)
def get_event(event_id: str, db: Session = Depends(get_db), _=Depends(verify_token)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.put("/{event_id}", response_model=EventResponse)
def update_event(
    event_id: str,
    body: EventUpdate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)
    return event