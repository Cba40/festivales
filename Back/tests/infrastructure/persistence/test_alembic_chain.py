"""Invariantes del arbol de migraciones activo (Back/alembic/versions/).

Sustituye a `test_migrations_p30.py`, que validaba el arbol huerfano de
`src/infrastructure/persistence/migrations/` (eliminado: no lo usaba nadie y
describia un esquema incompatible con la app real).

Solo se parsean los archivos con `ast`: no se importa nada del proyecto ni se
toca la base, asi que corre sin `DATABASE_URL` y sin PostGIS.
"""
from __future__ import annotations

import ast
from pathlib import Path

BACK = Path(__file__).resolve().parents[3]
VERSIONS_DIR = BACK / "alembic" / "versions"
INI_PATH = BACK / "alembic.ini"
ENV_PATH = BACK / "alembic" / "env.py"


def _read_chain() -> dict[str, str | None]:
    """revision -> down_revision, para todas las migraciones del arbol activo."""
    chain: dict[str, str | None] = {}
    for path in sorted(VERSIONS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        found: dict[str, str | None] = {}
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            targets = []
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                targets = [(node.target.id, node.value)]
            elif isinstance(node, ast.Assign):
                targets = [(t.id, node.value) for t in node.targets if isinstance(t, ast.Name)]
            for name, value in targets:
                if name in ("revision", "down_revision"):
                    try:
                        found[name] = ast.literal_eval(value)
                    except ValueError:
                        found[name] = None
        revision, down = found.get("revision"), found.get("down_revision")
        assert revision, f"{path.name} no declara 'revision'"
        assert revision not in chain, f"revision ID duplicada: {revision}"
        chain[revision] = down
    return chain


def test_alembic_ini_points_to_the_active_tree() -> None:
    assert 'script_location = %(here)s/alembic' in INI_PATH.read_text(encoding="utf-8")


def test_no_duplicate_revision_ids() -> None:
    # _read_chain ya falla si encuentra un duplicado al construir el dict.
    assert len(_read_chain()) > 1


def test_exactly_one_root_and_one_head() -> None:
    chain = _read_chain()
    assert [r for r, d in chain.items() if d is None] != [], "ninguna revision raiz"
    assert len([r for r, d in chain.items() if d is None]) == 1, "hay mas de una raiz"
    parents = {d for d in chain.values() if d is not None}
    heads = [r for r in chain if r not in parents]
    assert len(heads) == 1, f"se esperaba una sola head, hay {len(heads)}: {heads}"


def test_chain_is_linear_and_has_no_gaps() -> None:
    chain = _read_chain()
    parents = {d for d in chain.values() if d is not None}
    unknown = parents - set(chain)
    assert not unknown, f"down_revision sin archivo: {unknown}"

    children: dict[str | None, list[str]] = {}
    for revision, down in chain.items():
        children.setdefault(down, []).append(revision)
    forks = {p: kids for p, kids in children.items() if len(kids) > 1}
    assert not forks, f"la cadena se bifurca en {forks}"

    root = next(r for r, d in chain.items() if d is None)
    walked, cursor = [], root
    while cursor is not None:
        walked.append(cursor)
        kids = children.get(cursor, [])
        cursor = kids[0] if kids else None
    assert set(walked) == set(chain), (
        f"revisiones inalcanzables desde la raiz: {sorted(set(chain) - set(walked))}"
    )


def test_env_py_registers_the_src_layer() -> None:
    """Guarda del arreglo que evito que Alembic propusiera drop_table en src/.

    `OperationalObservationModel` y demas viven en su propio Base, distinto del
    que declaraba env.py antes del commit 92141ae. Si se pierde ese import,
    `--autogenerate` vuelve a proponer borrar esas tablas.
    """
    env_py = ENV_PATH.read_text(encoding="utf-8")
    assert "from src.infrastructure.persistence.models import" in env_py
    assert "OperationalObservationModel" in env_py
    assert "SrcBase" in env_py
    assert "to_metadata" in env_py
