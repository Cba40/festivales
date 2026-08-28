# Back/seed.py
# Script idempotente: ejecutar múltiples veces sin duplicar datos.

import sys
from datetime import datetime, timezone, timedelta
sys.path.insert(0, '.')

from sqlalchemy import insert, select, text
from app.db.session import SessionLocal
from app.models.event import Event
from app.models.zone import Zone
from app.models.exit_destination import ExitDestination
from app.models.exit_zone_destination import exit_zone_destinations_table
from app.models.transport_line import TransportLine
from app.models.transport_line_stop import TransportLineStop
from app.models.transport_schedule import TransportSchedule
from app.models.accommodation import Accommodation, AccommodationType
from app.models.city import City
from app.models.emergency import Emergency, EmergencyType

EVENT_ID = "663e6e32-9d4a-4f20-b992-3585b9310522"

EVENT_SLUG = "festival-jesus-maria-2026"

TZ = timezone(timedelta(hours=-3))
EVENT_DATA = {
    "name": "Festival de Jesús María 2026",
    "description": (
        "El Festival Nacional de Doma y Folklore de Jesús María es una "
        "de las celebraciones populares más importantes de Argentina y América Latina, "
        "combinando destreza gaucha, música folklórica y tradición."
    ),
    "location": "Jesús María, Córdoba, Argentina",
    "start_date": datetime(2026, 7, 15, 0, 0, tzinfo=TZ),
    "end_date": datetime(2026, 7, 25, 23, 59, tzinfo=TZ),
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
        "subtipo": "foodtruck",
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
        "subtipo": "restaurante",
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
        "subtipo": "patio_de_comidas",
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
        "transporte": "vehicular",
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
    {
        "name": "Baños Sector Escenario",
        "type": "servicios",
        "capacity": 30,
        "latitude": -30.976500,
        "longitude": -64.093200,
        "subtipo": "banos",
        "x": 45,
        "y": 45,
    },
    {
        "name": "Punto de Hidratación Campo",
        "type": "servicios",
        "capacity": 15,
        "latitude": -30.974800,
        "longitude": -64.091200,
        "subtipo": "hidratacion",
        "x": 38,
        "y": 32,
    },
    {
        "name": "Puesto Sanitario Norte",
        "type": "servicios",
        "capacity": 20,
        "latitude": -30.971500,
        "longitude": -64.089200,
        "subtipo": "salud",
        "x": 20,
        "y": 15,
    },
    {
        "name": "Espacio de Descanso Preferencial",
        "type": "servicios",
        "capacity": 40,
        "latitude": -30.979200,
        "longitude": -64.096500,
        "subtipo": "descanso",
        "x": 55,
        "y": 70,
    },
]


# ─────────────────────────────────────────────────────────────
# Salir V1 (S1/PARTE 4): destinos de egreso y relaciones N:N.
# IDs de zona tomados de la auditoría de producción (2026-08).
# Si un ID no existe en la BD objetivo, la relación se omite con
# advertencia (nunca se crean zonas nuevas ni otros destinos).
# ─────────────────────────────────────────────────────────────
EXIT_DESTINATION_NAMES = ["Córdoba", "Colonia Caroya", "Sinsacate", "Sierras Chicas"]

EXIT_ZONE_DESTINATIONS = {
    # Salida Norte Auto (vehicular): RN9 hacia Córdoba, RP10 hacia Caroya/Sinsacate.
    "b8a6ff92-0fce-4a53-8262-20b0c2d05f0c": ["Córdoba", "Colonia Caroya", "Sinsacate"],
    # Salida Sur Peatonal: destino peatonal realista desde la periferia sur.
    "4a2fbeef-b6d0-4530-8a5e-b192853f5d56": ["Sierras Chicas"],
}


def seed_exit_destinations(session, event):
    """Crea los destinos del evento si no existen (idempotente).

    Lookup por clave natural (event_id, name); skip si existe.
    Devuelve {"created": n, "skipped": n}.
    """
    created = 0
    skipped = 0
    for name in EXIT_DESTINATION_NAMES:
        existente = session.query(ExitDestination).filter(
            ExitDestination.event_id == event.id,
            ExitDestination.name == name,
        ).first()
        if existente:
            print(f"ℹ️ Destino ya existe: {name}")
            skipped += 1
            continue

        session.add(ExitDestination(event_id=event.id, name=name, active=True))
        session.flush()
        created += 1
        print(f"✅ Destino creado: {name}")

    return {"created": created, "skipped": skipped}


def seed_exit_zone_destinations(session):
    """Relaciona las zonas de salida (por ID exacto) con sus destinos.

    Guardas: la zona debe existir y ser type='salida'; el destino debe existir
    para el evento de la zona; la tupla (exit_zone_id, destination_id) no debe
    existir aún. Idempotente: N ejecuciones no duplican ni lanzan errores.
    La consulta de zonas selecciona solo (id, type, event_id): nunca carga
    columnes pesadas como geometry.
    Devuelve la lista de tuplas (zone_id, destination_id) creadas en esta pasada.
    """
    creadas = []
    for zone_id, destination_names in EXIT_ZONE_DESTINATIONS.items():
        zona = session.execute(
            select(Zone.id, Zone.type, Zone.event_id).where(Zone.id == zone_id)
        ).first()
        if zona is None:
            print(f"⚠️ Zona de salida no encontrada en esta BD (skip): {zone_id}")
            continue
        if zona.type != "salida":
            print(f"⚠️ La zona {zone_id} es type='{zona.type}', no 'salida' (skip)")
            continue

        for destination_name in destination_names:
            destino = session.query(ExitDestination).filter(
                ExitDestination.event_id == zona.event_id,
                ExitDestination.name == destination_name,
            ).first()
            if destino is None:
                print(f"⚠️ Destino inexistente para el evento {zona.event_id} (skip): {destination_name}")
                continue

            existe_relacion = session.execute(
                select(exit_zone_destinations_table).where(
                    exit_zone_destinations_table.c.exit_zone_id == zone_id,
                    exit_zone_destinations_table.c.destination_id == destino.id,
                )
            ).first()
            if existe_relacion:
                print(f"ℹ️ Relación ya existe: {destination_name}")
                continue

            session.execute(
                insert(exit_zone_destinations_table).values(
                    exit_zone_id=zone_id,
                    destination_id=destino.id,
                )
            )
            session.flush()
            creadas.append((zone_id, destino.id))
            print(f"✅ Relación creada: {zone_id[:8]}… -> {destination_name}")

    return creadas


# ─────────────────────────────────────────────────────────────
# Transporte V1 (S1/PARTE 4): líneas, paradas y horarios de prueba.
# ─────────────────────────────────────────────────────────────

TRANSPORT_LINES_DATA = [
    {
        "name": "Línea 100 Ejemplo",
        "type": "interurbano",
        "company": "Empresa Ejemplo SRL",
        "color": "#FF5733",
    },
    {
        "name": "Línea 200 Ejemplo",
        "type": "urbano",
        "company": "Transporte Urbano SA",
        "color": "#3498DB",
    },
]

TRANSPORT_STOP_LINKS = [
    {"line_name": "Línea 100 Ejemplo", "zone_name": "Parada Línea A", "stop_order": 1},
    {"line_name": "Línea 100 Ejemplo", "zone_name": "Parada Línea B", "stop_order": 2},
    {"line_name": "Línea 200 Ejemplo", "zone_name": "Parada Línea A", "stop_order": 1},
    {"line_name": "Línea 200 Ejemplo", "zone_name": "Parada Express", "stop_order": 2},
]

TRANSPORT_SCHEDULES_DATA = [
    {"line_name": "Línea 100 Ejemplo", "zone_name": "Parada Línea A", "day_type": "weekday", "hour": 10, "minute": 15, "destination": "Córdoba"},
    {"line_name": "Línea 100 Ejemplo", "zone_name": "Parada Línea A", "day_type": "weekday", "hour": 11, "minute": 30, "destination": "Córdoba"},
    {"line_name": "Línea 100 Ejemplo", "zone_name": "Parada Línea B", "day_type": "weekday", "hour": 10, "minute": 25, "destination": "Córdoba"},
    {"line_name": "Línea 100 Ejemplo", "zone_name": "Parada Línea B", "day_type": "weekday", "hour": 11, "minute": 40, "destination": "Córdoba"},
    {"line_name": "Línea 200 Ejemplo", "zone_name": "Parada Línea A", "day_type": "weekday", "hour": 8, "minute": 0, "destination": "Terminal"},
    {"line_name": "Línea 200 Ejemplo", "zone_name": "Parada Línea A", "day_type": "weekday", "hour": 9, "minute": 0, "destination": "Terminal"},
    {"line_name": "Línea 200 Ejemplo", "zone_name": "Parada Express", "day_type": "weekday", "hour": 8, "minute": 15, "destination": "Terminal"},
]


def seed_transport_data(session, event):
    """Crea líneas, paradas y horarios de transporte de prueba (idempotente).

    Las paradas son zonas existentes con type='transporte'.
    Lookup por clave natural en cada nivel; skip si existe.
    Devuelve {"lines_created": n, "stops_created": n, "schedules_created": n}.
    """
    lines_created = 0
    stops_created = 0
    schedules_created = 0

    # --- 1. Líneas ---
    lines_by_name = {}
    for ld in TRANSPORT_LINES_DATA:
        existente = session.query(TransportLine).filter(
            TransportLine.event_id == event.id,
            TransportLine.name == ld["name"],
        ).first()
        if existente:
            print(f"ℹ️ Línea ya existe: {ld['name']}")
            lines_by_name[ld["name"]] = existente
            continue

        line = TransportLine(
            event_id=event.id,
            name=ld["name"],
            type=ld["type"],
            company=ld["company"],
            color=ld["color"],
        )
        session.add(line)
        session.flush()
        lines_by_name[ld["name"]] = line
        lines_created += 1
        print(f"✅ Línea creada: {ld['name']}")

    # --- 2. Paradas (line_stops) ---
    line_stops_by_key = {}
    for sl in TRANSPORT_STOP_LINKS:
        line = lines_by_name[sl["line_name"]]
        zona_row = session.execute(
            select(Zone.id, Zone.event_id).where(
                Zone.event_id == event.id,
                Zone.name == sl["zone_name"],
                Zone.type == "transporte",
            )
        ).first()
        if zona_row is None:
            print(f"⚠️ Zona no encontrada (skip): {sl['zone_name']}")
            continue
        zona_id = zona_row.id

        existente = session.query(TransportLineStop).filter(
            TransportLineStop.line_id == line.id,
            TransportLineStop.zone_id == zona_id,
        ).first()
        if existente:
            print(f"ℹ️ Parada ya existe: {sl['line_name']} → {sl['zone_name']}")
            line_stops_by_key[(sl["line_name"], sl["zone_name"])] = existente
            continue

        tls = TransportLineStop(
            line_id=line.id,
            zone_id=zona_id,
            stop_order=sl["stop_order"],
        )
        session.add(tls)
        session.flush()
        line_stops_by_key[(sl["line_name"], sl["zone_name"])] = tls
        stops_created += 1
        print(f"✅ Parada creada: {sl['line_name']} → {sl['zone_name']} (orden {sl['stop_order']})")

    # --- 3. Horarios ---
    from datetime import time as dtime
    for sd in TRANSPORT_SCHEDULES_DATA:
        key = (sd["line_name"], sd["zone_name"])
        tls = line_stops_by_key.get(key)
        if tls is None:
            print(f"⚠️ Line_stop no encontrado (skip): {key}")
            continue

        departure = dtime(sd["hour"], sd["minute"])
        existente = session.query(TransportSchedule).filter(
            TransportSchedule.line_stop_id == tls.id,
            TransportSchedule.day_type == sd["day_type"],
            TransportSchedule.departure_time == departure,
            TransportSchedule.destination == sd["destination"],
        ).first()
        if existente:
            print(f"ℹ️ Horario ya existe: {sd['line_name']} {departure} → {sd['destination']}")
            continue

        ts = TransportSchedule(
            line_stop_id=tls.id,
            day_type=sd["day_type"],
            departure_time=departure,
            destination=sd["destination"],
        )
        session.add(ts)
        session.flush()
        schedules_created += 1
        print(f"✅ Horario creado: {sd['line_name']} {departure} → {sd['destination']}")

    return {
        "lines_created": lines_created,
        "stops_created": stops_created,
        "schedules_created": schedules_created,
    }


def get_or_create_event(session):
    event = session.query(Event).filter(Event.id == EVENT_ID).first()
    if event:
        print(f"ℹ️ Evento ya existe: {event.name} (id={event.id})")
        return event

    session.execute(text("""
        INSERT INTO events (id, name, description, location, start_date, end_date)
        VALUES (:id, :name, :description, :location, :start_date, :end_date)
    """), {
        "id": EVENT_ID,
        "name": EVENT_DATA["name"],
        "description": EVENT_DATA["description"],
        "location": EVENT_DATA["location"],
        "start_date": EVENT_DATA["start_date"],
        "end_date": EVENT_DATA["end_date"],
    })
    session.commit()

    event = session.query(Event).filter(Event.id == EVENT_ID).first()
    print(f"✅ Evento creado: {event.name} (id={event.id})")
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


ACCOMMODATIONS_DATA = [
    {
        "name": "Hotel de la Estación",
        "type": AccommodationType.HOTEL,
        "address": "Av. Independencia 1250, Jesús María, Córdoba",
        "reference": "A 1,2 km del anfiteatro, sobre Av. Independencia",
        "latitude": -30.9815,
        "longitude": -64.0935,
        "phone": "+54 3525 420-101",
        "website": "https://hoteldelaestacion.com.ar",
        "official_info_url": "https://jesusmaria.gob.ar/turismo",
    },
    {
        "name": "Hostel La Doma",
        "type": AccommodationType.HOSTEL,
        "address": "Calle Córdoba 340, Jesús María, Córdoba",
        "reference": "A 800 m del festival, ambiente joven",
        "latitude": -30.9790,
        "longitude": -64.0910,
        "phone": "+54 3525 420-202",
        "website": "https://hostelladoma.com.ar",
        "official_info_url": "https://jesusmaria.gob.ar/turismo",
    },
    {
        "name": "Camping Municipal Ribera",
        "type": AccommodationType.CAMPING,
        "address": "Ruta Nacional 9 km 148, Jesús María, Córdoba",
        "reference": "A 3,5 km del predio, a orillas del río",
        "latitude": -30.9700,
        "longitude": -64.1000,
        "phone": "+54 3525 420-303",
        "website": "https://jesusmaria.gob.ar/turismo/camping",
        "official_info_url": "https://jesusmaria.gob.ar/turismo",
    },
]


def seed_accommodations(session, event):
    """Seed idempotente de alojamientos de ejemplo (Hospedaje V1)."""
    for ad in ACCOMMODATIONS_DATA:
        existing = session.query(Accommodation).filter(
            Accommodation.event_id == event.id,
            Accommodation.name == ad["name"],
        ).first()
        if existing:
            print(f"\u2139\ufe0f Alojamiento ya existe: {existing.name}")
            continue
        acc = Accommodation(
            event_id=event.id,
            **ad,
        )
        session.add(acc)
        session.flush()
        print(f"\u2705 Alojamiento creado: {acc.name} ({acc.type.value})")


# ─────────────────────────────────────────────────────────────
# Emergencia V1 (S1): ciudades y puntos de emergencia.
# ─────────────────────────────────────────────────────────────

CITIES_SEED = [
    {"name": "Jesús María", "province": "Córdoba", "country": "Argentina"},
    {"name": "Córdoba", "province": "Córdoba", "country": "Argentina"},
]

EMERGENCIES_SEED = [
    {
        "name": "Destacamento Policial Norte",
        "type": EmergencyType.policia,
        "phone": "+54 3525 123456",
        "address": "Av. Vélez Sarsfield 1200",
        "reference": "Frente a la terminal",
        "latitude": -30.9785,
        "longitude": -64.0950,
        "services": "Atención 24hs, denuncias",
        "schedule": "24hs",
    },
    {
        "name": "Cuartel Bomberos Voluntarios",
        "type": EmergencyType.bomberos,
        "phone": "+54 3525 420100",
        "emergency_number": "100",
        "address": "Calle Los Bomberos 450",
        "reference": "A 300m de la plaza",
        "latitude": -30.9801,
        "longitude": -64.0935,
        "services": "Incendios, rescates, prevención",
        "schedule": "24hs",
    },
    {
        "name": "Hospital Municipal",
        "type": EmergencyType.salud,
        "phone": "+54 3525 421234",
        "emergency_number": "107",
        "address": "Av. San Martín 123",
        "reference": "Frente a la Plaza San Martín",
        "latitude": -30.9815,
        "longitude": -64.0920,
        "services": "Urgencias, guardia 24hs",
        "schedule": "24hs",
    },
    {
        "name": "Defensa Civil Jesús María",
        "type": EmergencyType.defensa_civil,
        "phone": "+54 3525 422345",
        "address": "Calle Defensa 789",
        "reference": "Edificio municipal",
        "latitude": -30.9795,
        "longitude": -64.0940,
        "services": "Emergencias climáticas, evacuaciones",
        "schedule": "24hs",
    },
    {
        "name": "SAME 107",
        "type": EmergencyType.numero_emergencia,
        "emergency_number": "107",
        "services": "Emergencias médicas",
        "schedule": "24hs",
        # latitude y longitude son NULL (no tiene ubicación física)
    },
    {
        "name": "Emergencias 911",
        "type": EmergencyType.numero_emergencia,
        "emergency_number": "911",
        "services": "Número único de emergencias",
        "schedule": "24hs",
        # latitude y longitude son NULL
    },
]


def seed_cities_and_emergencies(session):
    """Seed idempotente de ciudades y emergencias (Emergencia V1).

    Lookup por clave natural: City por (name, province, country); Emergency por
    (city_id, name). Las emergencias se asocian a la ciudad "Jesús María".
    Devuelve {"cities_created": n, "cities_skipped": n,
              "emergencies_created": n, "emergencies_skipped": n}.
    """
    cities_created = 0
    cities_skipped = 0
    emergencies_created = 0
    emergencies_skipped = 0

    jesus_maria = None

    for cd in CITIES_SEED:
        city = session.query(City).filter(
            City.name == cd["name"],
            City.province == cd["province"],
            City.country == cd["country"],
        ).first()
        if city:
            print(f"\u2139\ufe0f Ciudad ya existe: {city.name} ({city.province})")
            cities_skipped += 1
        else:
            city = City(name=cd["name"], province=cd["province"], country=cd["country"])
            session.add(city)
            session.flush()
            cities_created += 1
            print(f"\u2705 Ciudad creada: {city.name} ({city.province})")

        if city.name == "Jesús María" and city.province == "Córdoba":
            jesus_maria = city

    if jesus_maria is None:
        print("⚠️ No se encontró la ciudad 'Jesús María' para las emergencias (skip)")
        return {
            "cities_created": cities_created,
            "cities_skipped": cities_skipped,
            "emergencies_created": 0,
            "emergencies_skipped": 0,
        }

    for ed in EMERGENCIES_SEED:
        existing = session.query(Emergency).filter(
            Emergency.city_id == jesus_maria.id,
            Emergency.name == ed["name"],
        ).first()
        if existing:
            print(f"\u2139\ufe0f Emergencia ya existe: {existing.name}")
            emergencies_skipped += 1
            continue
        em = Emergency(city_id=jesus_maria.id, **ed)
        session.add(em)
        session.flush()
        emergencies_created += 1
        print(f"\u2705 Emergencia creada: {em.name} ({em.type.value})")

    return {
        "cities_created": cities_created,
        "cities_skipped": cities_skipped,
        "emergencies_created": emergencies_created,
        "emergencies_skipped": emergencies_skipped,
    }


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
        # Asegurar que el evento esté persistido antes de crear entidades con FK
        session.commit()

        # Re-obtener el evento desde la base para garantizar consistencia del id
        event = session.query(Event).filter(Event.id == event.id).first()

        seed_zones(session, event)
        session.commit()

        # Salir V1 (S1/PARTE 4): destinos + relaciones N:N
        seed_exit_destinations(session, event)
        session.commit()
        seed_exit_zone_destinations(session)
        session.commit()

        # Transporte V1 (S1/PARTE 4): líneas, paradas y horarios de prueba
        seed_transport_data(session, event)
        session.commit()

        # Hospedaje V1 (S1): alojamientos de ejemplo
        seed_accommodations(session, event)
        session.commit()

        # Emergencia V1 (S1): ciudades y puntos de emergencia
        seed_cities_and_emergencies(session)
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
