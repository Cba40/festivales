"""Tests de ``GET /api/events/active``.

Este endpoint es la fuente de verdad del ``event_id`` del frontend: reemplaza a
``import.meta.env.VITE_EVENT_ID``, que Vite horneaba en el bundle al compilar. Con
la variable de entorno, cambiar de evento exigía redeploy y un valor obsoleto en
``.env`` hacia que la app pidiera datos de un evento inexistente (el 404 "No se
encontraron zonas para el evento").

Dos decisiones que los tests fijan:

1. Sin autenticación. El frente público (mapa de zonas, barra de estado) consulta
   este endpoint antes de que exista sesión; exigir token lo dejaría sin
   ``event_id`` justamente en el caso de uso abierto.
2. Orden de rutas: ``/active`` tiene que declararse antes de ``/{event_id}`` o
   FastAPI lo matchea contra el path param y devuelve 404. Hay un test dedicado a
   esto porque es un fallo silencioso hasta que alguien lo deploya.

No usa base de datos: se sobreescribe ``get_db`` con un mock de la sesión sync.
"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app

ENDPOINT = "/api/events/active"

EVENT_ID = "663e6e32-9d4a-4f20-b992-3585b9310522"
OTHER_EVENT_ID = "2d4f210e-63ad-488c-a02e-44daa8945898"


def _day(day_id: str, event_id: str, day: date, is_active: bool = True):
    return SimpleNamespace(id=day_id, event_id=event_id, date=day, is_active=is_active)


def _db_mock(hoy=None, mas_reciente=None, event_name="Festival de Jesús María 2026"):
    """Session sync mockeada.

    ``get_active_event`` hace dos ``db.query()`` con argumentos distintos: uno sobre
    el modelo ``EventDay`` para elegir la jornada, otro sobre la columna
    ``Event.name`` para traer el nombre. No se distinguen por el modelo sino por
    tener atributo ``class_``: una columna de SQLAlchemy lo tiene, una entidad no.

    Cada ``.first()`` sobre ``EventDay`` avanza al siguiente candidato: primero la
    jornada de hoy, después la activa más reciente.
    """
    day_rows = [r for r in (hoy, mas_reciente) if r is not None]
    db = MagicMock()

    def query(arg):
        q = MagicMock()
        if getattr(arg, "class_", None) is None:
            # Entidad: la búsqueda de la jornada.
            seq = iter(day_rows)
            q.filter.return_value.order_by.return_value.first.side_effect = (
                lambda: next(seq, None)
            )
        else:
            # Columna (`Event.name`): el nombre del evento.
            q.filter.return_value.scalar.return_value = event_name
        return q

    db.query.side_effect = query
    return db


@pytest.fixture(autouse=True)
def _clean_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _override(db):
    def override():
        yield db

    app.dependency_overrides[get_db] = override


class TestResolveActiveEvent:
    def test_devuelve_el_evento_de_la_jornada_de_hoy(self, client: TestClient):
        _override(_db_mock(hoy=_day("d1", EVENT_ID, date.today())))

        resp = client.get(ENDPOINT)

        assert resp.status_code == 200
        body = resp.json()
        assert body["event_id"] == EVENT_ID
        assert body["event_day_id"] == "d1"
        assert body["event_name"] == "Festival de Jesús María 2026"
        assert body["date"] == date.today().isoformat()

    def test_es_el_evento_real_y_no_un_id_inventado(self, client: TestClient):
        """El 663e6e32... es el evento con zonas; el 2d4f210e... está vacío.

        Este test documenta por qué el endpoint existe: pedir con el valor que
        estaba en `.env` devolvía cero zonas, y el error que llegaba a la UI
        ("No se encontraron zonas para el evento") no señalaba la causa real.
        """
        _override(_db_mock(hoy=_day("d1", EVENT_ID, date.today())))

        body = client.get(ENDPOINT).json()

        assert body["event_id"] == EVENT_ID
        assert body["event_id"] != OTHER_EVENT_ID

    def test_sin_jornada_de_hoy_usa_la_activa_mas_reciente(self, client: TestClient):
        """Prevención y rehearsal: se consulta fuera del día de evento."""
        _override(
            _db_mock(
                hoy=None,
                mas_reciente=_day("d9", EVENT_ID, date(2026, 7, 15)),
            )
        )

        resp = client.get(ENDPOINT)

        assert resp.status_code == 200
        assert resp.json()["event_day_id"] == "d9"

    def test_404_sin_ninguna_jornada_activa(self, client: TestClient):
        """Sin jornada no hay ID que inventar.

        Un fallback hardcodeado sería justamente el bug que este endpoint elimina:
        devolvería un ID inexistente y cada request volvería a fallar en 404
        opaco. El 404 en cambio es accionable ("configurá una jornada").
        """
        _override(_db_mock(hoy=None, mas_reciente=None))

        resp = client.get(ENDPOINT)

        assert resp.status_code == 404
        assert resp.json()["detail"] == "No hay evento activo configurado"

    def test_no_devuelve_un_fallback_hardcodeado(self, client: TestClient):
        _override(_db_mock(hoy=None, mas_reciente=None))

        resp = client.get(ENDPOINT)

        assert resp.status_code != 200
        assert "default-event-id" not in resp.text


class TestPublicAccess:
    def test_no_exige_token(self, client: TestClient):
        """El frente público consulta esto sin sesión.

        Si el endpoint exigiera token, ``ZoneList`` y ``EventStatusBar``
        arrancarían sin ``event_id``, que es exactamente el caso de uso abierto
        de la app.
        """
        _override(_db_mock(hoy=_day("d1", EVENT_ID, date.today())))

        resp = client.get(ENDPOINT)

        assert resp.status_code == 200


class TestRouteOrdering:
    def test_active_no_cae_en_el_path_param_event_id(self, client: TestClient):
        """`/active` debe ganarle a `/{event_id}`.

        FastAPI matchea en orden de registro. Si el endpoint viviera después de
        `GET /api/events/{event_id}`, esta request entraría por el path param con
        ``event_id="active"`` y devolvería 404 "Event not found" — el mismo
        síntoma que el bug original, y sin ningún error de compilación que lo
        delate.
        """
        _override(_db_mock(hoy=_day("d1", EVENT_ID, date.today())))

        resp = client.get(ENDPOINT)

        assert resp.status_code == 200
        assert resp.json()["event_id"] == EVENT_ID

    def test_event_id_lista_sigue_funcionando(self, client: TestClient):
        """La reordenación no rompe la ruta parametrizada existente."""
        db = MagicMock()
        evento = SimpleNamespace(
            id=EVENT_ID,
            name="Festival de Jesús María 2026",
            description=None,
            location=None,
            start_date=None,
            end_date=None,
            reference_point_latitude=None,
            reference_point_longitude=None,
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
        )
        db.query.return_value.filter.return_value.first.return_value = evento

        def override():
            yield db

        from tests._auth_tokens import mint_token

        app.dependency_overrides[get_db] = override
        resp = client.get(
            f"/api/events/{EVENT_ID}",
            headers={"Authorization": f"Bearer {mint_token()}"},
        )

        assert resp.status_code == 200
        assert resp.json()["id"] == EVENT_ID