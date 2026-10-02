"""Tests de autorización de los módulos admin de Emergencia (Fase 4 del RBAC).

Cubre `emergency_admin.py` y `emergency_protocol_admin.py`, que hasta ahora no
tenían ningún test de ruta: por eso sus `verify_token` nunca se llegaron a
cuestionar.

El contrato que se verifica:

* Las **escrituras** exigen su permiso: 401 sin token, 403 sin el permiso,
  201/200/204 con el permiso.
* Las **lecturas de admin** siguen públicas, como documenta cada módulo. No es un
  olvido: el test existe para fijar que NO se cierran. Cerrarlas sería quitarle
  acceso a un panel que hoy lo tiene.
* Los dos dominios no comparten prefijo de permiso: `protocols:write` (observación)
  no habilita `emergency_protocols:write` (emergencia), ni al revés.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests._auth_tokens import mint_token

ADMIN = "/api/admin"


def _auth(username: str) -> dict:
    """Header de un usuario que existe en la base.

    El token sale de la misma función que el login real, pero lo que decide el
    acceso es la fila en `users`: `get_current_user` relee roles y permisos de ahí,
    para que revocar un permiso surta efecto inmediato y no 15 minutos después,
    cuando expira el access token.
    """
    return {"Authorization": f"Bearer {mint_token(subject=username)}"}


@pytest.fixture
def municipal(rbac_municipal: str) -> str:
    return rbac_municipal


@pytest.fixture
def campo(rbac_field: str) -> str:
    return rbac_field


@pytest.fixture
def ciudad(client: TestClient, municipal: str) -> dict:
    """Ciudad creada por un admin. Es el padre de las emergencias."""
    r = client.post(
        f"{ADMIN}/cities",
        json={"name": "Ciudad de Prueba", "province": "Buenos Aires"},
        headers=_auth(municipal),
    )
    assert r.status_code == 201, r.text
    return r.json()


def _emergencia(ciudad_id: str, name: str = "Hospital Central") -> dict:
    # `type` usa el enum EmergencyType: policia, bomberos, salud, defensa_civil,
    # numero_emergencia, otro. No es un string libre.
    return {"city_id": ciudad_id, "name": name, "type": "salud"}


def _protocolo(title: str = "Evacuación") -> dict:
    # `icon` y `priority` son obligatorios en ProtocolCreate; `context` es un enum
    # (festival / transporte / hospedaje).
    return {
        "context": "festival",
        "title": title,
        "icon": "exit",
        "steps": ["Avisar", "Dirigir"],
        "priority": 1,
    }


class TestLecturasPublicasNoSeCierran:
    """Estas tres lecturas quedan PÚBLICAS a propósito.

    Cada módulo lo documenta (`emergency_admin.py` y `emergency_protocol_admin.py`,
    ambos "lecturas públicas"), y existen endpoints ciudadano equivalentes en los
    módulos product: `emergency.py` sirve `/api/cities` y `/api/emergencies`, y
    `emergency_protocol.py` sirve `/api/emergency-protocols`, los tres sin token.

    Que exista además la versión bajo `/api/admin` es duplicación de prefijo, no
    una política de acceso. De-duplicarlas es una tarea aparte.
    """

    def test_get_cities_es_publico(self, client: TestClient, ciudad: dict):
        r = client.get(f"{ADMIN}/cities")
        assert r.status_code == 200
        assert any(c["id"] == ciudad["id"] for c in r.json())

    def test_get_emergencies_es_publico(self, client: TestClient, ciudad: dict, municipal: str):
        creada = client.post(
            f"{ADMIN}/emergencies", json=_emergencia(ciudad["id"]), headers=_auth(municipal)
        )
        assert creada.status_code == 201, creada.text

        r = client.get(f"{ADMIN}/emergencies", params={"city_id": ciudad["id"]})
        assert r.status_code == 200
        assert any(e["name"] == "Hospital Central" for e in r.json())

    def test_get_emergency_protocols_es_publico(self, client: TestClient):
        assert client.get(f"{ADMIN}/emergency-protocols").status_code == 200

    def test_un_token_invalido_no_rompe_la_lectura_publica(self, client: TestClient):
        """Un `Authorization` basura no debe volver 401 una ruta pública.

        El interceptor del frontend manda el token siempre; si se corrompe, las
        rutas públicas tienen que seguir sirviendo igual.
        """
        r = client.get(
            f"{ADMIN}/emergency-protocols", headers={"Authorization": "Bearer basura"}
        )
        assert r.status_code == 200


class TestEmergencyAdminEscrituras:
    """`emergency:write` gobierna las 4 escrituras de emergencia_admin."""

    def test_401_sin_token(self, client: TestClient, ciudad: dict):
        assert client.post(f"{ADMIN}/cities", json={"name": "X"}).status_code == 401
        r = client.post(
            f"{ADMIN}/emergencies", json=_emergencia(ciudad["id"])
        )
        assert r.status_code == 401
        assert client.put(
            f"{ADMIN}/emergencies/algo", json={"name": "Y"}
        ).status_code == 401
        assert client.delete(f"{ADMIN}/emergencies/algo").status_code == 401

    def test_403_sin_el_permiso(self, client: TestClient, ciudad: dict, campo: str):
        """OPERADOR_CAMPO tiene `emergency:read` pero no `emergency:write`."""
        r = client.post(
            f"{ADMIN}/emergencies",
            json=_emergencia(ciudad["id"]),
            headers=_auth(campo),
        )
        assert r.status_code == 403
        assert r.json()["detail"] == "Permiso requerido: emergency:write"

    def test_403_no_le_deja_crear_ciudades(self, client: TestClient, campo: str):
        r = client.post(f"{ADMIN}/cities", json={"name": "Otra"}, headers=_auth(campo))
        assert r.status_code == 403

    def test_403_no_le_deja_borrar(
        self, client: TestClient, ciudad: dict, municipal: str, campo: str
    ):
        creada = client.post(
            f"{ADMIN}/emergencies",
            json=_emergencia(ciudad["id"], "Sala"),
            headers=_auth(municipal),
        ).json()
        assert client.delete(
            f"{ADMIN}/emergencies/{creada['id']}", headers=_auth(campo)
        ).status_code == 403

    def test_403_no_le_deja_editar(
        self, client: TestClient, ciudad: dict, municipal: str, campo: str
    ):
        creada = client.post(
            f"{ADMIN}/emergencies",
            json=_emergencia(ciudad["id"], "Sala"),
            headers=_auth(municipal),
        ).json()
        r = client.put(
            f"{ADMIN}/emergencies/{creada['id']}",
            json={"name": "Renombrada"},
            headers=_auth(campo),
        )
        assert r.status_code == 403

    def test_201_con_permiso(self, client: TestClient, ciudad: dict, municipal: str):
        r = client.post(
            f"{ADMIN}/emergencies",
            json=_emergencia(ciudad["id"], "Bombero"),
            headers=_auth(municipal),
        )
        assert r.status_code == 201
        assert r.json()["name"] == "Bombero"

    def test_put_y_delete_con_permiso(
        self, client: TestClient, ciudad: dict, municipal: str
    ):
        creada = client.post(
            f"{ADMIN}/emergencies",
            json=_emergencia(ciudad["id"], "Sala"),
            headers=_auth(municipal),
        ).json()
        h = _auth(municipal)

        r = client.put(
            f"{ADMIN}/emergencies/{creada['id']}",
            json={"name": "Sala Nueva"},
            headers=h,
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Sala Nueva"

        assert client.delete(f"{ADMIN}/emergencies/{creada['id']}", headers=h).status_code == 204


class TestEmergencyProtocolAdminEscrituras:
    """`emergency_protocols:write` gobierna las 3 escrituras del catálogo."""

    def test_401_sin_token(self, client: TestClient):
        assert client.post(
            f"{ADMIN}/emergency-protocols", json=_protocolo()
        ).status_code == 401
        assert client.put(
            f"{ADMIN}/emergency-protocols/algo", json={"title": "X"}
        ).status_code == 401
        assert client.delete(f"{ADMIN}/emergency-protocols/algo").status_code == 401

    def test_403_sin_el_permiso(self, client: TestClient, campo: str):
        r = client.post(
            f"{ADMIN}/emergency-protocols", json=_protocolo(), headers=_auth(campo)
        )
        assert r.status_code == 403
        assert r.json()["detail"] == "Permiso requerido: emergency_protocols:write"

    def test_201_con_permiso(self, client: TestClient, municipal: str):
        r = client.post(
            f"{ADMIN}/emergency-protocols", json=_protocolo(), headers=_auth(municipal)
        )
        assert r.status_code == 201
        assert r.json()["title"] == "Evacuación"

    def test_put_y_delete_con_permiso(self, client: TestClient, municipal: str):
        creada = client.post(
            f"{ADMIN}/emergency-protocols", json=_protocolo(), headers=_auth(municipal)
        ).json()
        h = _auth(municipal)

        r = client.put(
            f"{ADMIN}/emergency-protocols/{creada['id']}",
            json={"title": "Evacuación v2"},
            headers=h,
        )
        assert r.status_code == 200
        assert r.json()["title"] == "Evacuación v2"

        assert client.delete(
            f"{ADMIN}/emergency-protocols/{creada['id']}", headers=h
        ).status_code == 204


class TestPermisosNoSeConfunden:
    """Los dos dominios no comparten prefijo de permiso.

    `protocols:*` es del módulo de Protocolos de Control de Observaciones;
    `emergency_protocols:*` es del catálogo de emergencia. Que compartieran el
    string haría que un usuario con lectura de protocolos de observación ganara
    automáticamente los de emergencia, sin que nadie lo decidiera.
    """

    def test_emergencia_write_no_habilita_protocolos_de_emergencia(
        self, client: TestClient, campo: str
    ):
        """`emergency:*` es de emergencias, no del catálogo de protocolos.

        Si se mezclaran, editar una emergencia habilitaría reescribir el protocolo
        de evacuación. Son cosas distintas.
        """
        r = client.post(
            f"{ADMIN}/emergency-protocols", json=_protocolo(), headers=_auth(campo)
        )
        assert r.status_code == 403
        assert "emergency_protocols" in r.json()["detail"]

    def test_la_lectura_publica_no_habilita_escritura(
        self, client: TestClient, ciudad: dict
    ):
        """El riesgo real de este lote: abrir lecturas puede hacer creer que
        "emergencias" quedó accesible para cualquiera, cuando en realidad el GET
        sigue abierto y lo protegido es exactamente lo que debe estarlo."""
        assert client.get(
            f"{ADMIN}/emergencies", params={"city_id": ciudad["id"]}
        ).status_code == 200
        assert client.post(
            f"{ADMIN}/emergencies", json=_emergencia(ciudad["id"])
        ).status_code == 401

    def test_el_operador_conserva_su_acceso_de_lectura(
        self, client: TestClient, campo: str
    ):
        """`emergency_protocols:read` va también a OPERADOR_CAMPO a propósito.

        El GET era público hasta este lote. No darle el permiso sería quitarle un
        acceso que ya tenía: least privilege es "no dar más de lo que ya podía",
        no "dejarlo afuera de algo que ya leía".
        """
        assert client.get(f"{ADMIN}/emergency-protocols", headers=_auth(campo)).status_code == 200

    def test_quitar_el_permiso_corta_el_acceso_al_instante(
        self, client: TestClient, municipal: str, db_session
    ):
        """Revocar el rol surte efecto en el request siguiente.

        Es la razón de que `get_current_user` relea la base: confiando en los
        claims del JWT, esto tardaría hasta 15 minutos.
        """
        from sqlalchemy import delete

        from app.models.user import UserRole

        assert client.post(
            f"{ADMIN}/cities", json={"name": "Antes"}, headers=_auth(municipal)
        ).status_code == 201

        u = db_session.query(__import__("app.models.user", fromlist=["User"]).User).filter_by(
            username=municipal
        ).one()
        db_session.execute(delete(UserRole).where(UserRole.user_id == u.id))
        db_session.flush()
        db_session.expire_all()

        assert client.post(
            f"{ADMIN}/cities", json={"name": "Despues"}, headers=_auth(municipal)
        ).status_code == 403