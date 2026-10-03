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
#
# El POST resuelve el actor con `get_current_user`, que relee la tabla `users` en
# cada request. Por eso `obs_env` overridea tambien `get_db` y se apoya en los
# fixtures de RBAC de tests/conftest.py: un token con un `sub` que no existe en
# `users` ya no alcanza, sale 401. Las tablas de RBAC viven en `public`, que ya
# esta en el `search_path` de la conexion del schema temporal.

import re

import httpx
import pytest
from datetime import date, datetime, timezone
from types import SimpleNamespace

from sqlalchemy import String, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateIndex, CreateTable

from app.core.config import settings
from app.db.session import get_async_db, get_db
from app.main import app
from app.models.user import User

# Token de acceso valido, firmado con la misma funcion que el login real.
from tests._auth_tokens import mint_token
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
async def obs_env(db_session: Session, rbac_municipal: str, rbac_field: str):
    # `db_session` + los fixtures `rbac_*` son los de tests/conftest.py: crean
    # usuarios reales en `users` y dan de vuelta sus usernames. El POST exige un
    # actor que exista en la base, asi que sin esto todos los tests que crean una
    # observacion salen 401 antes de llegar al CRUD.
    #
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
        async for value in _obs_env_impl(db_session, rbac_municipal, rbac_field):
            yield value
    finally:
        geometry_column.type = original_type


async def _obs_env_impl(db_session: Session, municipal: str, field: str):
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

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_async_db] = _override_get_async_db
    # `get_current_user` (POST) depende de la sesion SINCRONA `get_db`, que por
    # defecto apunta al motor de DESARROLLO: sin este override el usuario del
    # token se busca en la base equivocada. Se saca solo lo que se puso, en vez de
    # `clear()`, para no pisar los overrides de otros fixtures de la suite.
    app.dependency_overrides[get_db] = _override_get_db
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    )
    try:
        yield SimpleNamespace(
            client=client,
            session=session,
            db=db_session,
            user=municipal,
            field_user=field,
        )
    finally:
        await client.aclose()
        app.dependency_overrides.pop(get_async_db, None)
        app.dependency_overrides.pop(get_db, None)
        await session.close()
        await conn.close()
        await engine.dispose()


def _auth_headers(username: str) -> dict:
    """Token de un usuario REAL, para el que creo el fixture de RBAC.

    El POST usa `get_current_user`: la dependencia relee `users` y devuelve 401 si
    el `sub` no corresponde a una cuenta activa. Un `sub` inventado ya no sirve
    para "firmar" nada, asi que el username es siempre el de `rbac_municipal` o el
    de `rbac_field`.
    """
    return {"Authorization": f"Bearer {mint_token(subject=username)}"}


def _user_id(db_session: Session, username: str) -> str:
    return db_session.execute(
        select(User).where(User.username == username)
    ).scalar_one().id


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


async def _crear(env, overrides=None, username: str | None = None) -> dict:
    response = await env.client.post(
        "/api/operational-observations/",
        json=_create_body(overrides),
        headers=_auth_headers(username or env.user),
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
            headers=_auth_headers(obs_env.user),
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
            headers=_auth_headers(obs_env.user),
        )
        assert response.status_code == 200
        assert response.json()["source"] == "sensor"
        assert response.json()["observed_density"] == created["observed_density"]

    async def test_patch_persiste_en_la_base(self, obs_env) -> None:
        created = await _crear(obs_env)
        await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"observed_density": 77},
            headers=_auth_headers(obs_env.user),
        )
        reread = await obs_env.client.get(
            f"/api/operational-observations/{created['id']}",
            headers=_auth_headers(obs_env.user),
        )
        assert reread.json()["observed_density"] == 77

    async def test_patch_inexistente_404(self, obs_env) -> None:
        response = await obs_env.client.patch(
            "/api/operational-observations/11111111-1111-1111-1111-111111111111",
            json={"observed_density": 10},
            headers=_auth_headers(obs_env.user),
        )
        assert response.status_code == 404

    async def test_patch_vacio_422(self, obs_env) -> None:
        created = await _crear(obs_env)
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={},
            headers=_auth_headers(obs_env.user),
        )
        assert response.status_code == 422

    async def test_patch_densidad_negativa_422(self, obs_env) -> None:
        created = await _crear(obs_env)
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"observed_density": -1},
            headers=_auth_headers(obs_env.user),
        )
        assert response.status_code == 422

    async def test_patch_observer_id_422(self, obs_env) -> None:
        """`observer_id` salio del DTO de correccion: mandarlo es 422, no 400.

        Antes se aceptaba y se validaba el formato (400 si no era UUID). Ahora el
        campo ni existe en `OperationalObservationUpdate`, asi que el rechazo lo
        hace `extra="forbid"` antes de tocar la fila.
        """
        created = await _crear(obs_env)
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"observer_id": "no-soy-un-uuid"},
            headers=_auth_headers(obs_env.user),
        )
        assert response.status_code == 422
        reread = await obs_env.client.get(
            f"/api/operational-observations/{created['id']}",
            headers=_auth_headers(obs_env.user),
        )
        assert reread.json()["observer_id"] == created["observer_id"]


class TestImmutableFields:
    """timestamp, zone_id, event_day_id y observer_id no se pueden tocar: 422, no ignore."""

    @pytest.mark.parametrize(
        "campo", ["timestamp", "zone_id", "event_day_id", "observer_id"]
    )
    async def test_patch_campo_inmutable_422(self, obs_env, campo: str) -> None:
        created = await _crear(obs_env)
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"observed_density": 50, campo: "cualquiera"},
            headers=_auth_headers(obs_env.user),
        )
        assert response.status_code == 422
        # Y la densidad no se aplicó: el 422 corta la request entera.
        reread = await obs_env.client.get(
            f"/api/operational-observations/{created['id']}",
            headers=_auth_headers(obs_env.user),
        )
        assert reread.json()["observed_density"] == created["observed_density"]

    async def test_patch_no_puede_falsificar_auditoria(self, obs_env) -> None:
        """corrected_by viene del token, no del body."""
        created = await _crear(obs_env)
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"observed_density": 50, "corrected_by": "yo-quisiera-ser-admin"},
            headers=_auth_headers(obs_env.field_user),
        )
        assert response.status_code == 422

    async def test_patch_no_puede_setear_corrected_at(self, obs_env) -> None:
        created = await _crear(obs_env)
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"observed_density": 50, "corrected_at": "2020-01-01T00:00:00Z"},
            headers=_auth_headers(obs_env.user),
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
            headers=_auth_headers(obs_env.field_user),
        )
        body = response.json()
        assert body["corrected_by"] == obs_env.field_user
        assert body["corrected_at"] is not None

    async def test_corrected_at_es_una_fecha_parseable(self, obs_env) -> None:
        created = await _crear(obs_env)
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"source": "sensor"},
            headers=_auth_headers(obs_env.user),
        )
        parsed = datetime.fromisoformat(response.json()["corrected_at"])
        assert parsed.tzinfo is not None

    async def test_correccion_repetida_actualiza_el_autor(self, obs_env) -> None:
        """Dos operadores reales distintos: el `sub` del token es la firma."""
        created = await _crear(obs_env)
        obs_id = f"/api/operational-observations/{created['id']}"
        first = await obs_env.client.patch(
            obs_id,
            json={"observed_density": 50},
            headers=_auth_headers(obs_env.field_user),
        )
        second = await obs_env.client.patch(
            obs_id,
            json={"observed_density": 60},
            headers=_auth_headers(obs_env.user),
        )
        assert first.json()["corrected_by"] == obs_env.field_user
        assert second.json()["corrected_by"] == obs_env.user

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
            headers=_auth_headers(obs_env.user),
        )
        metadata = response.json()["metadata"]
        assert "posible_error_tipeo" not in (metadata or {}).get("warnings", [])

    async def test_patch_sube_la_densidad_crea_el_warning(self, obs_env) -> None:
        created = await _crear(obs_env, {"observed_density": 10})
        assert not (created["metadata"] or {}).get("warnings")
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"observed_density": 900},
            headers=_auth_headers(obs_env.user),
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
            headers=_auth_headers(obs_env.user),
        )
        # Mismo valor: no se recalcula, se preserva. Y si se recalculara contra
        # si misma, la variacion seria 0% y el warning se perderia.
        assert "variacion_extrema" in response.json()["metadata"]["warnings"]

    async def test_editar_notas_no_toca_los_warnings(self, obs_env) -> None:
        created = await _crear(obs_env, {"metadata": {"notas": "cola larga"}})
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"metadata": {"notas": "nota corregida"}},
            headers=_auth_headers(obs_env.user),
        )
        metadata = response.json()["metadata"]
        assert metadata["notas"] == "nota corregida"
        assert "posible_error_tipeo" in metadata["warnings"]

    async def test_patch_preserva_las_notas_al_cambiar_densidad(self, obs_env) -> None:
        created = await _crear(obs_env, {"metadata": {"notas": "cola larga"}})
        response = await obs_env.client.patch(
            f"/api/operational-observations/{created['id']}",
            json={"observed_density": 50},
            headers=_auth_headers(obs_env.user),
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
            headers=_auth_headers(obs_env.user),
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
            headers=_auth_headers(obs_env.user),
        )
        metadata = response.json()["metadata"]
        # 120 contra 100 previo es +20%: deja de ser variacion extrema.
        assert "variacion_extrema" not in (metadata or {}).get("warnings", [])


class TestObserverIdBlindaje:
    """`observer_id` lo escribe el servidor, con el id del usuario autenticado.

    Antes el campo venia en el body: cualquier cliente podia atribuir su conteo a
    otro observador. Ahora el DTO de alta no lo tiene y el router lo inyecta desde
    `current_user.id`, asi que la fila siempre dice quien esta autenticado de verdad.
    """

    async def test_observer_id_se_inyecta_desde_el_token_no_del_body(
        self, obs_env
    ) -> None:
        """El `observer_id` guardado debe ser el del usuario autenticado,
        no lo que mande el frontend."""
        user_id = _user_id(obs_env.db, obs_env.user)
        # Se manda un UUID valido en el body: es exactamente el caso que un
        # cliente malicioso (o un formulario viejo que no se actualizo) manda.
        response = await obs_env.client.post(
            "/api/operational-observations/",
            json=_create_body({"observer_id": "00000000-0000-0000-0000-000000000000"}),
            headers=_auth_headers(obs_env.user),
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["observer_id"] == user_id

        # Y en la base esta el id del usuario, no el que vino en el body.
        obs = (
            await obs_env.session.execute(
                select(OperationalObservationModel).where(
                    OperationalObservationModel.id == body["id"]
                )
            )
        ).scalar_one()
        assert obs.observer_id == user_id
        assert obs.observer_id != "00000000-0000-0000-0000-000000000000"

    async def test_observer_id_es_el_del_usuario_que_creo_la_fila(
        self, obs_env
    ) -> None:
        """Cada alta guarda el id de quien la hizo, no el de otro operador."""
        creada_por_campo = await _crear(
            obs_env, username=obs_env.field_user, overrides={"timestamp": TS_BASE}
        )
        creada_por_municipal = await _crear(
            obs_env, username=obs_env.user, overrides={"timestamp": TS_LATER}
        )
        campo_id = _user_id(obs_env.db, obs_env.field_user)
        municipal_id = _user_id(obs_env.db, obs_env.user)
        assert creada_por_campo["observer_id"] == campo_id
        assert creada_por_municipal["observer_id"] == municipal_id
        assert campo_id != municipal_id

    async def test_create_sin_usuario_en_la_base_es_401(self, obs_env) -> None:
        """Un `sub` valido y firmado, pero que no esta en `users`, no pasa.

        Es el cierre del blindaje: `get_current_user` relee la tabla en cada
        request, asi que revocar la cuenta corta el acceso aunque el token siga
        sin expirar.
        """
        response = await obs_env.client.post(
            "/api/operational-observations/",
            json=_create_body(),
            headers=_auth_headers("usuario-que-no-existe"),
        )
        assert response.status_code == 401
