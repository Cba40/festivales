import sys
sys.path.insert(0, '.')
from sqlalchemy import create_engine, text

engine = create_engine('postgresql+psycopg://postgres:postgres@localhost:5432/territorial_mvp')

with engine.connect() as conn:
    r = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'knowledge_model_versions' ORDER BY ordinal_position"))
    print('knowledge_model_versions columns:', r.fetchall())
    
    r2 = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'operational_observations' ORDER BY ordinal_position"))
    print('operational_observations columns:', r2.fetchall())