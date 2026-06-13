import sys; sys.path.insert(0, '.')
from app.main import app

for r in app.routes:
    if not hasattr(r, 'path'):
        continue
    path = r.path
    methods = getattr(r, 'methods', None)
    name = getattr(r, 'endpoint', None)
    ename = name.__name__ if name else '?'
    print(f'{methods} {path} -> {ename}')
