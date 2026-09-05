import os

base = r'D:/CBA 4.0/Festivales/Back'
new_files = [
    'src/domain/entities/knowledge_model_version.py',
    'src/infrastructure/persistence/models/knowledge_model_version.py',
    'alembic/versions/kmv_000000000001_knowledge_model_versioning.py',
    'src/domain/ports/knowledge_model_version_repository.py',
    'src/infrastructure/persistence/repositories/knowledge_model_version_repository.py',
    'src/application/knowledge_model/snapshot_service.py',
    'src/infrastructure/persistence/repositories/zone_type_repository.py',
    'src/infrastructure/persistence/repositories/attendance_level_repository.py',
    'src/infrastructure/persistence/repositories/operational_phase_repository.py',
    'src/infrastructure/persistence/repositories/event_day_phase_repository.py',
]

modified_files = [
    'src/domain/value_objects/territorial_prediction.py',
    'src/infrastructure/persistence/models/prediction.py',
    'src/infrastructure/persistence/mappers/prediction_mapper.py',
    'src/application/context_engine/context_engine.py',
    'src/application/context_engine/stage5_prediction_assembly.py',
    'src/infrastructure/composition/prediction_module.py',
]

print('=== ARCHIVOS NUEVOS ===')
for f in new_files:
    path = os.path.join(base, f)
    exists = os.path.exists(path)
    print('  {} {}'.format('OK' if exists else 'MISSING', f))

print()
print('=== ARCHIVOS MODIFICADOS ===')
for f in modified_files:
    path = os.path.join(base, f)
    exists = os.path.exists(path)
    print('  {} {}'.format('OK' if exists else 'MISSING', f))

# Check repos __init__.py
init_path = os.path.join(base, 'src/infrastructure/persistence/repositories/__init__.py')
print('  {} src/infrastructure/persistence/repositories/__init__.py (updated)'.format('OK' if os.path.exists(init_path) else 'MISSING'))