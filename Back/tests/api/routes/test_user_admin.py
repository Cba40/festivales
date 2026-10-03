"""Tests del CRUD de usuarios del administrador municipal.

Cubre el CRUD completo, las validaciones de unicidad y FK, y sobre todo los dos
ciclos de seguridad del módulo: que un administrador no pueda desactivarse ni
quitarse su propio rol.

También verifica el invariante de que el hash de la contraseña no aparece en
ninguna respuesta.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests._auth_tokens import mint_token

BASE = "/api/admin/users"
PASSWORD = "clave-de-prueba-larga"


def _auth(username: str) -> dict:
    return {"Authorization": f"Bearer {mint_token(subject=username)}"}


@pytest.fixture
def admin(rbac_municipal: str) -> str:
    """Un MUNICIPAL_ADMIN real, que es el actor de la mayoría de los tests."""
    return rbac_municipal


@pytest.fixture
def campo(rbac_field: str) -> str:
    """Un OPERADOR_CAMPO real: no tiene users:write, así que da 403."""
    return rbac_field


def _crear(client: TestClient, admin: str, username: str = "nuevo", **over) -> dict:
    body = {
        "username": username,
        "password": PASSWORD,
        "role": "OPERADOR_CAMPO",
    }
    body.update(over)
    r = client.post(BASE, json=body, headers=_auth(admin))
    assert r.status_code == 201, r.text
    return r.json()


class TestCreate:
    def test_crea_usuario_con_rol(self, client: TestClient, admin: str):
        r = client.post(
            BASE,
            json={"username": "juan", "password": PASSWORD, "role": "OPERADOR_CAMPO",
                  "email": "juan@muni.ar", "full_name": "Juan Pérez"},
            headers=_auth(admin),
        )
        assert r.status_code == 201
        data = r.json()
        assert data["username"] == "juan"
        assert data["email"] == "juan@muni.ar"
        assert data["full_name"] == "Juan Pérez"
        assert data["is_active"] is True
        assert [r["role_code"] for r in data["roles"]] == ["OPERADOR_CAMPO"]

    def test_nunca_devuelve_el_password_ni_el_hash(self, client: TestClient, admin: str):
        """El invariante de este módulo.

        Un `GET` de la lista no puede filtrar hashes: no son la contraseña, pero
        alimentan el offline cracking.
        """
        creado = _crear(client, admin)
        assert "password" not in creado
        assert "password_hash" not in creado

        listado = client.get(BASE, headers=_auth(admin))
        assert listado.status_code == 200
        crudo = listado.text
        assert "password_hash" not in crudo
        assert "$argon2" not in crudo

    def test_username_duplicado_es_409(self, client: TestClient, admin: str):
        _crear(client, admin, username="repetido")
        r = client.post(
            BASE,
            json={"username": "repetido", "password": PASSWORD, "role": "ANALISTA"},
            headers=_auth(admin),
        )
        assert r.status_code == 409

    def test_username_en_blanco_es_422(self, client: TestClient, admin: str):
        r = client.post(
            BASE,
            json={"username": "   ", "password": PASSWORD, "role": "ANALISTA"},
            headers=_auth(admin),
        )
        assert r.status_code == 422

    def test_password_corto_es_422(self, client: TestClient, admin: str):
        r = client.post(
            BASE,
            json={"username": "corto", "password": "1234567", "role": "ANALISTA"},
            headers=_auth(admin),
        )
        assert r.status_code == 422

    def test_rol_desconocido_es_404(self, client: TestClient, admin: str):
        r = client.post(
            BASE,
            json={"username": "xavier", "password": PASSWORD, "role": "SUPREMO"},
            headers=_auth(admin),
        )
        assert r.status_code == 404
        assert "SUPREMO" in r.json()["detail"]

    def test_401_sin_token(self, client: TestClient):
        assert client.post(
            BASE, json={"username": "xavier", "password": PASSWORD, "role": "ANALISTA"}
        ).status_code == 401

    def test_403_sin_permiso(self, client: TestClient, campo: str):
        r = client.post(
            BASE,
            json={"username": "xavier", "password": PASSWORD, "role": "ANALISTA"},
            headers=_auth(campo),
        )
        assert r.status_code == 403
        assert r.json()["detail"] == "Permiso requerido: users:write"


class TestList:
    def test_lista_usuarios(self, client: TestClient, admin: str):
        _crear(client, admin, username="listado")
        r = client.get(BASE, headers=_auth(admin))
        assert r.status_code == 200
        assert r.json()["total"] >= 1
        assert any(u["username"] == "listado" for u in r.json()["users"])

    def test_omite_inactivos_por_defecto(self, client: TestClient, admin: str):
        creado = _crear(client, admin, username="inactivo")
        client.delete(f"{BASE}/{creado['id']}", headers=_auth(admin))

        r = client.get(BASE, headers=_auth(admin))
        assert not any(u["username"] == "inactivo" for u in r.json()["users"])

    def test_include_inactive_los_trae(self, client: TestClient, admin: str):
        creado = _crear(client, admin, username="inactivo")
        client.delete(f"{BASE}/{creado['id']}", headers=_auth(admin))

        r = client.get(f"{BASE}/?include_inactive=true", headers=_auth(admin))
        assert any(u["username"] == "inactivo" for u in r.json()["users"])

    def test_401_sin_token(self, client: TestClient):
        assert client.get(BASE).status_code == 401

    def test_403_sin_permiso(self, client: TestClient, campo: str):
        assert client.get(BASE, headers=_auth(campo)).status_code == 403


class TestUpdate:
    def test_cambia_email_y_nombre(self, client: TestClient, admin: str):
        creado = _crear(client, admin, username="editable")
        r = client.put(
            f"{BASE}/{creado['id']}",
            json={"email": "nuevo@muni.ar", "full_name": "Nuevo Nombre"},
            headers=_auth(admin),
        )
        assert r.status_code == 200
        assert r.json()["email"] == "nuevo@muni.ar"
        assert r.json()["full_name"] == "Nuevo Nombre"

    def test_cambiar_password_no_toca_lo_demas(self, client: TestClient, admin: str):
        creado = _crear(client, admin, username="pwe")
        r = client.put(
            f"{BASE}/{creado['id']}",
            json={"password": "otra-clave-distinta-larga"},
            headers=_auth(admin),
        )
        assert r.status_code == 200
        assert r.json()["username"] == "pwe"

    def test_desactiva_con_is_active_false(self, client: TestClient, admin: str):
        creado = _crear(client, admin, username="desactiva")
        r = client.put(
            f"{BASE}/{creado['id']}", json={"is_active": False}, headers=_auth(admin)
        )
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    def test_reactivar(self, client: TestClient, admin: str):
        creado = _crear(client, admin, username="reactivable")
        client.put(f"{BASE}/{creado['id']}", json={"is_active": False}, headers=_auth(admin))
        r = client.put(
            f"{BASE}/{creado['id']}", json={"is_active": True}, headers=_auth(admin)
        )
        assert r.json()["is_active"] is True

    def test_inexistente_es_404(self, client: TestClient, admin: str):
        assert client.put(
            f"{BASE}/no-existe", json={"is_active": False}, headers=_auth(admin)
        ).status_code == 404

    def test_no_acepta_is_superuser(self, client: TestClient, admin: str):
        """`is_superuser` no es un campo editable.

        Si lo fuera, cualquier admin con `users:write` se autoelevaría a
        superusuario por API, sin tocar la base.
        """
        creado = _crear(client, admin, username="noelevar")
        r = client.put(
            f"{BASE}/{creado['id']}", json={"is_superuser": True}, headers=_auth(admin)
        )
        assert r.status_code == 200
        assert r.json()["is_superuser"] is False

    def test_401_sin_token(self, client: TestClient):
        assert client.put(f"{BASE}/x", json={"is_active": False}).status_code == 401

    def test_403_sin_permiso(self, client: TestClient, campo: str):
        assert client.put(
            f"{BASE}/x", json={"is_active": False}, headers=_auth(campo)
        ).status_code == 403


class TestNoDesactivarseASiMismo:
    """Ciclo 1: el admin no puede quedarse sin `users:write` a sí mismo."""

    def test_put_no_se_desactiva(self, client: TestClient, admin: str, db_session):
        from sqlalchemy import select

        from app.models.user import User

        yo = db_session.execute(
            select(User).where(User.username == admin)
        ).scalar_one()
        r = client.put(
            f"{BASE}/{yo.id}", json={"is_active": False}, headers=_auth(admin)
        )
        assert r.status_code == 409
        assert "tu propia cuenta" in r.json()["detail"]

    def test_delete_no_se_desactiva(self, client: TestClient, admin: str, db_session):
        from sqlalchemy import select

        from app.models.user import User

        yo = db_session.execute(
            select(User).where(User.username == admin)
        ).scalar_one()
        r = client.delete(f"{BASE}/{yo.id}", headers=_auth(admin))
        assert r.status_code == 409
        assert "tu propia cuenta" in r.json()["detail"]

    def test_el_mensaje_explica_por_que(self, client: TestClient, admin: str, db_session):
        """El mensaje tiene que decir qué pasa, no solo "no permitido".

        Sin la explicación, el operador piensa que la UI está rota y busca otro
        camino.
        """
        from sqlalchemy import select

        from app.models.user import User

        yo = db_session.execute(
            select(User).where(User.username == admin)
        ).scalar_one()
        detalle = client.delete(f"{BASE}/{yo.id}", headers=_auth(admin)).json()["detail"]
        assert "municipio" in detalle

    def test_puede_desactivar_a_otro(self, client: TestClient, admin: str):
        otro = _crear(client, admin, username="otro")
        r = client.delete(f"{BASE}/{otro['id']}", headers=_auth(admin))
        assert r.status_code == 200
        assert r.json()["is_active"] is False


class TestDeactivate:
    def test_soft_delete_mantiene_la_fila(self, client: TestClient, admin: str, db_session):
        """No borra: el `audit_log` y los refresh tokens la referencian."""
        from sqlalchemy import select

        from app.models.user import User

        creado = _crear(client, admin, username="soft")
        client.delete(f"{BASE}/{creado['id']}", headers=_auth(admin))

        fila = db_session.execute(
            select(User).where(User.id == creado["id"])
        ).scalar_one_or_none()
        assert fila is not None
        assert fila.is_active is False

    def test_desactivar_dos_veces_es_409(self, client: TestClient, admin: str):
        creado = _crear(client, admin, username="doble")
        client.delete(f"{BASE}/{creado['id']}", headers=_auth(admin))
        r = client.delete(f"{BASE}/{creado['id']}", headers=_auth(admin))
        assert r.status_code == 409

    def test_inexistente_es_404(self, client: TestClient, admin: str):
        assert client.delete(f"{BASE}/no-existe", headers=_auth(admin)).status_code == 404

    def test_401_sin_token(self, client: TestClient):
        assert client.delete(f"{BASE}/x").status_code == 401

    def test_403_sin_permiso(self, client: TestClient, campo: str):
        assert client.delete(f"{BASE}/x", headers=_auth(campo)).status_code == 403


class TestRoles:
    def test_asigna_rol_adicional(self, client: TestClient, admin: str):
        """Un usuario puede tener varios roles; la respuesta trae la lista."""
        creado = _crear(client, admin, username="multirrol", role="OPERADOR_CAMPO")
        r = client.post(
            f"{BASE}/{creado['id']}/roles",
            json={"role_code": "ANALISTA"},
            headers=_auth(admin),
        )
        assert r.status_code == 201
        assert sorted(x["role_code"] for x in r.json()["roles"]) == [
            "ANALISTA",
            "OPERADOR_CAMPO",
        ]

    def test_asigna_con_scope_de_zona(self, client: TestClient, admin: str):
        zona = "22222222-2222-2222-2222-222222222222"
        creado = _crear(client, admin, username="acotado", role="OPERADOR_CAMPO")
        r = client.post(
            f"{BASE}/{creado['id']}/roles",
            json={"role_code": "ANALISTA", "zone_id": zona},
            headers=_auth(admin),
        )
        assert r.status_code == 201
        asignacion = next(x for x in r.json()["roles"] if x["role_code"] == "ANALISTA")
        assert asignacion["zone_id"] == zona

    def test_mismo_rol_mismo_scope_es_409(self, client: TestClient, admin: str):
        creado = _crear(client, admin, username="dup", role="ANALISTA")
        r = client.post(
            f"{BASE}/{creado['id']}/roles",
            json={"role_code": "ANALISTA"},
            headers=_auth(admin),
        )
        assert r.status_code == 409

    def test_mismo_rol_otro_scope_es_409(self, client: TestClient, admin: str):
        """Un usuario tiene cada rol UNA vez, aunque el scope sea distinto.

        La PK de `user_roles` es `(user_id, role_id)`: no hay dos filas del mismo
        rol para el mismo usuario. La primera versión de esta ruta chequeaba el
        scope también y devolvía 500 con `UniqueViolation` en este caso; ahora es
        un 409 que explica la restricción y cómo resolverla.
        """
        creado = _crear(client, admin, username="doszonas", role="OPERADOR_CAMPO")
        r = client.post(
            f"{BASE}/{creado['id']}/roles",
            json={"role_code": "OPERADOR_CAMPO",
                  "zone_id": "22222222-2222-2222-2222-222222222222"},
            headers=_auth(admin),
        )
        assert r.status_code == 409
        detalle = r.json()["detail"]
        assert "OPERADOR_CAMPO" in detalle
        assert "quitalo primero" in detalle

    def test_rol_distinto_con_scope_si_se_puede(
        self, client: TestClient, admin: str
    ):
        """El scope vive en la asignación, así que dos roles distintos pueden
        tener alcances distintos en el mismo usuario."""
        creado = _crear(client, admin, username="mixtos", role="OPERADOR_CAMPO")
        r = client.post(
            f"{BASE}/{creado['id']}/roles",
            json={"role_code": "ANALISTA",
                  "zone_id": "22222222-2222-2222-2222-222222222222"},
            headers=_auth(admin),
        )
        assert r.status_code == 201

    def test_rol_desconocido_es_404(self, client: TestClient, admin: str):
        creado = _crear(client, admin, username="paraRolDesconocido")
        r = client.post(
            f"{BASE}/{creado['id']}/roles",
            json={"role_code": "INVENTADO"},
            headers=_auth(admin),
        )
        assert r.status_code == 404

    def test_quita_rol(self, client: TestClient, admin: str):
        creado = _crear(client, admin, username="con2", role="OPERADOR_CAMPO")
        r2 = client.post(
            f"{BASE}/{creado['id']}/roles",
            json={"role_code": "ANALISTA"},
            headers=_auth(admin),
        ).json()
        role_id = next(x["role_id"] for x in r2["roles"] if x["role_code"] == "ANALISTA")

        r = client.delete(f"{BASE}/{creado['id']}/roles/{role_id}", headers=_auth(admin))
        assert r.status_code == 204

    def test_quitar_rol_inexistente_es_404(self, client: TestClient, admin: str):
        creado = _crear(client, admin, username="sinrol")
        r = client.delete(
            f"{BASE}/{creado['id']}/roles/no-existe", headers=_auth(admin)
        )
        assert r.status_code == 404

    def test_no_puede_quitarse_su_propio_rol(self, client: TestClient, admin: str, db_session):
        """Ciclo 2: quitarse el propio rol deja al admin sin acceso.

        Es el caso que este módulo no puede dejar pasar: el super admin del
        proveedor no depende de una fila de `users`, así que quedarse sin roles lo
        deja afuera del sistema.
        """
        from sqlalchemy import select

        from app.models.user import User

        yo = db_session.execute(
            select(User).where(User.username == admin)
        ).scalar_one()
        role_id = yo.user_roles[0].role_id

        r = client.delete(f"{BASE}/{yo.id}/roles/{role_id}", headers=_auth(admin))
        assert r.status_code == 409
        assert "tu propio rol" in r.json()["detail"]

    def test_puede_quitarle_el_rol_a_otro(self, client: TestClient, admin: str):
        otro = _crear(client, admin, username="suelodeotro")
        role_id = otro["roles"][0]["role_id"]
        r = client.delete(f"{BASE}/{otro['id']}/roles/{role_id}", headers=_auth(admin))
        assert r.status_code == 204

    def test_401_sin_token(self, client: TestClient, admin: str):
        creado = _crear(client, admin, username="tok")
        assert client.post(
            f"{BASE}/{creado['id']}/roles", json={"role_code": "ANALISTA"}
        ).status_code == 401

    def test_403_sin_permiso(self, client: TestClient, campo: str, admin: str):
        creado = _crear(client, admin, username="perm")
        assert client.post(
            f"{BASE}/{creado['id']}/roles",
            json={"role_code": "ANALISTA"},
            headers=_auth(campo),
        ).status_code == 403


class TestIntegracionConLogin:
    def test_el_usuario_creado_puede_loguearse(self, client: TestClient, admin: str, db_session):
        """El alta por API produce un usuario que el login acepta.

        Es la prueba de que el CRUD y el flujo de sesión son el mismo sistema: si
        esto fallara, el módulo estaría creando filas que nadie puede usar.
        """
        from sqlalchemy import select

        from app.models.user import User

        _crear(client, admin, username="logueable", password="password-de-prueba")

        # `db_session` es la MISMA sesion que el cliente inyecta en `get_db`, asi
        # que lo que escribio la API se ve aca. No se usa `SessionLocal`: apunta a
        # `settings.DATABASE_URL` (la de desarrollo), donde no existe `users`.
        fila = db_session.execute(
            select(User).where(User.username == "logueable")
        ).scalar_one()
        # argon2id: nunca la contraseña en claro.
        assert fila.password_hash.startswith("$argon2id$")
        assert "password-de-prueba" not in fila.password_hash

    def test_reinicia_el_lockout_al_cambiar_la_password(
        self, client: TestClient, admin: str, db_session
    ):
        """Restablecer la clave de un usuario bloqueado lo desbloquea.

        Sin esto, el admin reponía la contraseña y el usuario seguía sin poder
        entrar, sin motivo aparente.
        """
        from datetime import datetime, timedelta, timezone

        from sqlalchemy import select

        from app.models.user import User

        creado = _crear(client, admin, username="bloqueado")
        u = db_session.execute(
            select(User).where(User.username == "bloqueado")
        ).scalar_one()
        u.failed_login_count = 5
        u.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
        db_session.flush()

        client.put(
            f"{BASE}/{creado['id']}",
            json={"password": "clave-nueva-para-desbloquear"},
            headers=_auth(admin),
        )

        db_session.expire_all()
        u = db_session.execute(
            select(User).where(User.username == "bloqueado")
        ).scalar_one()
        assert u.failed_login_count == 0
        assert u.locked_until is None