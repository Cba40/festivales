"""Autorización y ownership de las escrituras de alertas (RFC-ALERTS-MESSAGES-V1).

Cubre los dos huecos que encontró la auditoría del módulo:

1. Las nueve escrituras de ``alert_admin.py`` (4 de alertas + 5 de mensajes)
   pedían ``verify_token`` ("cualquier usuario autenticado") aunque el permiso
   ``alerts:write`` ya existía y ya se otorgaba a los roles. Publicar o borrar un
   aviso de seguridad al público era una operación abierta a cualquier cuenta con
   token válido, incluido ANALISTA, que es de solo lectura.
2. ``update``, ``deactivate``, ``delete``, ``publish``, ``cancel`` y el ``delete``
   de mensajes tomaban el ``alert_id`` / ``message_id`` del path y actuaban sobre
   la fila sin comparar su ``event_id`` con el de la URL. Solo ``get_alert_endpoint``
   chequeaba. Con eso, un token válido para un evento alcanzaba para modificar o
   borrar los avisos de otro (IDOR).

Infraestructura
---------------
Estas rutas son async (``get_async_db``) y el resto de la suite solo sobreescribe
la sesión sync (``get_db``), así que el módulo no tenía ninguna forma de probar
sus endpoints contra la base de test. Este archivo monta su propio motor async
contra la misma base y siembra las filas **commiteadas**: la sesión transaccional
de ``db_session`` hace rollback al final del test, así que lo que el handler ve
por la sesión async tiene que estar confirmado en la base. Por eso el teardown
borra explícitamente lo sembrado.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.session import get_async_db, get_db
from app.main import app
from app.models.event import Event
from app.models.operator_message import OperatorMessage
from app.models.transport_alert import TransportAlert
from tests._auth_tokens import mint_token

ADMIN = "/api/admin/events"

EVENTO_PROPIO = "test-alerts-evento-propio"
EVENTO_AJENO = "test-alerts-evento-ajeno"


def _auth(username: str) -> dict:
    """Token de un usuario que existe en la base.

    Lo que decide el acceso es la fila en `users`: `get_current_user` relee roles
    y permisos de ahí, no de los claims del JWT.
    """
    return {"Authorization": f"Bearer {mint_token(subject=username)}"}


def _alerta_json(event_id: str) -> dict:
    return {
        "event_id": event_id,
        "alert_type": "warning",
        "title": "Corte de línea",
        "description": "Prueba de autorización",
        "valid_from": "2026-01-01T10:00:00Z",
        "valid_until": "2026-01-01T12:00:00Z",
    }


def _mensaje_json(event_id: str) -> dict:
    return {
        "event_id": event_id,
        "priority": "normal",
        "title": "Aviso de prueba",
        "description": "Prueba de autorización",
        "publish_at": "2026-01-01T10:00:00Z",
    }


def _motor_async():
    """Motor async contra la MISMA base que usa la suite.

    La URL de test viene en forma asyncpg, que no entiende el parámetro `sslmode`
    de psycopg: hay que sacarlo de la URL y pasarlo como `ssl` en connect_args.

    `NullPool` porque cada test usa su propio event loop: una conexión asyncpg
    queda atada al loop que la creó, y si el pool la recicla hacia otro loop
    asyncpg falla con "another operation is in progress".
    """
    url = os.environ.get("TEST_DATABASE_URL", settings.DATABASE_URL)
    partes = urlsplit(url)
    query = dict(parse_qsl(partes.query))
    ssl = query.pop("sslmode", None)
    query.pop("channel_binding", None)
    limpia = urlunsplit(
        (partes.scheme, partes.netloc, partes.path, urlencode(query), "")
    )
    connect_args = {"ssl": ssl} if ssl else {}
    return create_async_engine(limpia, connect_args=connect_args, poolclass=NullPool)


@pytest.fixture(autouse=True)
def _limpiar_overrides():
    yield
    app.dependency_overrides.pop(get_async_db, None)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def alertas(
    db_session,
    rbac_municipal: str,
    rbac_analista: str,
    rbac_field: str,
):
    """Client con la sesión async apuntando a la base de test, y filas sembradas.

    Depende de `db_session` (aunque no lo use) para que corra el fixture
    `test_engine`, que es el que hace `create_all`. Las filas se siembran
    commiteadas porque el handler las lee por una sesión async distinta, y
    `db_session` hace rollback al terminar.
    """
    motor = _motor_async()
    factory = async_sessionmaker(motor, expire_on_commit=False)

    async def override_get_async_db():
        async with factory() as session:
            yield session

    # `get_db` también va sobreescrito: `require_permission` resuelve el usuario
    # por la sesión **sync** (`get_current_user` -> `get_db`), así que sin esto la
    # comprobación de permisos leería de la base real en vez de la de test.
    def override_get_db():
        yield db_session

    async def sembrar():
        ahora = datetime.now(timezone.utc)
        async with factory() as session:
            session.add_all([
                Event(id=EVENTO_PROPIO, name="Evento propio"),
                Event(id=EVENTO_AJENO, name="Evento ajeno"),
            ])
            await session.flush()
            alerta = TransportAlert(
                event_id=EVENTO_AJENO,
                alert_type="disruption",
                title="Alerta del evento ajeno",
                description="No debe ser alcanzable desde el evento propio",
                valid_from=ahora,
                valid_until=ahora + timedelta(hours=2),
            )
            mensaje = OperatorMessage(
                event_id=EVENTO_AJENO,
                priority="urgent",
                title="Mensaje del evento ajeno",
                description="No debe ser alcanzable desde el evento propio",
                publish_at=ahora,
            )
            session.add_all([alerta, mensaje])
            await session.commit()
            return alerta.id, mensaje.id

    async def limpiar():
        async with factory() as session:
            await session.execute(delete(TransportAlert).where(
                TransportAlert.event_id.in_([EVENTO_PROPIO, EVENTO_AJENO])
            ))
            await session.execute(delete(OperatorMessage).where(
                OperatorMessage.event_id.in_([EVENTO_PROPIO, EVENTO_AJENO])
            ))
            await session.execute(delete(Event).where(
                Event.id.in_([EVENTO_PROPIO, EVENTO_AJENO])
            ))
            await session.commit()

    loop = asyncio.new_event_loop()
    try:
        alerta_id, mensaje_id = loop.run_until_complete(sembrar())
        app.dependency_overrides[get_async_db] = override_get_async_db
        app.dependency_overrides[get_db] = override_get_db

        with TestClient(app, raise_server_exceptions=False) as c:
            yield c, {
                "alerta_id": str(alerta_id),
                "mensaje_id": str(mensaje_id),
                "municipal": rbac_municipal,
                "analista": rbac_analista,
                "campo": rbac_field,
            }
    finally:
        app.dependency_overrides.pop(get_async_db, None)
        app.dependency_overrides.pop(get_db, None)
        loop.run_until_complete(limpiar())
        loop.run_until_complete(motor.dispose())
        loop.close()


class TestEscriturasExigenPermiso:
    """`alerts:write` gobierna las 10 escrituras de `alert_admin.py`."""

    def test_401_sin_token(self, alertas):
        client, _ = alertas
        h = f"{ADMIN}/{EVENTO_PROPIO}"
        cuerpo = _alerta_json(EVENTO_PROPIO)

        assert client.post(f"{h}/alerts", json=cuerpo).status_code == 401
        assert client.put(f"{h}/alerts/{uuid4()}", json={"title": "X"}).status_code == 401
        assert client.patch(
            f"{h}/alerts/{uuid4()}/deactivate"
        ).status_code == 401
        assert client.delete(f"{h}/alerts/{uuid4()}").status_code == 401
        assert client.post(
            f"{h}/messages", json=_mensaje_json(EVENTO_PROPIO)
        ).status_code == 401
        assert client.put(
            f"{h}/messages/{uuid4()}", json={"title": "X"}
        ).status_code == 401
        assert client.patch(
            f"{h}/messages/{uuid4()}/publish"
        ).status_code == 401
        assert client.patch(
            f"{h}/messages/{uuid4()}/cancel"
        ).status_code == 401
        assert client.delete(f"{h}/messages/{uuid4()}").status_code == 401

    def test_403_analista_no_puede_publicar(self, alertas):
        """ANALISTA es de solo lectura: no tiene `alerts:write`.

        Este es el caso que motivó el arreglo. Con `verify_token` la escritura
        pasaba y un rol de análisis podía publicar avisos al público.
        """
        client, ctx = alertas
        h = f"{ADMIN}/{EVENTO_PROPIO}"
        headers = _auth(ctx["analista"])

        r = client.post(
            f"{h}/alerts", json=_alerta_json(EVENTO_PROPIO), headers=headers
        )
        assert r.status_code == 403
        assert r.json()["detail"] == "Permiso requerido: alerts:write"

        assert client.post(
            f"{h}/messages", json=_mensaje_json(EVENTO_PROPIO), headers=headers
        ).status_code == 403

    def test_403_analista_no_puede_borrar_ni_desactivar(self, alertas):
        client, ctx = alertas
        h = f"{ADMIN}/{EVENTO_AJENO}"
        headers = _auth(ctx["analista"])

        assert client.delete(
            f"{h}/alerts/{ctx['alerta_id']}", headers=headers
        ).status_code == 403
        assert client.patch(
            f"{h}/alerts/{ctx['alerta_id']}/deactivate", headers=headers
        ).status_code == 403
        assert client.delete(
            f"{h}/messages/{ctx['mensaje_id']}", headers=headers
        ).status_code == 403

    def test_operador_campo_si_puede(self, alertas):
        """OPERADOR_CAMPO tiene `alerts:write`: el panel no se le cierra."""
        client, ctx = alertas
        h = f"{ADMIN}/{EVENTO_PROPIO}"
        headers = _auth(ctx["campo"])

        r = client.post(
            f"{h}/alerts", json=_alerta_json(EVENTO_PROPIO), headers=headers
        )
        assert r.status_code == 201, r.text
        assert r.json()["title"] == "Corte de línea"

    def test_escrituras_con_permiso(self, alertas):
        """Ciclo completo con MUNICIPAL_ADMIN sobre su propio evento."""
        client, ctx = alertas
        h = f"{ADMIN}/{EVENTO_PROPIO}"
        headers = _auth(ctx["municipal"])

        creada = client.post(
            f"{h}/alerts", json=_alerta_json(EVENTO_PROPIO), headers=headers
        )
        assert creada.status_code == 201, creada.text
        alert_id = creada.json()["id"]

        assert client.get(f"{h}/alerts/{alert_id}", headers=headers).status_code == 200

        r = client.put(
            f"{h}/alerts/{alert_id}",
            json={"title": "Corte ampliado"},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["title"] == "Corte ampliado"

        assert client.patch(
            f"{h}/alerts/{alert_id}/deactivate", headers=headers
        ).status_code == 204
        assert client.delete(f"{h}/alerts/{alert_id}", headers=headers).status_code == 204

        creado = client.post(
            f"{h}/messages", json=_mensaje_json(EVENTO_PROPIO), headers=headers
        )
        assert creado.status_code == 201, creado.text
        message_id = creado.json()["id"]

        assert client.get(
            f"{h}/messages/{message_id}", headers=headers
        ).status_code == 200
        assert client.patch(
            f"{h}/messages/{message_id}/publish", headers=headers
        ).status_code == 200
        assert client.patch(
            f"{h}/messages/{message_id}/cancel", headers=headers
        ).status_code == 200
        assert client.delete(
            f"{h}/messages/{message_id}", headers=headers
        ).status_code == 204


class TestOwnershipPorEvento:
    """El `event_id` del path tiene que matchear al del recurso (anti-IDOR).

    Todas estas requests usan el permiso correcto y un token válido: lo único que
    cambia es que el `alert_id` / `message_id` pertenece a OTRO evento. Si el
    chequeo no estuviera, todas responderían 2xx y modificarían datos ajenos.
    """

    def test_el_recurso_propio_sigue_siendo_alcanzable(self, alertas):
        """Control: el 404 de abajo no puede deberse a un id inválido."""
        client, ctx = alertas
        r = client.get(
            f"{ADMIN}/{EVENTO_AJENO}/alerts/{ctx['alerta_id']}",
            headers=_auth(ctx["municipal"]),
        )
        assert r.status_code == 200
        assert r.json()["title"] == "Alerta del evento ajeno"

    def test_alerta_ajena_no_se_puede_editar(self, alertas):
        client, ctx = alertas
        r = client.put(
            f"{ADMIN}/{EVENTO_PROPIO}/alerts/{ctx['alerta_id']}",
            json={"title": "Secuestrada"},
            headers=_auth(ctx["municipal"]),
        )
        assert r.status_code == 404
        assert r.json()["detail"] == "TransportAlert not found"

    def test_alerta_ajena_no_se_puede_desactivar(self, alertas):
        client, ctx = alertas
        r = client.patch(
            f"{ADMIN}/{EVENTO_PROPIO}/alerts/{ctx['alerta_id']}/deactivate",
            headers=_auth(ctx["municipal"]),
        )
        assert r.status_code == 404

    def test_alerta_ajena_no_se_puede_borrar(self, alertas):
        client, ctx = alertas
        r = client.delete(
            f"{ADMIN}/{EVENTO_PROPIO}/alerts/{ctx['alerta_id']}",
            headers=_auth(ctx["municipal"]),
        )
        assert r.status_code == 404

        # Y el recurso sigue intacto: el 404 tiene que ser previo a cualquier
        # escritura, no el efecto de un borrado que igual devolvió 404.
        sigue = client.get(
            f"{ADMIN}/{EVENTO_AJENO}/alerts/{ctx['alerta_id']}",
            headers=_auth(ctx["municipal"]),
        )
        assert sigue.status_code == 200

    def test_mensaje_ajeno_no_se_puede_editar(self, alertas):
        client, ctx = alertas
        r = client.put(
            f"{ADMIN}/{EVENTO_PROPIO}/messages/{ctx['mensaje_id']}",
            json={"title": "Secuestrado"},
            headers=_auth(ctx["municipal"]),
        )
        assert r.status_code == 404
        assert r.json()["detail"] == "OperatorMessage not found"

    def test_mensaje_ajeno_no_se_puede_publicar_ni_cancelar(self, alertas):
        client, ctx = alertas
        for accion in ("publish", "cancel"):
            r = client.patch(
                f"{ADMIN}/{EVENTO_PROPIO}/messages/{ctx['mensaje_id']}/{accion}",
                headers=_auth(ctx["municipal"]),
            )
            assert r.status_code == 404, accion

    def test_mensaje_ajeno_no_se_puede_borrar(self, alertas):
        client, ctx = alertas
        r = client.delete(
            f"{ADMIN}/{EVENTO_PROPIO}/messages/{ctx['mensaje_id']}",
            headers=_auth(ctx["municipal"]),
        )
        assert r.status_code == 404

        sigue = client.get(
            f"{ADMIN}/{EVENTO_AJENO}/messages/{ctx['mensaje_id']}",
            headers=_auth(ctx["municipal"]),
        )
        assert sigue.status_code == 200

    def test_un_id_inexistente_tambien_da_404(self, alertas):
        """El ownership no se distingue del "no existe": mismo 404, mismo detalle."""
        client, ctx = alertas
        h = f"{ADMIN}/{EVENTO_PROPIO}"
        headers = _auth(ctx["municipal"])
        inexistente = str(uuid4())

        assert client.get(
            f"{h}/alerts/{inexistente}", headers=headers
        ).status_code == 404
        assert client.put(
            f"{h}/alerts/{inexistente}", json={"title": "X"}, headers=headers
        ).status_code == 404
        assert client.delete(
            f"{h}/messages/{inexistente}", headers=headers
        ).status_code == 404


class TestLecturasSiguenAbiertas:
    """Las lecturas no cambian: era una decisión, no un olvido.

    No existe un permiso `alerts:read`, así que restringirlas no aportaría nada:
    todos los roles que pueden escribir ya pueden leer. Lo que sí se verifica acá
    es que el token siga siendo obligatorio, porque `verify_token` no es "público".
    """

    def test_lectura_exige_token(self, alertas):
        client, _ = alertas
        h = f"{ADMIN}/{EVENTO_AJENO}"
        assert client.get(f"{h}/alerts").status_code == 401
        assert client.get(f"{h}/messages").status_code == 401

    def test_lectura_con_token(self, alertas):
        client, ctx = alertas
        h = f"{ADMIN}/{EVENTO_AJENO}"
        headers = _auth(ctx["analista"])

        assert client.get(f"{h}/alerts", headers=headers).status_code == 200
        assert client.get(f"{h}/messages", headers=headers).status_code == 200

    def test_la_lista_solo_muestra_el_evento_del_path(self, alertas):
        """`list_by_event` siempre filtró; el test lo fija para que no se rompa."""
        client, ctx = alertas
        headers = _auth(ctx["municipal"])

        propias = client.get(
            f"{ADMIN}/{EVENTO_PROPIO}/alerts", headers=headers
        ).json()
        ajenas = client.get(
            f"{ADMIN}/{EVENTO_AJENO}/alerts", headers=headers
        ).json()

        assert all(a["event_id"] == EVENTO_PROPIO for a in propias)
        assert all(a["event_id"] == EVENTO_AJENO for a in ajenas)
        assert not any(a["id"] == ctx["alerta_id"] for a in propias)