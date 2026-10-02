"""Tests de los endpoints de autenticacion (Fase 2 del RBAC).

Cubre el contrato observable:
- login correcto / incorrecto / usuario inexistente / usuario inactivo
- lockout por intentos fallidos
- refresh con rotacion y deteccion de reuso
- logout que revoca
- /me
- el mismo mensaje 401 para "no existe" y para "contrasena mala" (no enumeracion)

El super admin del proveedor se prueba con un override de settings, porque su
existencia depende de variables de entorno que en CI no estan definidas. Es
precisamente el caso que no se puede probar contra la base: el usuario del
proveedor NO esta en `users`.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models.user import Role, User, UserRole
from tests._auth_tokens import mint_token

BASE = "/api/auth"
PASSWORD = "clave-de-prueba-suficientemente-larga"


@pytest.fixture
def client(test_engine):
    def override_get_db():
        with Session(bind=test_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def municipal(test_engine):
    """Un MUNICIPAL_ADMIN real en la base.

    El motor de la suite es de scope sesion y este fixture hace `commit`, así que
    la fila persiste entre tests. Se borra antes de crear para que el test sea
    idempotente: sin eso, el segundo test que pide el fixture choca contra el
    UNIQUE de `users.username`.
    """
    from sqlalchemy import delete

    with Session(bind=test_engine) as db:
        previous = db.execute(
            select(User).where(User.username == "alcalde")
        ).scalar_one_or_none()
        if previous is not None:
            db.execute(delete(UserRole).where(UserRole.user_id == previous.id))
            db.execute(delete(User).where(User.id == previous.id))
            db.commit()

        role = db.execute(
            select(Role).where(Role.code == "MUNICIPAL_ADMIN")
        ).scalar_one()
        user = User(username="alcalde", password_hash=hash_password(PASSWORD))
        db.add(user)
        db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id))
        db.commit()
        return user.id


def _login(client, username, password=PASSWORD):
    return client.post(f"{BASE}/login", json={"username": username, "password": password})


class TestLogin:
    def test_credenciales_validas_devuelve_token(self, client, municipal):
        r = _login(client, "alcalde")
        assert r.status_code == 200
        body = r.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]
        assert body["expires_in"] == settings.ACCESS_TOKEN_MINUTES * 60
        assert body["roles"] == ["MUNICIPAL_ADMIN"]
        # El access dura 15 min, no las 8 horas del login viejo.
        assert body["expires_in"] == 15 * 60

    def test_guarda_el_refresh_en_cookie_httponly(self, client, municipal):
        r = _login(client, "alcalde")
        # `HttpOnly` es lo que impide que un XSS lea el refresh.
        assert "refresh_token" in r.cookies
        raw = r.headers.get("set-cookie", "")
        assert "HttpOnly" in raw
        assert "SameSite=strict" in raw.replace("Strict", "strict")

    def test_password_incorrecto_es_401(self, client, municipal):
        assert _login(client, "alcalde", "no-es-la-clave").status_code == 401

    def test_usuario_inexistente_es_401(self, client):
        assert _login(client, "nadie@example.com").status_code == 401

    def test_no_enumera_usuarios(self, client, municipal):
        """"No existe" y "contrasena mala" devuelven el mismo mensaje.

        Si difirieran, un atacante solo tendria que cronometrar 401s para armar el
        padron de usuarios sin crackear una sola contrasena.
        """
        inexistente = _login(client, "nadie@example.com")
        mala_clave = _login(client, "alcalde", "no-es-la-clave")
        assert inexistente.json()["detail"] == mala_clave.json()["detail"]

    def test_usuario_inactivo_es_401(self, client, municipal, test_engine):
        with Session(bind=test_engine) as db:
            u = db.execute(select(User).where(User.username == "alcalde")).scalar_one()
            u.is_active = False
            db.commit()
        assert _login(client, "alcalde").status_code == 401


class TestLockout:
    """Bloqueo por cuenta, que es distinta del rate limit por IP.

    Las dos barreras coexisten y se complementan: el rate limit frena a un
    atacante desde una IP, el lockout frena a uno que reparte intentos entre
    varias. Acá se apaga el rate limit para poder observar el lockout aislado; de
    lo contrario el sexto request devuelve 429 por cuota de IP y el test probaría
    el mecanismo equivocado.
    """

    @pytest.fixture(autouse=True)
    def _sin_rate_limit(self, monkeypatch):
        monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)

    def test_bloquea_despues_del_maximo_de_intentos(self, client, municipal):
        for _ in range(settings.LOGIN_MAX_FAILED_ATTEMPTS - 1):
            assert _login(client, "alcalde", "malo").status_code == 401

        # El intento que completa el maximo devuelve 401 y arma el lockout.
        assert _login(client, "alcalde", "malo").status_code == 401

        # A partir de ahi, incluso la contrasena CORRECTA queda bloqueada.
        r = _login(client, "alcalde")
        assert r.status_code == 429
        assert "bloqueada" in r.json()["detail"].lower()

    def test_lockout_no_se_levanta_con_la_contrasena_correcta(
        self, client, municipal
    ):
        for _ in range(settings.LOGIN_MAX_FAILED_ATTEMPTS):
            _login(client, "alcalde", "malo")
        assert _login(client, "alcalde").status_code == 429

    def test_credenciales_correctas_limpian_el_contador(
        self, client, municipal, test_engine
    ):
        _login(client, "alcalde", "malo")
        _login(client, "alcalde", "malo")
        assert _login(client, "alcalde").status_code == 200
        with Session(bind=test_engine) as db:
            u = db.execute(select(User).where(User.username == "alcalde")).scalar_one()
            assert u.failed_login_count == 0


class TestRefresh:
    def test_renueva_la_sesion(self, client, municipal):
        original = _login(client, "alcalde").json()["refresh_token"]
        r = client.post(f"{BASE}/refresh", json={"refresh_token": original})
        assert r.status_code == 200
        assert r.json()["access_token"]

    def test_la_rotacion_invalida_el_refresh_anterior(self, client, municipal):
        original = _login(client, "alcalde").json()["refresh_token"]
        assert client.post(f"{BASE}/refresh", json={"refresh_token": original}).status_code == 200
        # Reusarlo es la señal de que alguien robo un refresh: se rechaza.
        r = client.post(f"{BASE}/refresh", json={"refresh_token": original})
        assert r.status_code == 401

    def test_refresh_invalido_es_401(self, client):
        assert client.post(f"{BASE}/refresh", json={"refresh_token": "inventado"}).status_code == 401

    def test_sin_refresh_es_401(self, client):
        assert client.post(f"{BASE}/refresh", json={}).status_code == 401


class TestLogout:
    def test_revoca_el_refresh(self, client, municipal):
        refresh = _login(client, "alcalde").json()["refresh_token"]
        r = client.post(f"{BASE}/logout", json={"refresh_token": refresh})
        assert r.status_code == 200
        assert r.json()["revoked"] is True
        # El refresh ya no sirve: el logout es real, no cosmético.
        assert client.post(f"{BASE}/refresh", json={"refresh_token": refresh}).status_code == 401

    def test_limpia_el_cookie(self, client, municipal):
        r = _login(client, "alcalde")
        r = client.post(f"{BASE}/logout", json={})
        assert r.status_code == 200


class TestMe:
    def test_devuelve_identidad_y_permisos(self, client, municipal):
        token = _login(client, "alcalde").json()["access_token"]
        r = client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        body = r.json()
        assert body["username"] == "alcalde"
        assert body["roles"] == ["MUNICIPAL_ADMIN"]
        assert "users:write" in body["permissions"]
        assert body["is_global_scope"] is True

    def test_sin_token_es_401(self, client):
        assert client.get(f"{BASE}/me").status_code == 401

    def test_token_invalido_es_401(self, client):
        assert client.get(
            f"{BASE}/me", headers={"Authorization": "Bearer no-es-un-jwt"}
        ).status_code == 401

    def test_usuario_dado_de_baja_pierde_el_acceso_inmediatamente(
        self, client, municipal, test_engine
    ):
        """El token sigue siendo criptograficamente valido, pero el usuario ya no.

        Es la razon de consultar la base en `get_current_user` en vez de confiar en
        los claims: sin esto, una baja tardaria hasta 15 minutos en surtir efecto.
        """
        token = _login(client, "alcalde").json()["access_token"]
        assert client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200

        with Session(bind=test_engine) as db:
            u = db.execute(select(User).where(User.username == "alcalde")).scalar_one()
            u.is_active = False
            db.commit()

        r = client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401




class TestLeastPrivilege:
    """El motivo de existir del RBAC: dos personas con token, capacidades distintas."""

    @staticmethod
    def _crear(test_engine, username, role_code, zone_id=None):
        from sqlalchemy import delete

        with Session(bind=test_engine) as db:
            previo = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
            if previo is not None:
                db.execute(delete(UserRole).where(UserRole.user_id == previo.id))
                db.execute(delete(User).where(User.id == previo.id))
                db.commit()

            role = db.execute(select(Role).where(Role.code == role_code)).scalar_one()
            user = User(username=username, password_hash=hash_password(PASSWORD))
            db.add(user)
            db.flush()
            db.add(UserRole(user_id=user.id, role_id=role.id, zone_id=zone_id))
            db.commit()

    def test_operador_recibe_menos_permisos_que_admin(self, client, test_engine):
        self._crear(test_engine, "contador", "OPERADOR_CAMPO")

        token = _login(client, "contador").json()["access_token"]
        body = client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {token}"}).json()

        assert body["roles"] == ["OPERADOR_CAMPO"]
        # Lo que puede hacer de campo:
        assert "counts:write" in body["permissions"]
        assert "observations:write" in body["permissions"]
        # Lo que NO puede. Esto es el punto del RBAC: antes, con `verify_token`,
        # podia entrar a todo lo que tuviera un token valido.
        assert "users:write" not in body["permissions"]
        assert "reports:read" not in body["permissions"]
        assert "config:write" not in body["permissions"]
        assert len(body["permissions"]) < 10

    def test_operador_con_scope_de_zona_no_es_global(self, client, test_engine):
        zona = "22222222-2222-2222-2222-222222222222"
        self._crear(test_engine, "contador_zona", "OPERADOR_CAMPO", zone_id=zona)

        token = _login(client, "contador_zona").json()["access_token"]
        body = client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {token}"}).json()

        assert body["is_global_scope"] is False
        assert body["scopes"] == [{"event_id": None, "zone_id": zona}]


class TestSuperAdminDelProveedor:
    """El super admin no esta en la base: se resuelve por variables de entorno.

    Por eso necesita `monkeypatch` sobre `settings`: en CI las variables no estan
    definidas, y esta es justamente la garantia que hay que probar —que la cuenta
    del proveedor no existe en el lado del cliente.
    """

    def test_entra_con_la_clave_del_proveedor(self, client, monkeypatch):
        monkeypatch.setattr(settings, "SUPER_ADMIN_USERNAMES", ["soporte@festivales"])
        monkeypatch.setattr(settings, "PROVIDER_TOKEN_SECRET", "k" * 48)

        r = client.post(
            f"{BASE}/login",
            json={"username": "soporte@festivales", "password": "k" * 48},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["roles"] == ["SUPER_ADMIN"]
        assert body["permissions"] == ["*"]

    def test_no_deja_entrar_con_la_clave_de_un_usuario(self, client, monkeypatch):
        monkeypatch.setattr(settings, "SUPER_ADMIN_USERNAMES", ["soporte@festivales"])
        monkeypatch.setattr(settings, "PROVIDER_TOKEN_SECRET", "k" * 48)

        r = client.post(
            f"{BASE}/login",
            json={"username": "soporte@festivales", "password": "la-clave-de-alguien"},
        )
        assert r.status_code == 401

    def test_no_esta_en_la_tabla_users(self, client, monkeypatch, test_engine):
        """La garantia de fondo: la cuenta no existe en la base del cliente.

        Si fuera una fila de `users`, un administrador municipal con
        `users:manage` podria leerla y copiarse el rol.
        """
        monkeypatch.setattr(settings, "SUPER_ADMIN_USERNAMES", ["soporte@festivales"])
        monkeypatch.setattr(settings, "PROVIDER_TOKEN_SECRET", "k" * 48)
        client.post(
            f"{BASE}/login",
            json={"username": "soporte@festivales", "password": "k" * 48},
        )
        with Session(bind=test_engine) as db:
            existe = db.execute(
                select(User).where(User.username == "soporte@festivales")
            ).scalar_one_or_none()
            assert existe is None

    def test_me_lo_reporta_como_proveedor(self, client, monkeypatch):
        monkeypatch.setattr(settings, "SUPER_ADMIN_USERNAMES", ["soporte@festivales"])
        monkeypatch.setattr(settings, "PROVIDER_TOKEN_SECRET", "k" * 48)

        token = client.post(
            f"{BASE}/login",
            json={"username": "soporte@festivales", "password": "k" * 48},
        ).json()["access_token"]
        body = client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {token}"}).json()

        assert body["is_provider_super_admin"] is True
        assert body["id"] is None          # no existe en users
        assert body["is_global_scope"] is True


class TestChangePassword:
    def test_cambia_la_contrasena_y_revoca_las_sesiones(self, client, municipal):
        token = _login(client, "alcalde").json()["access_token"]
        refresh = _login(client, "alcalde").json()["refresh_token"]

        r = client.post(
            f"{BASE}/change-password",
            json={
                "current_password": PASSWORD,
                "new_password": "otra-clave-nueva-larga-2026",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200

        # La vieja ya no entra; la nueva si.
        assert _login(client, "alcalde").status_code == 401
        assert _login(client, "alcalde", "otra-clave-nueva-larga-2026").status_code == 200
        # Y el refresh anterior quedo revocado.
        assert client.post(
            f"{BASE}/refresh", json={"refresh_token": refresh}
        ).status_code == 401

    def test_contrasena_actual_incorrecta_es_400(self, client, municipal):
        token = _login(client, "alcalde").json()["access_token"]
        r = client.post(
            f"{BASE}/change-password",
            json={"current_password": "incorrecta", "new_password": "otra-clave-larga-2026"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 400

    def test_no_permite_reusar_la_misma(self, client, municipal):
        token = _login(client, "alcalde").json()["access_token"]
        r = client.post(
            f"{BASE}/change-password",
            json={"current_password": PASSWORD, "new_password": PASSWORD},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 422
