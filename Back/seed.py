# Back/seed.py
# Script idempotente: ejecutar múltiples veces sin duplicar datos.

import sys
sys.path.insert(0, '.')

from app.db.session import SessionLocal
from app.models.event import Event
from app.models.zone import Zone

EVENT_SLUG = "festival-jesus-maria-2026"

EVENT_DATA = {
    "name": "Festival de Jesús María 2026",
    "description": (
        "El Festival de Jesús María es una de las celebraciones más "
        "emblemáticas del Perú, combinando tradición, música y cultura "
        "en un entorno único."
    ),
    "location": "Jesús María, Lima, Perú",
    "start_date": "2026-07-15T00:00:00-05:00",
    "end_date": "2026-07-25T23:59:00-05:00",
}

ZONES_DATA = [
    {
        "name": "Estacionamiento Norte",
        "type": "estacionamiento",
        "capacity": 500,
        "latitude": -30.973313,
        "longitude": -64.088529,
        "disponibilidad": 45,
    },
    {
        "name": "Estacionamiento Sur",
        "type": "estacionamiento",
        "capacity": 400,
        "latitude": -30.985337,
        "longitude": -64.094209,
        "disponibilidad": 80,
    },
    {
        "name": "Estacionamiento VIP",
        "type": "estacionamiento",
        "capacity": 100,
        "latitude": -30.978107,
        "longitude": -64.094779,
        "disponibilidad": 10,
    },
    {
        "name": "Estacionamiento General",
        "type": "estacionamiento",
        "capacity": 600,
        "latitude": -30.981249,
        "longitude": -64.099398,
        "disponibilidad": 0,
    },
    {
        "name": "Parada Línea A",
        "type": "transporte",
        "capacity": 300,
        "latitude": -30.973313,
        "longitude": -64.088529,
        "espera_min": 8,
        "calle": "Av. Principal",
    },
    {
        "name": "Parada Línea B",
        "type": "transporte",
        "capacity": 250,
        "latitude": -30.978107,
        "longitude": -64.094779,
        "espera_min": 15,
        "calle": "Calle Secundaria",
    },
    {
        "name": "Parada Express",
        "type": "transporte",
        "capacity": 200,
        "latitude": -30.985337,
        "longitude": -64.094209,
        "espera_min": 5,
        "calle": "Ruta Nacional",
    },
    {
        "name": "Food Truck Central",
        "type": "comida",
        "capacity": 150,
        "latitude": -30.973313,
        "longitude": -64.088529,
        "subtipo": "rapido",
        "tipo_culinario": "comida_rapida",
        "geometry_type": "point",
        "coordinates": [-30.973313, -64.088529],
    },
    {
        "name": "Parrilla Festival",
        "type": "comida",
        "capacity": 200,
        "latitude": -30.978107,
        "longitude": -64.094779,
        "subtipo": "comida",
        "tipo_culinario": "parrillas",
        "geometry_type": "point",
        "coordinates": [-30.978107, -64.094779],
    },
    {
        "name": "Patio Gastronómico Central",
        "type": "comida",
        "capacity": 400,
        "latitude": -30.975000,
        "longitude": -64.090000,
        "subtipo": "comida",
        "tipo_culinario": "mixto",
        "geometry_type": "line",
        "coordinates": [[-30.975, -64.090], [-30.973, -64.092], [-30.971, -64.094]],
    },
    {
        "name": "Baños Norte",
        "type": "servicios",
        "capacity": 20,
        "latitude": -30.973313,
        "longitude": -64.088529,
        "subtipo": "banos",
        "x": 25,
        "y": 20,
    },
    {
        "name": "Baños Sur",
        "type": "servicios",
        "capacity": 20,
        "latitude": -30.985337,
        "longitude": -64.094209,
        "subtipo": "banos",
        "x": 65,
        "y": 80,
    },
    {
        "name": "Punto de Agua Central",
        "type": "servicios",
        "capacity": 10,
        "latitude": -30.973313,
        "longitude": -64.088529,
        "subtipo": "hidratacion",
        "x": 50,
        "y": 40,
    },
    {
        "name": "Zona Sombría",
        "type": "servicios",
        "capacity": 30,
        "latitude": -30.981249,
        "longitude": -64.099398,
        "subtipo": "descanso",
        "x": 75,
        "y": 55,
    },
    {
        "name": "Primeros Auxilios",
        "type": "servicios",
        "capacity": 15,
        "latitude": -30.978107,
        "longitude": -64.094779,
        "subtipo": "salud",
        "x": 45,
        "y": 65,
    },
    {
        "name": "Destacamento Policial",
        "type": "emergencia",
        "capacity": 10,
        "latitude": -30.9785,
        "longitude": -64.0950,
        "direccion": "Av. Vélez Sarsfield 1200",
        "horario": "24hs",
        "telefono": "+543511234567",
    },
    {
        "name": "Puesto de Salud Municipal",
        "type": "emergencia",
        "capacity": 15,
        "latitude": -30.9801,
        "longitude": -64.0935,
        "direccion": "Córdoba 450",
        "horario": "24hs",
        "telefono": "+543517654321",
    },
    {
        "name": "Salida Norte Auto",
        "type": "salida",
        "capacity": 400,
        "latitude": -30.973313,
        "longitude": -64.088529,
        "transporte": "auto",
        "espera_min": 15,
        "capacidad_estimada": 400,
    },
    {
        "name": "Salida Sur Peatonal",
        "type": "salida",
        "capacity": 80,
        "latitude": -30.985337,
        "longitude": -64.094209,
        "transporte": "peatonal",
        "espera_min": 4,
        "capacidad_estimada": 80,
    },
    {
        "name": "Hotel del Festival",
        "type": "hospedaje",
        "capacity": 80,
        "latitude": -30.976000,
        "longitude": -64.091000,
        "subtipo": "hotel",
        "telefono": "+543511234568",
        "web": "https://hoteldelfestival.com",
        "disponibilidad": 45,
    },
    {
        "name": "Hostel Centro",
        "type": "hospedaje",
        "capacity": 40,
        "latitude": -30.982000,
        "longitude": -64.095000,
        "subtipo": "hostel",
        "telefono": "+543511234569",
        "disponibilidad": 20,
    },
    {
        "name": "Camping Municipal",
        "type": "hospedaje",
        "capacity": 200,
        "latitude": -30.970000,
        "longitude": -64.100000,
        "subtipo": "camping",
        "telefono": "+543511234570",
        "disponibilidad": 120,
    },
    {
        "name": "Alojamientos Doña Rosa",
        "type": "hospedaje",
        "capacity": 20,
        "latitude": -30.983000,
        "longitude": -64.092000,
        "subtipo": "hospedaje",
        "telefono": "+543511234571",
        "disponibilidad": 5,
    },
]


def get_or_create_event(session):
    event = session.query(Event).filter(Event.name == EVENT_DATA["name"]).first()
    if event:
        print(f"\u2139\ufe0f Evento ya existe: {event.name} (id={event.id})")
        return event

    event = Event(
        name=EVENT_DATA["name"],
        description=EVENT_DATA["description"],
        location=EVENT_DATA["location"],
        start_date=EVENT_DATA["start_date"],
        end_date=EVENT_DATA["end_date"],
    )
    session.add(event)
    session.flush()
    print(f"\u2705 Evento creado: {event.name} (id={event.id})")
    return event


def seed_zones(session, event):
    for zd in ZONES_DATA:
        zone = session.query(Zone).filter(
            Zone.event_id == event.id,
            Zone.name == zd["name"],
        ).first()
        if zone:
            print(f"\u2139\ufe0f Zona ya existe: {zone.name}")
            continue

        extra_fields = {k: v for k, v in zd.items()
                        if k not in ("name", "type", "capacity", "latitude", "longitude")}
        saturation = "bajo"
        status = "activa"
        disp = zd.get("disponibilidad")
        if disp is not None:
            if disp == 0:
                saturation = "alto"
                status = "critico"
            elif disp <= 20:
                saturation = "medio"
                status = "alerta"

        cap = zd["capacity"]
        sat_to_avail = {"bajo": cap, "medio": int(cap * 0.6), "alto": int(cap * 0.35), "colapsado": int(cap * 0.1)}

        zone = Zone(
            event_id=event.id,
            name=zd["name"],
            type=zd["type"],
            capacity=cap,
            available_capacity=sat_to_avail[saturation],
            saturation=saturation,
            status=status,
            latitude=zd["latitude"],
            longitude=zd["longitude"],
            **extra_fields,
        )
        session.add(zone)
        session.flush()
        print(f"\u2705 Zona creada: {zone.name}")


def main():
    session = SessionLocal()
    try:
        # Migrar zonas existentes: type='servicios' + subtipo='hospedaje' → type='hospedaje'
        migrated = session.query(Zone).filter(
            Zone.type == 'servicios',
            Zone.subtipo == 'hospedaje',
        ).update({"type": "hospedaje"})
        if migrated:
            print(f"✅ Migradas {migrated} zonas de servicios→hospedaje")

        # Migrar zonas existentes: type='parking' → type='estacionamiento'
        parked = session.query(Zone).filter(Zone.type == 'parking').update({"type": "estacionamiento"})
        if parked:
            print(f"✅ Migradas {parked} zonas de parking→estacionamiento")

        session.commit()

        event = get_or_create_event(session)
        seed_zones(session, event)
        session.commit()
        print(f"\n\U0001f4cb VITE_EVENT_ID={event.id}")
    except Exception as e:
        session.rollback()
        print(f"\u274c Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
