import sys
sys.path.insert(0, '.')
from sqlalchemy import create_engine, text, MetaData

engine = create_engine('postgresql+psycopg://postgres:postgres@localhost:5432/territorial_mvp')
meta = MetaData()
meta.reflect(bind=engine)
print('Tablas reflejadas:', list(meta.tables.keys()))

if 'predictions' in meta.tables:
    table = meta.tables['predictions']
    print('Columnas predictions:')
    for col in table.columns:
        print(f'  {col.name}: {col.type}')
else:
    print('Tabla predictions NO encontrada en metadata')
    
# Also check with raw SQL
with engine.connect() as conn:
    r = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'predictions' ORDER BY ordinal_position"))
    print('Raw SQL predictions:', r.fetchall())