"""Tests del CRUD admin de Protocolos de Control de Observaciones.

Usa el `client` de tests/conftest.py, que overridea `get_db` con la sesion
transaccional real: el CRUD es sincronico y contra Postgres de verdad, asi que
esto ejercita el DDL de verdad (FKs, UNIQUE y CHECK), no un mock.

Cubre el CRUD completo, las validaciones de FK (404 por entidad inexistente),
el 409 de unicidad por `(event_id, name)`, el soft delete, y el par
suggestions / apply-suggestions con su idempotencia.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import Base, get_async_db, get_db
from app.main import app
from app.models.event import Event
from app.models.event_day_phase import EventDayPhase
from app.models.observation_control_protocol import (
    ObservationControlProtocol,
    ObservationTriggerMetric,
    ObservationTriggerOperator,
)
from app.models.zone_type import ZoneType

# Token de acceso valido, firmado con la misma funcion que el login real.
from tests._auth_tokens import mint_token

BASE = "/api/admin/observation-control-protocols"
# Username del usuario con permisos que usa `_auth()`. Tiene que existir en la
# tabla `users`: `require_permission` resuelve contra la base, no contra los claims
# del token.
AUTH_USER = "ocp-municipal"
# Usuario sin permisos de protocolos, para probar el 403.
SIN_PERMISOS_USER = "ocp-sin-permisos"
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", settings.DATABASE_URL)
# La URL de `TEST_DATABASE_URL` viene en forma asyncpg (es la de Neon), pero
# `ocp_engine` abre un motor SINCRONO. `create_engine` no acepta un driver
# async, asi que se fuerza psycopg. Mismo criterio que en conftest.py.
TEST_DATABASE_URL_SYNC = re.sub(
    r"^postgresql\+[a-z0-9_]+://", "postgresql+psycopg://", TEST_DATABASE_URL
)


# ── Motor propio del módulo ────────────────────────────────────────────────
#
# Este módulo NO usa el `test_engine` de conftest (scope sesion, que hace
# `DROP SCHEMA public CASCADE` al terminar) ni su `db_session`. Comparte motor
# con el resto de la suite, y `tests/integration/test_recommendation_flow.py`
# gestiona su propio DDL sobre la misma base. Segun cuantos tests corran antes,
# el estado que uno deja cambia lo que el otro encuentra, y aparecen fallos en
# tests/models y tests/unit sin relacion con esta feature (verificado: con este
# archivo, `tests/api + tests/integration + tests/models + tests/unit` daba 8
# fallos; sin el, los mismos grupos dan 740 passed).
#
# Un motor propio por modulo es el criterio que ya usan
# tests/crud/test_operational_observation.py y
# tests/integration/test_recommendation_flow.py: cada uno abre el suyo y no deja
# el pool de la suite en un estado que otro herede.
@pytest.fixture(scope="module")
def ocp_engine():
    engine = create_engine(TEST_DATABASE_URL_SYNC, pool_pre_ping=True)
    # Workaround de PostGIS, identico al de tests/conftest.py:
    # `_degrade_geometry_for_tests`. Sin la libreria `postgis-3`, `create_all`
    # falla al crear la columna geometry, y degradarla a VARCHAR hace fallar
    # ademas los indices GIST sobre ella (una columna VARCHAR no tiene clase de
    # operadores por omision para `gist`). Se quitan mientras dure el modulo.
    saved_types = [
        (table.c[name], column.type)
        for table in Base.metadata.tables.values()
        for name, column in table.columns.items()
        if "geometry" in column.type.__class__.__name__.lower()
    ]
    removed_indexes = [
        index
        for table in Base.metadata.tables.values()
        for index in table.indexes
        if "geometry" in [c.name for c in index.columns]
    ]
    for column, _ in saved_types:
        column.type = String()
    for index in removed_indexes:
        index.table.indexes.discard(index)

    # Segundo bug preexistente de los modelos: `EventDayPhase.intensity` declara
    # `server_default=func.text('1.0')` y Postgres rechaza un default de tipo text
    # sobre una columna double precision. Mismo criterio que conftest.
    from sqlalchemy import DefaultClause, text as sa_text

    intensity_column = EventDayPhase.__table__.c.intensity
    saved_default = intensity_column.server_default
    intensity_column.server_default = DefaultClause(sa_text("1.0"))

    try:
        Base.metadata.create_all(bind=engine)
        # `create_all` crea las TABLAS, no los datos. Este modulo abre su propio
        # motor (no usa el `test_engine` de conftest), asi que el seed de roles y
        # permisos que vive ahi no corrio sobre este esquema: sin esto, cualquier
        # test que monte un usuario con un rol falla con `NoResultFound`.
        from tests.conftest import _seed_rbac_catalog

        _seed_rbac_catalog(engine)
        yield engine
    finally:
        intensity_column.server_default = saved_default
        for column, original in saved_types:
            column.type = original
        for index in removed_indexes:
            index.table.indexes.add(index)
    engine.dispose()


@pytest.fixture
def db_session(ocp_engine):
    connection = ocp_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    session.begin_nested()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def municipal(db_session: Session) -> str:
    """Crea un MUNICIPAL_ADMIN real y devuelve su username.

    Hace falta porque `require_permission` resuelve los permisos contra la tabla
    `users` en cada request (a proposito, para que una baja o un cambio de rol
    surtan efecto inmediato). Un token minted sin usuario en la base daria 401,
    no 403.

    El usuario vive dentro de la misma transaccion que `db_session`, asi que
    existe durante el test y desaparece con el rollback.
    """
    from sqlalchemy import delete

    from app.core.security import hash_password
    from app.models.user import Role, User, UserRole

    previo = db_session.execute(
        select(User).where(User.username == AUTH_USER)
    ).scalar_one_or_none()
    if previo is not None:
        db_session.execute(delete(UserRole).where(UserRole.user_id == previo.id))
        db_session.execute(delete(User).where(User.id == previo.id))
        db_session.flush()

    role = db_session.execute(
        select(Role).where(Role.code == "MUNICIPAL_ADMIN")
    ).scalar_one()
    user = User(
        username=AUTH_USER,
        password_hash=hash_password("clave-de-prueba-larga-suficiente"),
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    db_session.flush()
    return AUTH_USER


@pytest.fixture
def sin_permisos(db_session: Session) -> str:
    """Un OPERADOR_CAMPO real: 5 permisos, ninguno de protocols:*."""
    from sqlalchemy import delete

    from app.core.security import hash_password
    from app.models.user import Role, User, UserRole

    previo = db_session.execute(
        select(User).where(User.username == SIN_PERMISOS_USER)
    ).scalar_one_or_none()
    if previo is not None:
        db_session.execute(delete(UserRole).where(UserRole.user_id == previo.id))
        db_session.execute(delete(User).where(User.id == previo.id))
        db_session.flush()

    role = db_session.execute(
        select(Role).where(Role.code == "OPERADOR_CAMPO")
    ).scalar_one()
    user = User(
        username=SIN_PERMISOS_USER,
        password_hash=hash_password("clave-de-prueba-larga-suficiente"),
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    db_session.flush()
    return SIN_PERMISOS_USER


@pytest.fixture
def sample_event(db_session: Session) -> Event:
    event = Event(id="test-event-1", name="Test Event", description="Test")
    db_session.add(event)
    db_session.flush()
    return event


@pytest.fixture
def client(db_session: Session, municipal: str) -> TestClient:
    """Cliente con la sesión transaccional y con un usuario con permisos.

    Depende de `municipal` a propósito: todos los endpoints del módulo ahora exigen
    `protocols:read` o `protocols:write`, y `require_permission` resuelve contra la
    base. Sin el usuario, cada request devolvería 401 y ningún test probaría lo que
    dice probar.
    """
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


def _body(event_id: str, **overrides) -> dict:
    payload = {
        "event_id": event_id,
        "name": "Saturación alta",
        "trigger_metric": "saturation_level",
        "trigger_operator": "gt",
        "threshold_value": "0.80",
        "action_interval_minutes": 5,
    }
    payload.update(overrides)
    return payload


class TestCreate:
    def test_crea_protocolo(self, client: TestClient, db_session: Session, sample_event: Event):
        resp = client.post(BASE, json=_body(sample_event.id), headers=_auth())

        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Saturación alta"
        assert data["trigger_metric"] == "saturation_level"
        assert data["trigger_operator"] == "gt"
        assert Decimal(str(data["threshold_value"])) == Decimal("0.80")
        assert data["action_interval_minutes"] == 5
        assert data["active"] is True
        assert data["event_day_id"] is None
        assert data["zone_type_id"] is None

    def test_persiste_en_la_base(
        self, client: TestClient, db_session: Session, sample_event: Event
    ):
        resp = client.post(BASE, json=_body(sample_event.id), headers=_auth())

        row = (
            db_session.query(ObservationControlProtocol)
            .filter(ObservationControlProtocol.id == resp.json()["id"])
            .one()
        )
        assert row.event_id == sample_event.id
        assert row.threshold_value == Decimal("0.80")

    def test_nombre_en_blanco_es_422(
        self, client: TestClient, sample_event: Event
    ):
        resp = client.post(
            BASE, json=_body(sample_event.id, name="   "), headers=_auth()
        )
        assert resp.status_code == 422

    def test_evento_inexistente_es_404(self, client: TestClient):
        resp = client.post(BASE, json=_body("no-existe"), headers=_auth())
        assert resp.status_code == 404
        assert "Event not found" in resp.json()["detail"]

    def test_jornada_inexistente_es_404(
        self, client: TestClient, sample_event: Event
    ):
        resp = client.post(
            BASE,
            json=_body(sample_event.id, event_day_id="no-existe"),
            headers=_auth(),
        )
        assert resp.status_code == 404
        assert "EventDay not found" in resp.json()["detail"]

    def test_tipo_de_zona_inexistente_es_404(
        self, client: TestClient, sample_event: Event
    ):
        resp = client.post(
            BASE,
            json=_body(sample_event.id, zone_type_id="no-existe"),
            headers=_auth(),
        )
        assert resp.status_code == 404
        assert "ZoneType not found" in resp.json()["detail"]

    def test_nombre_duplicado_en_el_mismo_evento_es_409(
        self, client: TestClient, sample_event: Event
    ):
        client.post(BASE, json=_body(sample_event.id), headers=_auth())
        resp = client.post(BASE, json=_body(sample_event.id), headers=_auth())
        assert resp.status_code == 409

    def test_mismo_nombre_en_otro_evento_se_permite(
        self, client: TestClient, db_session: Session, sample_event: Event
    ):
        otro = Event(id="otro-evento", name="Otro", description="")
        db_session.add(otro)
        db_session.flush()

        primero = client.post(BASE, json=_body(sample_event.id), headers=_auth())
        segundo = client.post(BASE, json=_body(otro.id), headers=_auth())

        assert primero.status_code == 201
        assert segundo.status_code == 201

    def test_intervalo_fuera_de_rango_es_422(
        self, client: TestClient, sample_event: Event
    ):
        resp = client.post(
            BASE,
            json=_body(sample_event.id, action_interval_minutes=0),
            headers=_auth(),
        )
        assert resp.status_code == 422

    def test_metrica_desconocida_es_422(self, client: TestClient, sample_event: Event):
        resp = client.post(
            BASE,
            json=_body(sample_event.id, trigger_metric="densidad_secreta"),
            headers=_auth(),
        )
        assert resp.status_code == 422

    def test_operador_desconocido_es_422(self, client: TestClient, sample_event: Event):
        resp = client.post(
            BASE,
            json=_body(sample_event.id, trigger_operator="aproximado"),
            headers=_auth(),
        )
        assert resp.status_code == 422

    def test_sin_token_es_401(self, client: TestClient, sample_event: Event):
        assert client.post(BASE, json=_body(sample_event.id)).status_code == 401


class TestList:
    def test_lista_solo_del_evento(
        self, client: TestClient, db_session: Session, sample_event: Event
    ):
        db_session.add(
            ObservationControlProtocol(
                event_id=sample_event.id,
                name="Mia",
                trigger_metric=ObservationTriggerMetric.CONFIDENCE,
                trigger_operator=ObservationTriggerOperator.LT,
                threshold_value=Decimal("0.5"),
                action_interval_minutes=15,
            )
        )
        db_session.flush()
        otro = Event(id="evento-ajeno", name="Ajeno", description="")
        db_session.add(otro)
        db_session.flush()
        db_session.add(
            ObservationControlProtocol(
                event_id=otro.id,
                name="De otro",
                trigger_metric=ObservationTriggerMetric.CONFIDENCE,
                trigger_operator=ObservationTriggerOperator.LT,
                threshold_value=Decimal("0.5"),
                action_interval_minutes=15,
            )
        )
        db_session.flush()

        resp = client.get(BASE, params={"event_id": sample_event.id}, headers=_auth())

        assert resp.status_code == 200
        nombres = [p["name"] for p in resp.json()]
        assert nombres == ["Mia"]

    def test_oculta_inactivos_por_defecto(
        self, client: TestClient, db_session: Session, sample_event: Event
    ):
        db_session.add(
            ObservationControlProtocol(
                event_id=sample_event.id,
                name="Inactivo",
                trigger_metric=ObservationTriggerMetric.CONFIDENCE,
                trigger_operator=ObservationTriggerOperator.LT,
                threshold_value=Decimal("0.5"),
                action_interval_minutes=15,
                active=False,
            )
        )
        db_session.flush()

        assert client.get(BASE, params={"event_id": sample_event.id}, headers=_auth()).json() == []

    def test_include_inactive_los_trae(
        self, client: TestClient, db_session: Session, sample_event: Event
    ):
        db_session.add(
            ObservationControlProtocol(
                event_id=sample_event.id,
                name="Inactivo",
                trigger_metric=ObservationTriggerMetric.CONFIDENCE,
                trigger_operator=ObservationTriggerOperator.LT,
                threshold_value=Decimal("0.5"),
                action_interval_minutes=15,
                active=False,
            )
        )
        db_session.flush()

        resp = client.get(
            BASE,
            params={"event_id": sample_event.id, "include_inactive": "true"},
            headers=_auth(),
        )
        assert [p["name"] for p in resp.json()] == ["Inactivo"]

    def test_ordenado_por_order(
        self, client: TestClient, db_session: Session, sample_event: Event
    ):
        for name, order in (("Tercero", 2), ("Primero", 0), ("Segundo", 1)):
            db_session.add(
                ObservationControlProtocol(
                    event_id=sample_event.id,
                    name=name,
                    trigger_metric=ObservationTriggerMetric.CONFIDENCE,
                    trigger_operator=ObservationTriggerOperator.LT,
                    threshold_value=Decimal("0.5"),
                    action_interval_minutes=15,
                    order=order,
                )
            )
        db_session.flush()

        resp = client.get(BASE, params={"event_id": sample_event.id}, headers=_auth())
        assert [p["name"] for p in resp.json()] == ["Primero", "Segundo", "Tercero"]

    def test_event_id_es_obligatorio(self, client: TestClient):
        # Con token: la validacion de auth pasa y gana la de query params.
        assert client.get(BASE, headers=_auth()).status_code == 422

    def test_lectura_ya_no_es_publica(self, client: TestClient, sample_event: Event):
        """Antes esta lectura NO exigia token. Ahora sí.

        El cambio es deliberado: expone la configuracion de reglas de todos los
        eventos de la municipalidad. Lo cubre tambien
        `TestAutorizacionRBAC.test_lecturas_sin_token_es_401`.
        """
        assert client.get(
            BASE, params={"event_id": sample_event.id}
        ).status_code == 401

    def test_lectura_con_permiso_es_200(self, client: TestClient, sample_event: Event):
        assert client.get(
            BASE, params={"event_id": sample_event.id}, headers=_auth()
        ).status_code == 200


class TestUpdate:
    def _create(self, client: TestClient, event_id: str) -> dict:
        return client.post(BASE, json=_body(event_id), headers=_auth()).json()

    def test_actualiza_campos(
        self, client: TestClient, db_session: Session, sample_event: Event
    ):
        created = self._create(client, sample_event.id)

        resp = client.put(
            f"{BASE}/{created['id']}",
            json={"threshold_value": "0.95", "action_interval_minutes": 2},
            headers=_auth(),
        )

        assert resp.status_code == 200
        assert Decimal(str(resp.json()["threshold_value"])) == Decimal("0.95")
        assert resp.json()["action_interval_minutes"] == 2

    def test_patch_parcial_no_toca_lo_demas(
        self, client: TestClient, sample_event: Event
    ):
        created = self._create(client, sample_event.id)

        resp = client.put(
            f"{BASE}/{created['id']}", json={"active": False}, headers=_auth()
        )

        assert resp.json()["name"] == created["name"]
        assert resp.json()["threshold_value"] == created["threshold_value"]
        assert resp.json()["active"] is False

    def test_renombrar_a_nombre_ocupado_es_409(
        self, client: TestClient, sample_event: Event
    ):
        primero = self._create(client, sample_event.id)
        client.post(
            BASE, json=_body(sample_event.id, name="Otro"), headers=_auth()
        )

        resp = client.put(
            f"{BASE}/{primero['id']}", json={"name": "Otro"}, headers=_auth()
        )
        assert resp.status_code == 409

    def test_mantener_el_propio_nombre_no_es_conflicto(
        self, client: TestClient, sample_event: Event
    ):
        created = self._create(client, sample_event.id)

        resp = client.put(
            f"{BASE}/{created['id']}", json={"name": created["name"]}, headers=_auth()
        )
        assert resp.status_code == 200

    def test_id_inexistente_es_404(self, client: TestClient):
        resp = client.put(
            f"{BASE}/no-existe", json={"active": True}, headers=_auth()
        )
        assert resp.status_code == 404

    def test_sin_token_es_401(self, client: TestClient, sample_event: Event):
        created = self._create(client, sample_event.id)
        assert client.put(f"{BASE}/{created['id']}", json={"active": False}).status_code == 401

    def test_descripcion_se_puede_limpiar_a_null(
        self, client: TestClient, sample_event: Event
    ):
        created = client.post(
            BASE,
            json=_body(sample_event.id, description="algo"),
            headers=_auth(),
        ).json()

        resp = client.put(
            f"{BASE}/{created['id']}", json={"description": None}, headers=_auth()
        )
        assert resp.json()["description"] is None


class TestDelete:
    def test_soft_delete_deja_la_fila(
        self, client: TestClient, db_session: Session, sample_event: Event
    ):
        created = client.post(
            BASE, json=_body(sample_event.id), headers=_auth()
        ).json()

        resp = client.delete(f"{BASE}/{created['id']}", headers=_auth())

        assert resp.status_code == 204
        row = db_session.get(ObservationControlProtocol, created["id"])
        assert row is not None, "el soft delete no debe borrar la fila"
        assert row.active is False

    def test_delete_deja_de_aparecer_en_el_listado(
        self, client: TestClient, sample_event: Event
    ):
        created = client.post(
            BASE, json=_body(sample_event.id), headers=_auth()
        ).json()
        client.delete(f"{BASE}/{created['id']}", headers=_auth())

        resp = client.get(BASE, params={"event_id": sample_event.id}, headers=_auth())
        assert resp.json() == []

    def test_id_inexistente_es_404(self, client: TestClient):
        assert client.delete(f"{BASE}/no-existe", headers=_auth()).status_code == 404

    def test_sin_token_es_401(self, client: TestClient, sample_event: Event):
        created = client.post(
            BASE, json=_body(sample_event.id), headers=_auth()
        ).json()
        assert client.delete(f"{BASE}/{created['id']}").status_code == 401


class TestSuggestions:
    def test_devuelve_las_cuatro_sugerencias(self, client: TestClient):
        resp = client.get(f"{BASE}/suggestions", headers=_auth())

        assert resp.status_code == 200
        keys = [s["key"] for s in resp.json()["suggestions"]]
        assert keys == [
            "saturacion_alta",
            "espera_larga",
            "disponibilidad_critica",
            "confianza_baja",
        ]

    def test_cada_sugerencia_tiene_frase_legible(self, client: TestClient):
        resp = client.get(f"{BASE}/suggestions", headers=_auth())

        for sugerencia in resp.json()["suggestions"]:
            assert sugerencia["rule_sentence"]
            assert sugerencia["action_interval_minutes"] >= 1

    def test_sin_token_es_401(self, client: TestClient):
        assert client.get(f"{BASE}/suggestions").status_code == 401


class TestApplySuggestions:
    def test_crea_las_sugerencias_pedidas(
        self, client: TestClient, sample_event: Event
    ):
        resp = client.post(
            f"{BASE}/apply-suggestions",
            json={"event_id": sample_event.id, "suggestion_keys": ["saturacion_alta"]},
            headers=_auth(),
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "created": 1,
            "skipped": 0,
            "created_names": ["Saturación alta"],
        }

        listado = client.get(BASE, params={"event_id": sample_event.id}, headers=_auth()).json()
        assert len(listado) == 1
        protocolo = listado[0]
        assert protocolo["trigger_metric"] == "saturation_level"
        assert protocolo["action_interval_minutes"] == 5

    def test_es_idempotente(
        self, client: TestClient, sample_event: Event
    ):
        payload = {
            "event_id": sample_event.id,
            "suggestion_keys": ["saturacion_alta", "espera_larga"],
        }
        client.post(f"{BASE}/apply-suggestions", json=payload, headers=_auth())
        segunda = client.post(
            f"{BASE}/apply-suggestions", json=payload, headers=_auth()
        )

        assert segunda.json() == {"created": 0, "skipped": 2, "created_names": []}
        listado = client.get(BASE, params={"event_id": sample_event.id}, headers=_auth()).json()
        assert len(listado) == 2

    def test_no_duplica_si_el_operador_ya_creo_esa_regla(
        self, client: TestClient, sample_event: Event
    ):
        """Si el operador ya creo "Saturación alta" a mano, adoptarla no duplica."""
        client.post(
            BASE,
            json=_body(sample_event.id, name="Saturación alta"),
            headers=_auth(),
        )

        resp = client.post(
            f"{BASE}/apply-suggestions",
            json={"event_id": sample_event.id, "suggestion_keys": ["saturacion_alta"]},
            headers=_auth(),
        )

        assert resp.json()["created"] == 0
        assert resp.json()["skipped"] == 1

    def test_sugerencia_desconocida_es_422(
        self, client: TestClient, sample_event: Event
    ):
        resp = client.post(
            f"{BASE}/apply-suggestions",
            json={"event_id": sample_event.id, "suggestion_keys": ["inventada"]},
            headers=_auth(),
        )
        assert resp.status_code == 422

    def test_evento_inexistente_es_404(self, client: TestClient):
        resp = client.post(
            f"{BASE}/apply-suggestions",
            json={"event_id": "no-existe", "suggestion_keys": ["saturacion_alta"]},
            headers=_auth(),
        )
        assert resp.status_code == 404

    def test_sin_lista_es_422(self, client: TestClient, sample_event: Event):
        resp = client.post(
            f"{BASE}/apply-suggestions",
            json={"event_id": sample_event.id, "suggestion_keys": []},
            headers=_auth(),
        )
        assert resp.status_code == 422

    def test_sin_token_es_401(self, client: TestClient, sample_event: Event):
        resp = client.post(
            f"{BASE}/apply-suggestions",
            json={"event_id": sample_event.id, "suggestion_keys": ["saturacion_alta"]},
        )
        assert resp.status_code == 401


class TestZoneTypeRelation:
    def test_guarda_tipo_de_zona_valido(
        self, client: TestClient, db_session: Session, sample_event: Event
    ):
        zone_type = ZoneType(
            id="zt-test-protocolo",
            name="Escenario",
            slug="escenario",
            icon="stage",
            description="Escenario",
            default_factors={},
        )
        db_session.add(zone_type)
        db_session.flush()

        resp = client.post(
            BASE,
            json=_body(sample_event.id, zone_type_id=zone_type.id),
            headers=_auth(),
        )
        assert resp.status_code == 201
        assert resp.json()["zone_type_id"] == zone_type.id


class _EmptyAsyncSession:
    """Sesion async sin datos, para ejercitar el cableado de `/compliance`.

    El endpoint lee con `get_async_db` (AsyncSession) y el evaluador consulta
    `predictions` / `operational_observations`, que viven en el registro de `src/`
    y NO estan en el `Base.metadata` que crea este modulo. Para probar la RUTA
    (auth, validacion de `event_id`, forma de la respuesta) no hace falta sembrar
    esas tablas: alcanza con que la sesion no devuelva ningun protocolo. La
    logica del evaluador ya esta cubierta en
    `tests/services/test_observation_compliance.py` con la sesion falsa propia.
    """

    def __init__(self):
        self.queries: list[str] = []

    async def execute(self, stmt):
        self.queries.append(str(stmt))
        return _EmptyResult()


class _EmptyResult:
    def scalars(self):
        return self

    def scalar_one_or_none(self):
        return None

    def all(self):
        return []


@pytest.fixture
def compliance_client(db_session: Session, municipal: str) -> TestClient:
    """Cliente para `/compliance`.

    Necesita las DOS overrides: el endpoint lee datos con `get_async_db`, pero su
    dependencia de autorizacion (`require_permission` -> `get_current_user`) usa
    `get_db`. Sin overridear `get_db` tambien, esa ultima abria el motor real de
    `settings.DATABASE_URL` y el request terminaba en 500 por conexion.
    """
    async def override_get_async_db():
        yield _EmptyAsyncSession()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_async_db] = override_get_async_db
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.pop(get_async_db, None)
    app.dependency_overrides.pop(get_db, None)


class TestComplianceEndpoint:
    """GET /compliance: el unico endpoint de la feature sin cobertura de ruta."""

    def test_devuelve_200_y_el_contrato_completo(self, compliance_client: TestClient):
        resp = compliance_client.get(
            f"{BASE}/compliance", params={"event_id": "test-event-1"}, headers=_auth()
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["event_id"] == "test-event-1"
        assert data["evaluated_at"]
        # Sin protocolos activos no hay nada que evaluar: 0 alertas Y 0 evaluados.
        # Lo importante es que `protocols_evaluated` exista, para que la UI pueda
        # distinguir "nada incumplido" de "nada evaluable".
        assert data["total_alerts"] == 0
        assert data["protocols_evaluated"] == 0
        assert data["alerts"] == []

    def test_requiere_token(self, compliance_client: TestClient):
        resp = compliance_client.get(
            f"{BASE}/compliance", params={"event_id": "test-event-1"}
        )
        assert resp.status_code == 401

    def test_token_invalido_es_401(self, compliance_client: TestClient):
        resp = compliance_client.get(
            f"{BASE}/compliance",
            params={"event_id": "test-event-1"},
            headers={"Authorization": "Bearer no-es-un-jwt"},
        )
        assert resp.status_code == 401

    def test_event_id_es_obligatorio(self, compliance_client: TestClient):
        resp = compliance_client.get(f"{BASE}/compliance", headers=_auth())
        assert resp.status_code == 422

    def test_event_id_vacio_es_422(self, compliance_client: TestClient):
        resp = compliance_client.get(
            f"{BASE}/compliance", params={"event_id": ""}, headers=_auth()
        )
        assert resp.status_code == 422


def _auth(username: str = AUTH_USER) -> dict:
    """Header `Authorization` de un usuario con permisos de protocolos.

    El token lo emite `mint_token` (la misma funcion del login real), pero lo que
    decide el acceso es la fila en `users`: `get_current_user` relee roles y
    permisos de ahi, y por eso el usuario tiene que existir. El fixture `municipal`
    lo crea.
    """
    return {"Authorization": f"Bearer {mint_token(subject=username)}"}


class TestAutorizacionRBAC:
    """401 sin token, 403 con token sin permiso, 200 con el permiso correcto.

    Antes de la migracion a `require_permission` estos endpoints solo pedian un
    token valido: cualquier usuario autenticado entraba, incluido un operador de
    campo. Estos tests fijan el contrato nuevo.
    """

    # ── 401: sin token ──
    def test_lecturas_sin_token_es_401(self, client: TestClient, sample_event: Event):
        assert client.get(f"{BASE}?event_id={sample_event.id}").status_code == 401
        assert client.get(f"{BASE}/suggestions").status_code == 401
        assert client.get(f"{BASE}/compliance?event_id={sample_event.id}").status_code == 401

    def test_escrituras_sin_token_es_401(self, client: TestClient, sample_event: Event):
        assert client.post(BASE, json=_body(sample_event.id)).status_code == 401
        r = client.post(
            f"{BASE}/apply-suggestions",
            json={"event_id": sample_event.id, "suggestion_keys": ["saturacion_alta"]},
        )
        assert r.status_code == 401
        assert client.put(f"{BASE}/no-existe", json={"active": False}).status_code == 401
        assert client.delete(f"{BASE}/no-existe").status_code == 401

    def test_token_invalido_es_401(self, client: TestClient, sample_event: Event):
        r = client.get(
            f"{BASE}?event_id={sample_event.id}",
            headers={"Authorization": "Bearer no-es-un-jwt"},
        )
        assert r.status_code == 401

    def test_token_de_usuario_inexistente_es_401(
        self, client: TestClient, sample_event: Event
    ):
        """Token bien firmado pero de alguien que no esta en `users`.

        No alcanza con que el JWT sea criptograficamente valido: `get_current_user`
        resuelve contra la base, asi que un token de un usuario borrado no sirve.
        """
        r = client.get(
            f"{BASE}?event_id={sample_event.id}",
            headers=_auth("fantasma-que-no-existe"),
        )
        assert r.status_code == 401

    # ── 403: token valido, sin el permiso ──
    def test_lecturas_sin_permiso_es_403(
        self, client: TestClient, sample_event: Event, sin_permisos: str
    ):
        """Un OPERADOR_CAMPO tiene sesion valida pero no `protocols:read`."""
        h = _auth(sin_permisos)
        assert client.get(f"{BASE}?event_id={sample_event.id}", headers=h).status_code == 403
        assert client.get(f"{BASE}/suggestions", headers=h).status_code == 403
        r = client.get(f"{BASE}/compliance?event_id={sample_event.id}", headers=h)
        assert r.status_code == 403

    def test_escrituras_sin_permiso_es_403(
        self, client: TestClient, sample_event: Event, sin_permisos: str
    ):
        h = _auth(sin_permisos)
        assert client.post(BASE, json=_body(sample_event.id), headers=h).status_code == 403

        creado = client.post(BASE, json=_body(sample_event.id), headers=_auth())
        pid = creado.json()["id"]
        assert client.put(f"{BASE}/{pid}", json={"active": False}, headers=h).status_code == 403
        assert client.delete(f"{BASE}/{pid}", headers=h).status_code == 403

    def test_el_403_dice_que_permiso_falta(
        self, client: TestClient, sample_event: Event, sin_permisos: str
    ):
        """El mensaje nombra el permiso: sin eso el operador llama al administrador
        y no sabe que pedir."""
        r = client.post(BASE, json=_body(sample_event.id), headers=_auth(sin_permisos))
        assert r.json()["detail"] == "Permiso requerido: protocols:write"

    def test_403_no_cierra_la_sesion(
        self, client: TestClient, sample_event: Event, sin_permisos: str
    ):
        """403 no es 401.

        Un 401 hace que el cliente cierre sesion y pierda lo que estaba haciendo.
        Con 403 solo se le niega esta accion.
        """
        r = client.get(f"{BASE}?event_id={sample_event.id}", headers=_auth(sin_permisos))
        assert r.status_code == 403
        assert "WWW-Authenticate" not in r.headers

    # ── 200: con el permiso ──
    def test_lecturas_con_permiso_es_200(
        self, client: TestClient, sample_event: Event
    ):
        h = _auth()
        assert client.get(f"{BASE}?event_id={sample_event.id}", headers=h).status_code == 200
        assert client.get(f"{BASE}/suggestions", headers=h).status_code == 200
        assert client.get(f"{BASE}/compliance?event_id={sample_event.id}", headers=h).status_code == 200

    def test_escrituras_con_permiso_es_200(self, client: TestClient, sample_event: Event):
        h = _auth()
        creado = client.post(BASE, json=_body(sample_event.id), headers=h)
        assert creado.status_code == 201
        pid = creado.json()["id"]
        assert client.put(f"{BASE}/{pid}", json={"active": False}, headers=h).status_code == 200
        assert client.delete(f"{BASE}/{pid}", headers=h).status_code == 204

    # ── El permiso es por endpoint, no "tocar el modulo" ──
    def test_read_no_alcanza_para_escribir(
        self, client: TestClient, sample_event: Event, db_session: Session
    ):
        """`protocols:read` no habilita escrituras.

        Si `apply-suggestions` se hubiera dejado con `read`, un usuario de solo
        lectura podria crear reglas.
        """
        from app.core.security import hash_password
        from app.models.user import Permission, Role, RolePermission, User, UserRole

        user = User(
            username="ocp-solo-lectura",
            password_hash=hash_password("clave-de-prueba-larga"),
        )
        db_session.add(user)
        db_session.flush()

        solo_read = Role(
            code="SOLO_LECTURA_PROTOCOLOS", name="Solo lectura", is_system=True
        )
        db_session.add(solo_read)
        db_session.flush()
        permiso = db_session.execute(
            select(Permission).where(Permission.code == "protocols:read")
        ).scalar_one()
        db_session.add(RolePermission(role_id=solo_read.id, permission_id=permiso.id))
        db_session.add(UserRole(user_id=user.id, role_id=solo_read.id))
        db_session.flush()

        h = _auth(user.username)
        assert client.get(f"{BASE}?event_id={sample_event.id}", headers=h).status_code == 200
        assert client.post(BASE, json=_body(sample_event.id), headers=h).status_code == 403

    # ── El acceso refleja el estado actual de la cuenta ──
    def test_quitar_el_permiso_corta_el_acceso_al_instante(
        self,
        client: TestClient,
        sample_event: Event,
        municipal: str,
        db_session: Session,
    ):
        """El token sigue siendo criptograficamente valido; la cuenta ya no alcanza.

        Es la razon de que `get_current_user` relea la base en vez de confiar en los
        claims del JWT: sin esto, revocar un permiso tardaria hasta 15 minutos (la
        vida del access token) en surtir efecto.

        Se opera sobre `db_session`, que es la misma sesion que el cliente inyecta
        en `get_db`: por eso el cambio es visible para el request siguiente.
        """
        from app.models.user import User

        h = _auth(municipal)
        assert client.get(f"{BASE}?event_id={sample_event.id}", headers=h).status_code == 200

        u = db_session.execute(
            select(User).where(User.username == municipal)
        ).scalar_one()
        for ur in list(u.user_roles):
            db_session.delete(ur)
        db_session.flush()
        # `User.user_roles` es `lazy="selectin"`: ya está cargado en el identity map
        # de esta sesión, y sin `expire_all` el request siguiente devolvería la
        # colección cacheada con los roles que ya se borraron.
        db_session.expire_all()

        assert client.get(f"{BASE}?event_id={sample_event.id}", headers=h).status_code == 403

    def test_desactivar_el_usuario_lo_expulsa(
        self,
        client: TestClient,
        sample_event: Event,
        municipal: str,
        db_session: Session,
    ):
        """Dar de baja a alguien es 401, no 403: la sesion deja de existir."""
        from app.models.user import User

        h = _auth(municipal)
        assert client.get(f"{BASE}?event_id={sample_event.id}", headers=h).status_code == 200

        u = db_session.execute(
            select(User).where(User.username == municipal)
        ).scalar_one()
        u.is_active = False
        db_session.flush()
        db_session.expire_all()

        assert client.get(f"{BASE}?event_id={sample_event.id}", headers=h).status_code == 401
