import sys
sys.path.insert(0, '.')
from sqlalchemy import create_engine, text, MetaData, inspect

engine = create_engine('postgresql+psycopg://postgres:postgres@localhost:5432/territorial_mvp')

# Method 1: SQLAlchemy Core inspection
insp = inspect(engine)
print('Tables in DB:', insp.get_table_names())

# Method 2: Metadata reflect
meta = MetaData()
meta.reflect(bind=engine)
print('Tables reflected:', list(meta.tables.keys()))

# Method 3: Raw SQL - check ALL schemas
with engine.connect() as conn:
    r = conn.execute(text("SELECT table_name, table_schema FROM information_schema.tables WHERE table_type = 'BASE TABLE'"))
    all_tables = r.fetchall()
    print('All tables in all schemas:', all_tables)
    
    # Look for predictions specifically
    pred_tables = [t for t in all_tables if 'predict' in t[0].lower() or 'pred' in t[0].lower()]
    print('Tables matching predict/pred:', pred_tables)
    
    # Check predictions column by column across all schemas
    for schema, table_name in [('public', 'predictions'), ('public', 'predictions')]:
        try:
            r = conn.execute(text(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}' AND table_schema = '{schema}' ORDER BY ordinal_position"))
            print(f'Columnas {schema}.{table_name}:', r.fetchall())
        except Exception as e:
            print(f'Error en {schema}.{table_name}: {e}')