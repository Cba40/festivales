import sys
sys.path.insert(0, '.')
from sqlalchemy import create_engine, text

engine = create_engine('postgresql+psycopg://postgres:postgres@localhost:5432/territorial_mvp')
with engine.connect() as conn:
    r = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"))
    print('Todas las tablas:', r.fetchall())
    r2 = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'predictions' ORDER BY ordinal_position"))
    print('Columnas predictions:', r2.fetchall())