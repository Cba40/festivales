import py_compile
import os

files = [
    'src/infrastructure/composition/prediction_module.py',
    'src/application/knowledge_model/snapshot_service.py',
    'src/infrastructure/persistence/repositories/zone_type_repository.py',
    'src/infrastructure/persistence/repositories/attendance_level_repository.py',
    'src/infrastructure/persistence/repositories/operational_phase_repository.py',
    'src/infrastructure/persistence/repositories/event_day_phase_repository.py',
    'src/infrastructure/persistence/repositories/__init__.py',
]

print("=== PY_COMPILE VALIDATION ===")
all_ok = True
for f in files:
    path = os.path.join(r'D:\CBA 4.0\Festivales\Back', f)
    try:
        py_compile.compile(path, doraise=True)
        print('OK: {}'.format(f))
    except py_compile.PyCompileError as e:
        print('ERROR: {} - {}'.format(f, e))
        all_ok = False

if all_ok:
    print("\nALL FILES COMPILE SUCCESSFULLY")
else:
    print("\nSOME FILES HAVE ERRORS")