import os
import re

base = r'D:/CBA 4.0/Festivales/Back'
files = [
    'src/infrastructure/persistence/models/attendance_level.py',
    'src/infrastructure/persistence/models/operational_phase.py',
    'src/infrastructure/persistence/models/event_day_phase.py',
]
for f in files:
    path = os.path.join(base, f)
    with open(path, 'r') as fp:
        content = fp.read()
        match = re.search(r'class (\w+)', content)
        if match:
            print(os.path.basename(f) + ': ' + match.group(1))
        else:
            print(os.path.basename(f) + ': NO CLASS FOUND')