"""Tests de `require_permission` / `require_role` y del catalogo de permisos.

Dos cosas se verifican acá:

1. Que las dependencias hagan lo que dicen: 403 sin el permiso, 200 con el, y
   401 sin token. Un 403 donde deberia ser 401 (o al reves) tambien rompe clientes
   y hace que un 401 dispare un logout cuando no toca.

2. Que el catalogo de `app/core/permissions.py` no se desincronice de lo que
   siembra la migracion `a7c8e9f0a1b2`. Es el fallo caro de este diseno: un
   endpoint que pide `require_permission("observatons:write")` con typo queda
   inaccesible para todo el mundo, y la unica senal es un 403 en produccion.
"""
from __future__ import annotations

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import (
    CurrentUser,
    get_current_user,
    require_any_permission,
    require_permission,
    require_role,
)
from app.core.permissions import (
    ALL_PERMISSIONS,
    PERMISSION_CATALOG,
    ROLE_PERMISSIONS,
    parse_permission,
)

# ── Catalogo ─────────────────────────────────────────────────────────────────


class TestCatalogo:
    def test_codigos_tienen_el_formato_module_action(self):
        for code, module, action, _desc in PERMISSION_CATALOG:
            parsed_module, parsed_action = parse_permission(code)
            assert parsed_module == module
            assert parsed_action == action

    def test_no_hay_codigos_duplicados(self):
        codes = [c for c, _m, _a, _d in PERMISSION_CATALOG]
        assert len(codes) == len(set(codes))

    def test_todo_rol_referenciado_existe(self):
        for role_code in ROLE_PERMISSIONS:
            assert role_code in {
                "SUPER_ADMIN", "MUNICIPAL_ADMIN", "OPERADOR_CAMPO", "ANALISTA"
            }

    def test_los_permisos_de_un_rol_existen_en_el_catalogo(self):
        """Si un rol declara un permiso inexistente, el rol queda con un permiso
        fantasma y el endpoint protegido por el queda inaccesible."""
        for role_code, perms in ROLE_PERMISSIONS.items():
            for perm in perms:
                assert perm in ALL_PERMISSIONS, (
                    f"el rol {role_code} declara {perm!r}, que no esta en "
                    "PERMISSION_CATALOG"
                )

    def test_super_admin_tiene_todos_los_permisos(self):
        assert set(ROLE_PERMISSIONS["SUPER_ADMIN"]) == ALL_PERMISSIONS

    def test_operador_de_campo_es_mas_restringido_que_admin(self):
        """Least privilege, asserted. Si alguien suma un permiso al operador, esto
        falla y obliga a pensarlo."""
        assert set(ROLE_PERMISSIONS["OPERADOR_CAMPO"]) < set(
            ROLE_PERMISSIONS["MUNICIPAL_ADMIN"]
        )
        assert "users:write" not in ROLE_PERMISSIONS["OPERADOR_CAMPO"]
        assert "reports:read" not in ROLE_PERMISSIONS["OPERADOR_CAMPO"]

    def test_parse_permission_rechaza_formatos_invalidos(self):
        for malo in ("sin_dos_puntos", ":accion", "modulo:", ""):
            with pytest.raises(ValueError):
                parse_permission(malo)


class TestCurrentUserHelpers:
    def test_has_permission_exacto(self):
        u = CurrentUser(username="op", permissions=["counts:write"])
        assert u.has_permission("counts:write")
        assert not u.has_permission("users:write")

    def test_comodin_solo_lo_tiene_el_proveedor(self):
        normal = CurrentUser(username="op", permissions=["*"])
        assert normal.has_permission("lo-que-sea:quiera")
        assert not normal.has_role("CUALQUIER_ROL")

    def test_superuser_pasa_todo(self):
        u = CurrentUser(username="root", is_superuser=True)
        assert u.has_permission("lo-que-sea:quiera")
        assert u.has_role("NADA")

    def test_is_global_scope(self):
        global_ = CurrentUser(username="a", scopes=[])
        acotado = CurrentUser(
            username="b", scopes=[{"event_id": None, "zone_id": "z1"}]
        )
        assert global_.is_global_scope is True
        assert acotado.is_global_scope is False


# ── Dependencias ─────────────────────────────────────────────────────────────


def _build_app(user: CurrentUser | None) -> FastAPI:
    """App minima con endpoints protegidos por cada mecanismo.

    Ningun endpoint con codigo invalido: `require_permission` valida el codigo al
    importarse, asi que uno roto aborta la construccion de la app entera y no
    dejaria probar nada mas. Eso se verifica aparte, en
    `TestRequirePermissionFallaTemprano`.
    """
    app = FastAPI()
    router = APIRouter()

    def override() -> CurrentUser:
        if user is None:
            # Reproduce lo que hace `get_current_user` cuando no hay token.
            from fastapi import HTTPException, status

            raise HTTPException(status_code=401, detail="Not authenticated")
        return user

    app.dependency_overrides[get_current_user] = override

    @router.get("/permiso")
    def por_permiso(current: CurrentUser = Depends(require_permission("counts:write"))):
        return {"ok": True, "who": current.username}

    @router.get("/rol")
    def por_rol(current: CurrentUser = Depends(require_role("MUNICIPAL_ADMIN"))):
        return {"ok": True, "who": current.username}

    @router.get("/cualquiera")
    def por_cualquiera(
        current: CurrentUser = Depends(
            require_any_permission("users:write", "config:write")
        )
    ):
        return {"ok": True}

    app.include_router(router)
    return app


def _client(user: CurrentUser | None) -> TestClient:
    return TestClient(_build_app(user), raise_server_exceptions=False)


class TestRequirePermission:
    def test_con_el_permiso_pasa(self):
        c = _client(CurrentUser(username="op", permissions=["counts:write"]))
        r = c.get("/permiso")
        assert r.status_code == 200
        assert r.json()["who"] == "op"

    def test_sin_el_permiso_es_403(self):
        c = _client(CurrentUser(username="op", permissions=["observations:read"]))
        r = c.get("/permiso")
        assert r.status_code == 403
        assert "counts:write" in r.json()["detail"]

    def test_sin_usuario_es_401_no_403(self):
        """Sin token es 401, no 403.

        La distincion importa: un 403 confirmaria que hay una sesion activa y solo
        le falta un permiso, lo que le dice al cliente que no debería hacer logout.
        """
        c = _client(None)
        assert c.get("/permiso").status_code == 401

    def test_super_admin_pasa_sin_tener_el_permiso_listado(self):
        c = _client(CurrentUser(username="proveedor", is_provider_super_admin=True))
        assert c.get("/permiso").status_code == 200


class TestRequireRole:
    def test_con_el_rol_pasa(self):
        c = _client(CurrentUser(username="alcalde", roles=["MUNICIPAL_ADMIN"]))
        assert c.get("/rol").status_code == 200

    def test_sin_el_rol_es_403(self):
        c = _client(CurrentUser(username="op", roles=["OPERADOR_CAMPO"]))
        r = c.get("/rol")
        assert r.status_code == 403
        assert "MUNICIPAL_ADMIN" in r.json()["detail"]


class TestRequireAnyPermission:
    def test_pasa_con_alguno_de_los_dos(self):
        for perms in (["users:write"], ["config:write"]):
            c = _client(CurrentUser(username="u", permissions=perms))
            assert c.get("/cualquiera").status_code == 200

    def test_no_pasa_con_ninguno(self):
        c = _client(CurrentUser(username="u", permissions=["counts:write"]))
        assert c.get("/cualquiera").status_code == 403


class TestRequirePermissionFallaTemprano:
    """Un typo en el codigo de permiso tiene que romper el arranque, no el request."""

    def test_rechaza_un_codigo_sin_dos_puntos(self):
        with pytest.raises(ValueError):
            require_permission("sin_dos_puntos")

    def test_rechaza_un_modulo_vacio(self):
        with pytest.raises(ValueError):
            require_permission(":accion")

    def test_una_app_con_codigo_invalido_no_llega_a_registrar_rutas(self):
        app = FastAPI()

        with pytest.raises(ValueError):

            @app.get("/roto")
            def roto(current=Depends(require_permission("typo_sin_dos_puntos"))):
                return {}

        # Y por lo tanto la ruta ni existe.
        c = TestClient(app, raise_server_exceptions=False)
        assert c.get("/roto").status_code == 404