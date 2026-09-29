# backend/tests/api/routes/test_operational_observations.py
# RFC-006 — PATCH de correccion in-place sobre OperationalObservation.
#
# Stack 100% async (AsyncSession + httpx.AsyncClient), mismo patron que
# test_operational_events_v1.py: schema temporal desechable (tmp_obs_api) con
# solo las tres tablas que toca el CRUD, y `search_path` fijado a nivel de
# conexion (SET, no SET LOCAL) para que sobreviva a los commits del CRUD.
#
# El DDL se genera desde la metadata de los modelos con `CreateTable`, no desde
# un CREATE TABLE escrito a mano: `Zone` tiene 27 columnas y `EventDay` tiene
# FKs a `events`, `attendance_levels` y `operational_profiles`, que no existen en
# este schema. Si el DDL estuviera escrito a mano, cualquier columna nueva en los
# modelos romperia estos tests con un "column does not exist" que no tiene nada
# que ver con lo que se esta probando. Las FKs se dejan como salen de la
# metadata y se resuelven con tablas stub de una columna (ver _scratch_ddl).

import re

import httpx
import pytest
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

from jose import jwt
from sqlalchemy import String, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateIndex, CreateTable

from app.core.config import settings
from app.db.session import get_async_db
from app.main import app
from app.models.event_day import EventDay
from app.models.zone import Zone
from src.infrastructure.persistence.models.operational_observation import (
    OperationalObservationModel,
)

ED_ID = "ed-obs-patch"
ZONE_ID = "zone-obs-patch"
EVENT_ID = "event-obs-patch"
CAPACITY = 100
SCHEMA = "tmp_obs_api"

# 12:00Z = 09:00 America/Argentina/Buenos_Aires, dentro de la ventana [0, 1440).
TS_BASE = "2026-09-29T12:00:00+00:00"
TS_LATER = "2026-09-29T16:00:00+00:00"

_UTC = timezone.utc


def _scratch_ddl() -> str:
    dialect = postgresql.dialect()
    # Stubs para las FKs que los modelos declaran. `events`,
    # `attendance_levels` y `operational_profiles` no se usan en lo que se prueba
    # (el CRUD solo carga EventDay y Zone por id), pero el DDL generado desde la
    # metadata los referencia y Postgres los exige. Declararlos con su id alcanza.
    stubs = [
        "CREATE TABLE events (id VARCHAR(36) PRIMARY KEY)",
        "CREATE TABLE attendance_levels (id VARCHAR(36) PRIMARY KEY)",
        "CREATE TABLE operational_profiles (id uuid PRIMARY KEY)",
    ]
    statements = list(stubs)
    for table in (EventDay.__table__, Zone.__table__, OperationalObservationModel.__table__):
        statements.append(str(CreateTable(table).compile(dialect=dialect)))
        for index in table.indexes:
            index_ddl = str(CreateIndex(index).compile(dialect=dialect))
            if "geometry" in index_ddl:
                # Índice GIST sobre zones.geometry: necesita el operador de
                # PostGIS, que no está instalado. Es irrelevante para estos tests
                # (el CRUD no consulta por geometría), asi que se omite.
                continue
            statements.append(index_ddl)
    # `CreateTable.compile()` no emite el `;` final: sin él, el driver recibe
    # ") CREATE INDEX ..." y Postgres responde "syntax error cerca de CREATE".
    ddl = ";\n".join(statements) + ";"

    # `Zone.geometry` se declara como Geometry("POLYGON"), pero la base de tests
    # tiene la extension postgis registrada en el catalogo SIN los binarios
    # instalados: `CREATE TABLE` con una columna geometry falla con
    # 'UndefinedFile: no se pudo acceder al archivo postgis-3'. Es el mismo
    # motivo por el que los tests DB-backed de test_operational_observation.py
    # se saltan. Se reemplaza por TEXT porque el CRUD solo lee `zone.capacity`:
    # la columna entra en el SELECT que arma `db.get(Zone, ...)` y siempre vale
    # NULL, asi que el tipo no cambia el resultado.
    ddl = re.sub(r"geometry\s+geometry\(POLYGON[^)]*\)", "geometry TEXT", ddl)
    return ddl


@pytest.fixture()
async def obs_env():
    # `Zone.geometry` esta declarada como Geometry("POLYGON"), y el tipo de
    # SQLAlchemy envuelve la columna en `ST_AsEWKB(zones.geometry)` al
    # proyectarla. La base de tests tiene la extension postgis registrada en el
    # catalogo pero SIN los binarios, asi que ese SELECT muere con
    # 'UndefinedFile: no se pudo acceder al archivo postgis-3'. Es el mismo motivo
    # por el que los tests DB-backed de test_operational_observation.py se saltan.
    #
    # Se baja el tipo de esa UNA columna a String mientras corre el test y se
    # restaura al final. Hace falta tocar el tipo y no solo el DDL porque el
    # problema esta en la expresion del SELECT, no en la definicion de la tabla.
    # El CRUD nunca lee `geometry`: solo usa `zone.id` y `zone.capacity`.
    geometry_column = Zone.__table__.c.geometry
    original_type = geometry_column.type
    geometry_column.type = String()
    try:
        async for value in _obs_env_impl():
            yield value
    finally:
        geometry_column.type = original_type


async def _obs_env_impl():
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    conn = await engine.connect()
    await conn.execute(text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
    await conn.execute(text(f"CREATE SCHEMA {SCHEMA}"))
    await conn.execute(text(f"SET search_path TO {SCHEMA}, public"))
    await conn.exec_driver_sql(_scratch_ddl())

    session = async_sessionmaker(bind=conn, expire_on_commit=False)()

    # Filas de las tablas stub, para que las FKs de EventDay y Zone se puedan
    # satisfacer. `operational_profiles` no necesita fila: el PATCH y el POST no
    # tocan operational_profile_id.
    await session.execute(text("INSERT INTO events (id) VALUES (:id)"), {"id": EVENT_ID})
    await session.execute(
        text("INSERT INTO attendance_levels (id) VALUES (:id)"), {"id": "al-obs"}
    )

    session.add(
        EventDay(
            id=ED_ID,
            event_id=EVENT_ID,
            date=date(2026, 9, 29),
            day_of_week="martes",
            attendance_level_id="al-obs",
            operational_start_min=0,
            operational_end_min=1440,
        )
    )
    session.add(
        Zone(
            id=ZONE_ID,
            event_id=EVENT_ID,
            name="Plaza Test",
            type="gastronomia",
            capacity=CAPACITY,
            available_capacity=CAPACITY,
        )
    )
    await session.commit()

    async def _override_get_async_db():
        yield session

    app.dependency_overrides[get_async_db] = _override_get_async_db
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    )
    try:
        yield SimpleNamespace(client=client, session=session)
    finally:
        await client.aclose()
        app.dependency_overrides.clear()
        await session.close()
        await conn.close()
        await engine.dispose()


def _auth_headers(sub: str = "admin") -> dict:
    expire = datetime.now(_UTC) + timedelta(hours=8)
    token = jwt.encode(
        {"sub": sub, "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


def _create_body(overrides: dict | None = None) -> dict:
    body = {
        "event_day_id": ED_ID,
        "zone_id": ZONE_ID,
        "timestamp": TS_BASE,
        "observed_density": 400,
        "source": "manual",
    }
    if overrides:
        body.update(overrides)
    return body


async def _crear(env, overrides=None, sub: str = "admin") -> dict:
    response = await env.client.post(
        "/api/operational-observations/",
        json=_create_body(overrides),
        headers=_auth_headers(sub),
    )
    assert response.status_code == 201, response.text
    return response.json()


class TestAuthentication:
    """Los cuatro endpoints del router exigen token."""

    async def test_401_create_sin_token(self, obs_env) -> None:
        response = await obs_env.client.post(
            "/api/operational-observations/", json=_create_body()
        )
        assert response.status_code == 401

    async def test_401_list_sin_token(self, obs_env) -> None:
        response = await obs_env.client.get("/api/operational-observations/")
        assert response.status_code == 401

    async def test_401_detail_sin_token(self, obs_env) -> None:
        created = await _crear(obs_env)
        response = await obs_env.client.get(
            f"/api/operational-observations/{created['id']}"
        )
        assert response.status_code == 401

    async def test_401_patch_sin_token(self, obs_env) -> None:
        created = await _crear(obs_env)
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"observed_density": 50},
        )
        assert response.status_code == 401


class TestPatch:
    async def test_patch_cambia_densidad(self, obs_env) -> None:
        created = await _crear(obs_env)
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"observed_density": 50},
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["observed_density"] == 50
        assert body["id"] == created["id"]

    async def test_patch_ignora_observer_id_si_no_se_manda(self, obs_env) -> None:
        created = await _crear(obs_env)
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"source": "sensor"},
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        assert response.json()["source"] == "sensor"
        assert response.json()["observed_density"] == created["observed_density"]

    async def test_patch_persiste_en_la_base(self, obs_env) -> None:
        created = await _crear(obs_env)
        await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"observed_density": 77},
            headers=_auth_headers(),
        )
        reread = await obs_env.client.get(
            f"/api/operational-observations/{created['id']}", headers=_auth_headers()
        )
        assert reread.json()["observed_density"] == 77

    async def test_patch_inexistente_404(self, obs_env) -> None:
        response = await obs_env.client.patch(
            "/api/operational-observations/11111111-1111-1111-1111-111111111111",
            json={"observed_density": 10},
            headers=_auth_headers(),
        )
        assert response.status_code == 404

    async def test_patch_vacio_422(self, obs_env) -> None:
        created = await _crear(obs_env)
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={},
            headers=_auth_headers(),
        )
        assert response.status_code == 422

    async def test_patch_densidad_negativa_422(self, obs_env) -> None:
        created = await _crear(obs_env)
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"observed_density": -1},
            headers=_auth_headers(),
        )
        assert response.status_code == 422

    async def test_patch_observer_id_invalido_400(self, obs_env) -> None:
        created = await _crear(obs_env)
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"observer_id": "no-soy-un-uuid"},
            headers=_auth_headers(),
        )
        assert response.status_code == 400


class TestImmutableFields:
    """timestamp, zone_id y event_day_id no se pueden tocar: 422, no ignore."""

    @pytest.mark.parametrize("campo", ["timestamp", "zone_id", "event_day_id"])
    async def test_patch_campo_inmutable_422(self, obs_env, campo: str) -> None:
        created = await _crear(obs_env)
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"observed_density": 50, campo: "cualquiera"},
            headers=_auth_headers(),
        )
        assert response.status_code == 422
        # Y la densidad no se aplicó: el 422 corta la request entera.
        reread = await obs_env.client.get(
            f"/api/operational-observations/{created['id']}", headers=_auth_headers()
        )
        assert reread.json()["observed_density"] == created["observed_density"]

    async def test_patch_no_puede_falsificar_auditoria(self, obs_env) -> None:
        """corrected_by viene del token, no del body."""
        created = await _crear(obs_env)
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"observed_density": 50, "corrected_by": "yo-quisiera-ser-admin"},
            headers=_auth_headers(sub="admin-real"),
        )
        assert response.status_code == 422

    async def test_patch_no_puede_setear_corrected_at(self, obs_env) -> None:
        created = await _crear(obs_env)
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"observed_density": 50, "corrected_at": "2020-01-01T00:00:00Z"},
            headers=_auth_headers(),
        )
        assert response.status_code == 422


class TestAuditFields:
    async def test_corrected_at_se_setea_solo(self, obs_env) -> None:
        created = await _crear(obs_env)
        assert created["corrected_by"] is None
        assert created["corrected_at"] is None

        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"observed_density": 50},
            headers=_auth_headers(sub="inspector-ana"),
        )
        body = response.json()
        assert body["corrected_by"] == "inspector-ana"
        assert body["corrected_at"] is not None

    async def test_corrected_at_es_una_fecha_parseable(self, obs_env) -> None:
        created = await _crear(obs_env)
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"source": "sensor"},
            headers=_auth_headers(),
        )
        parsed = datetime.fromisoformat(response.json()["corrected_at"])
        assert parsed.tzinfo is not None

    async def test_correccion_repetida_actualiza_el_autor(self, obs_env) -> None:
        created = await _crear(obs_env)
        obs_id = f"/api/operational-observations/{created['id']}"
        first = await obs_env.client.patch(
            obs_id, json={"observed_density": 50}, headers=_auth_headers(sub="ana")
        )
        second = await obs_env.client.patch(
            obs_id, json={"observed_density": 60}, headers=_auth_headers(sub="beto")
        )
        assert first.json()["corrected_by"] == "ana"
        assert second.json()["corrected_by"] == "beto"

    async def test_crear_no_marca_la_observacion_como_corregida(self, obs_env) -> None:
        created = await _crear(obs_env)
        assert created["corrected_by"] is None
        assert created["corrected_at"] is None


class TestWarningRecalculation:
    """400 sobre capacidad 100 dispara `posible_error_tipeo` (3x)."""

    async def test_alta_marca_warning_de_tipeo(self, obs_env) -> None:
        created = await _crear(obs_env)
        warnings = (created["metadata"] or {}).get("warnings", [])
        assert "posible_error_tipeo" in warnings

    async def test_patch_baja_la_densidad_elimina_el_warning(self, obs_env) -> None:
        created = await _crear(obs_env)
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"observed_density": 50},
            headers=_auth_headers(),
        )
        metadata = response.json()["metadata"]
        assert "posible_error_tipeo" not in (metadata or {}).get("warnings", [])

    async def test_patch_sube_la_densidad_crea_el_warning(self, obs_env) -> None:
        created = await _crear(obs_env, {"observed_density": 10})
        assert not (created["metadata"] or {}).get("warnings")
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"observed_density": 900},
            headers=_auth_headers(),
        )
        metadata = response.json()["metadata"]
        assert "posible_error_tipeo" in metadata["warnings"]
        assert metadata["densidad_observada"] == 900

    async def test_patch_no_compara_contra_si_misma(self, obs_env) -> None:
        """Sin `exclude_id`, la fila editada seria su propia referencia y la
        variacion daria siempre 0%. Este test falla si se pierde ese filtro."""
        await _crear(obs_env, {"observed_density": 10, "timestamp": TS_BASE})
        segunda = await _crear(obs_env, {"observed_density": 500, "timestamp": TS_LATER})
        # 500 contra 10 previo es +4900%: variacion extrema.
        assert "variacion_extrema" in segunda["metadata"]["warnings"]

        response = await obs_env.client.patch(
            f"/api/operational-observations/{segunda['id']}",
            json={"observed_density": 500},
            headers=_auth_headers(),
        )
        # Mismo valor: no se recalcula, se preserva. Y si se recalculara contra
        # si misma, la variacion seria 0% y el warning se perderia.
        assert "variacion_extrema" in response.json()["metadata"]["warnings"]

    async def test_editar_notas_no_toca_los_warnings(self, obs_env) -> None:
        created = await _crear(obs_env, {"metadata": {"notas": "cola larga"}})
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"metadata": {"notas": "nota corregida"}},
            headers=_auth_headers(),
        )
        metadata = response.json()["metadata"]
        assert metadata["notas"] == "nota corregida"
        assert "posible_error_tipeo" in metadata["warnings"]

    async def test_patch_preserva_las_notas_al_cambiar_densidad(self, obs_env) -> None:
        created = await _crear(obs_env, {"metadata": {"notas": "cola larga"}})
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"observed_density": 50},
            headers=_auth_headers(),
        )
        metadata = response.json()["metadata"]
        assert metadata["notas"] == "cola larga"
        assert "posible_error_tipeo" not in (metadata or {}).get("warnings", [])

    async def test_el_cliente_no_puede_inyectar_warnings(self, obs_env) -> None:
        created = await _crear(obs_env, {"observed_density": 10})
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={
                "observed_density": 10,
                "metadata": {"warnings": ["variacion_extrema"]},
            },
            headers=_auth_headers(),
        )
        metadata = response.json()["metadata"]
        assert "variacion_extrema" not in (metadata or {}).get("warnings", [])

    async def test_variacion_extrema_se_recalcula_contra_la_previa(self, obs_env) -> None:
        await _crear(obs_env, {"observed_density": 100, "timestamp": TS_BASE})
        segunda = await _crear(obs_env, {"observed_density": 400, "timestamp": TS_LATER})
        assert "variacion_extrema" in segunda["metadata"]["warnings"]
        assert segunda["metadata"]["densidad_anterior"] == 100

        response = await obs_env.client.patch(
            f"/api/operational-observations/{segunda['id']}",
            json={"observed_density": 120},
            headers=_auth_headers(),
        )
        metadata = response.json()["metadata"]
        # 120 contra 100 previo es +20%: deja de ser variacion extrema.
        assert "variacion_extrema" not in (metadata or {}).get("warnings", [])
