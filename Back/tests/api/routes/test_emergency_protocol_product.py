"""Tests del endpoint público GET /api/emergency-protocols (Emergencia V2 - S2).

Cubre:
- Contrato HTTP de la ruta: conteo por contexto, 422 por contexto inválido o
  ausente, query param ``active_only`` y orden determinístico.
- Respuestas vacías (lista, no 404) y acceso público sin token.

Patrón idéntico a test_emergency_product.py de V1: ``AsyncMock`` de
``get_async_db`` + ``app.dependency_overrides``.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_async_db
from app.models.emergency import EmergencyType
from app.models.emergency_protocol import EmergencyProtocol, EmergencyProtocolContext

BASE_URL = "/api/emergency-protocols"

FESTIVAL = EmergencyProtocolContext.FESTIVAL
TRANSPORTE = EmergencyProtocolContext.TRANSPORTE
HOSPEDAJE = EmergencyProtocolContext.HOSPEDAJE


def _make_protocol(
    context: EmergencyProtocolContext,
    title: str,
    priority: int,
    order: int,
    *,
    protocol_id: str | None = None,
    target_type: EmergencyType | None = None,
    active: bool = True,
) -> EmergencyProtocol:
    return EmergencyProtocol(
        id=protocol_id or str(uuid4()),
        context=context,
        title=title,
        description=f"Descripción de {title}",
        icon="🚨",
        steps=["Paso 1", "Paso 2", "Paso 3"],
        priority=priority,
        order=order,
        target_type=target_type,
        active=active,
    )


def _seed_all_protocols() -> list[EmergencyProtocol]:
    """Réplica del catálogo sembrado en Neon (4+4+3)."""
    return [
        _make_protocol(FESTIVAL, "Niño perdido", 1, 0, target_type=EmergencyType.policia),
        _make_protocol(FESTIVAL, "Persona herida", 1, 1, target_type=EmergencyType.salud),
        _make_protocol(FESTIVAL, "Robo o agresión", 2, 2, target_type=EmergencyType.policia),
        _make_protocol(FESTIVAL, "Intoxicación o descompensación", 2, 3, target_type=EmergencyType.salud),
        _make_protocol(TRANSPORTE, "Accidente", 1, 0),
        _make_protocol(TRANSPORTE, "Asalto", 1, 1),
        _make_protocol(TRANSPORTE, "Pasajero descompuesto", 2, 2),
        _make_protocol(TRANSPORTE, "Unidad averiada", 3, 3),
        _make_protocol(HOSPEDAJE, "Emergencia médica", 1, 0),
        _make_protocol(HOSPEDAJE, "Incendio", 1, 1),
        _make_protocol(HOSPEDAJE, "Robo", 2, 2),
    ]


def _override_db(rows: list[EmergencyProtocol]) -> AsyncMock:
    db = AsyncMock()
    result = MagicMock()
    scalars_result = MagicMock()
    scalars_result.all.return_value = rows
    result.scalars.return_value = scalars_result
    db.execute.return_value = result

    async def _fake_get_db():
        yield db

    app.dependency_overrides[get_async_db] = _fake_get_db
    return db


@pytest.fixture(autouse=True)
def _clean_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestEmergencyProtocolEndpoint:
    def test_get_protocols_festival_returns_4(self, client: TestClient):
        _override_db(_seed_all_protocols())
        resp = client.get(BASE_URL, params={"context": "festival"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["context"] == "festival"
        assert len(body["protocols"]) == 4

    def test_get_protocols_transporte_returns_4(self, client: TestClient):
        _override_db(_seed_all_protocols())
        resp = client.get(BASE_URL, params={"context": "transporte"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["context"] == "transporte"
        assert len(body["protocols"]) == 4

    def test_get_protocols_hospedaje_returns_3(self, client: TestClient):
        _override_db(_seed_all_protocols())
        resp = client.get(BASE_URL, params={"context": "hospedaje"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["context"] == "hospedaje"
        assert len(body["protocols"]) == 3

    def test_get_protocols_contexto_invalido_422(self, client: TestClient):
        _override_db([])
        resp = client.get(BASE_URL, params={"context": "invalido"})

        assert resp.status_code == 422

    def test_get_protocols_sin_contexto_422(self, client: TestClient):
        _override_db([])
        resp = client.get(BASE_URL)

        assert resp.status_code == 422

    def test_get_protocols_active_only_true_default(self, client: TestClient):
        rows = _seed_all_protocols()
        rows.append(
            _make_protocol(FESTIVAL, "Protocolo desactivado", 3, 9, active=False)
        )
        _override_db(rows)
        resp = client.get(BASE_URL, params={"context": "festival"})

        assert resp.status_code == 200
        body = resp.json()
        titles = [p["title"] for p in body["protocols"]]
        assert "Protocolo desactivado" not in titles
        assert len(body["protocols"]) == 4

    def test_get_protocols_active_only_false_incluye_inactivos(self, client: TestClient):
        rows = _seed_all_protocols()
        rows.append(
            _make_protocol(FESTIVAL, "Protocolo desactivado", 3, 9, active=False)
        )
        _override_db(rows)
        resp = client.get(
            BASE_URL, params={"context": "festival", "active_only": "false"}
        )

        assert resp.status_code == 200
        body = resp.json()
        titles = [p["title"] for p in body["protocols"]]
        assert "Protocolo desactivado" in titles
        assert len(body["protocols"]) == 5

    def test_get_protocols_ordenados_por_priority_order_id(self, client: TestClient):
        p1 = _make_protocol(
            FESTIVAL, "Prio2", priority=2, order=1,
            protocol_id="00000000-0000-0000-0000-000000000003",
        )
        p2 = _make_protocol(
            FESTIVAL, "Prio1orden1", priority=1, order=1,
            protocol_id="00000000-0000-0000-0000-000000000002",
        )
        p3 = _make_protocol(
            FESTIVAL, "Prio1orden0", priority=1, order=0,
            protocol_id="00000000-0000-0000-0000-000000000001",
        )
        p4 = _make_protocol(
            FESTIVAL, "IdB", priority=1, order=0,
            protocol_id="00000000-0000-0000-0000-00000000000b",
        )
        p5 = _make_protocol(
            FESTIVAL, "IdA", priority=1, order=0,
            protocol_id="00000000-0000-0000-0000-00000000000a",
        )
        _override_db([p5, p4, p3, p2, p1])  # desordenado a propósito

        resp = client.get(BASE_URL, params={"context": "festival"})

        assert resp.status_code == 200
        titles = [p["title"] for p in resp.json()["protocols"]]
        # priority ASC, luego order ASC, luego id ASC
        assert titles == ["Prio1orden0", "IdA", "IdB", "Prio1orden1", "Prio2"]

    def test_get_protocols_contexto_vacio_devuelve_lista_vacia(self, client: TestClient):
        _override_db([])
        resp = client.get(BASE_URL, params={"context": "festival"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["context"] == "festival"
        assert body["protocols"] == []

    def test_get_protocols_publico_sin_token(self, client: TestClient):
        _override_db(_seed_all_protocols())
        resp = client.get(BASE_URL, params={"context": "hospedaje"})

        assert resp.status_code == 200
        assert len(resp.json()["protocols"]) == 3