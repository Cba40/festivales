import sys; sys.path.insert(0, '.')
from sqlalchemy import text
from app.db.session import SessionLocal
s = SessionLocal()
try:
    rows = s.execute(text("SELECT id, name, type, saturation, status, capacity, available_capacity, latitude, longitude, distancia_min, espera_min, disponibilidad FROM zones")).fetchall()
    for r in rows:
        d = dict(r._mapping)
        print(f"  {d['name']:40s} type={d['type']:20s} sat={d['saturation']:10s} status={d['status']:10s} disp={d['disponibilidad']!s:5s} dist_min={d['distancia_min']!s}")
finally:
    s.close()
