"""Tests de los modelos de identidad contra Postgres real.

Estos tests usan el motor de la suite, con `create_all` desde el metadata, asi que
ejercitan el DDL de verdad: FKs, UNIQUE y CHECK. No alcanza con un mock porque el
que mas falla en un esquema de identidad es justamente una FK o una restriccion mal
declarada.

Lo que se cubre:
- unicidad de `username`
- el CHECK de `failed_login_count >= 0`
- el CHECK de `permissions.code` con dos puntos
- `ON DELETE CASCADE` de `user_roles` al borrar el usuario
- el scope opcional de `user_roles` (NULL = global)
- `roles.code` en mayusculas (CHECK)
- `refresh_tokens` borra en cascada con el usuario
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import Permission, RefreshToken, Role, User, UserRole


@pytest.fixture
def rol(db_session: Session) -> Role:
    """Usa el rol sembrado por el fixture de sesion de conftest."""
    return db_session.execute(
        select(Role).where(Role.code == "OPERADOR_CAMPO")
    ).scalar_one()


def _usuario(db: Session, username: str) -> User:
    u = User(username=username, password_hash=hash_password("clave-larga-de-prueba"))
    db.add(u)
    db.flush()
    return u


class TestUser:
    def test_crea_usuario(self, db_session: Session):
        u = _usuario(db_session, "operador1")
        assert u.id
        assert u.is_active is True
        assert u.is_superuser is False
        assert u.failed_login_count == 0

    def test_username_es_unico(self, db_session: Session, rol: Role):
        _usuario(db_session, "duplicado")
        db_session.add(User(username="duplicado", password_hash=hash_password("x" * 20)))
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_password_hash_se_persiste(self, db_session: Session):
        u = _usuario(db_session, "conpassword")
        fila = db_session.execute(
            select(User).where(User.id == u.id)
        ).scalar_one()
        # Nunca en claro: se guarda argon2id.
        assert fila.password_hash.startswith("$argon2id$")
        assert "clave-larga-de-prueba" not in fila.password_hash

    def test_hashes_distintos_para_la_misma_contrasena(self, db_session: Session):
        """Dos usuarios con la misma contraseña tienen hashes distintos.

        Si no, un atacante quetumbe la tabla vería que dos usuarios comparten
        contraseña solo con comparar columnas.
        """
        u1 = _usuario(db_session, "misma1")
        u2 = _usuario(db_session, "misma2")
        u1.password_hash = hash_password("exactamente-la-misma")
        u2.password_hash = hash_password("exactamente-la-misma")
        assert u1.password_hash != u2.password_hash

    def test_check_de_failed_login_count(self, db_session: Session):
        u = _usuario(db_session, "negativo")
        u.failed_login_count = -1
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()


class TestRoleYPermission:
    def test_roles_sembrados(self, db_session: Session):
        codigos = {
            r.code
            for r in db_session.execute(select(Role)).scalars()
        }
        assert {"SUPER_ADMIN", "MUNICIPAL_ADMIN", "OPERADOR_CAMPO", "ANALISTA"} <= codigos

    def test_codigo_de_rol_en_mayusculas(self, db_session: Session):
        from sqlalchemy import CheckConstraint  # noqa: F401  (documenta el CHECK)

        db_session.add(Role(code="minusculas", name="x"))
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_permiso_invalido_sin_dos_puntos(self, db_session: Session):
        db_session.add(
            Permission(code="sin_dos_puntos", module="x", action="y")
        )
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_permisos_se_descomponen(self, db_session: Session):
        p = db_session.execute(
            select(Permission).where(Permission.code == "observations:write")
        ).scalar_one()
        assert p.module == "observations"
        assert p.action == "write"


class TestUserRole:
    def test_asignacion_con_scope_global(self, db_session: Session, rol: Role):
        u = _usuario(db_session, "global1")
        db_session.add(UserRole(user_id=u.id, role_id=rol.id))
        db_session.flush()
        asignacion = db_session.execute(
            select(UserRole).where(UserRole.user_id == u.id)
        ).scalar_one()
        assert asignacion.event_id is None
        assert asignacion.zone_id is None

    def test_asignacion_acotada_a_zona(self, db_session: Session, rol: Role):
        u = _usuario(db_session, "acotado1")
        zona = str(uuid.uuid4())
        db_session.add(UserRole(user_id=u.id, role_id=rol.id, zone_id=zona))
        db_session.flush()
        asignacion = db_session.execute(
            select(UserRole).where(UserRole.user_id == u.id)
        ).scalar_one()
        assert asignacion.zone_id == zona

    def test_misma_asignacion_dos_veces_falla(self, db_session: Session, rol: Role):
        """La PK compuesta (user_id, role_id) impide duplicar el rol."""
        u = _usuario(db_session, "duprol1")
        db_session.add(UserRole(user_id=u.id, role_id=rol.id))
        db_session.flush()
        db_session.add(UserRole(user_id=u.id, role_id=rol.id))
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_borrar_usuario_arrastra_sus_asignaciones(self, db_session: Session, rol: Role):
        """`ON DELETE CASCADE`: no quedan roles huerfanos apuntando a un id que no
        existe. Con `SET NULL` quedarian filas invalidas y `get_current_user`
        resolveria un rol de alguien que ya no esta."""
        u = _usuario(db_session, "cascada1")
        db_session.add(UserRole(user_id=u.id, role_id=rol.id))
        db_session.flush()

        db_session.delete(u)
        db_session.flush()

        assert db_session.execute(
            select(UserRole).where(UserRole.user_id == u.id)
        ).scalars().all() == []

    def test_relacion_de_lectura_trae_roles_y_permisos(
        self, db_session: Session, rol: Role
    ):
        u = _usuario(db_session, "lectura1")
        db_session.add(UserRole(user_id=u.id, role_id=rol.id))
        db_session.flush()
        db_session.refresh(u)

        assert [ur.role.code for ur in u.user_roles] == ["OPERADOR_CAMPO"]
        permisos = {rp.permission.code for rp in u.user_roles[0].role.role_permissions}
        assert "counts:write" in permisos
        assert "users:write" not in permisos


class TestRefreshToken:
    def test_se_persiste_con_hash_del_token(self, db_session: Session):
        u = _usuario(db_session, "refresh1")
        jti = str(uuid.uuid4())
        db_session.add(
            RefreshToken(
                jti=jti,
                user_id=u.id,
                token_hash="a" * 64,
                expires_at=datetime.now(timezone.utc),
            )
        )
        db_session.flush()
        # Filtrado por `jti`: el motor de la suite es de scope sesion y los tests
        # de auth hacen commit, asi que puede haber refresh de otros usuarios.
        fila = db_session.execute(
            select(RefreshToken).where(RefreshToken.jti == jti)
        ).scalar_one()
        # Se guarda el SHA-256, nunca el token: si alguien lee la tabla no puede
        # suplantar la sesion.
        assert len(fila.token_hash) == 64

    def test_borrar_usuario_revoca_sus_refresh(self, db_session: Session):
        u = _usuario(db_session, "refresh2")
        jti = str(uuid.uuid4())
        db_session.add(
            RefreshToken(
                jti=jti,
                user_id=u.id,
                token_hash="b" * 64,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            )
        )
        db_session.flush()

        db_session.delete(u)
        db_session.flush()

        # Acotado al usuario borrado: otros usuarios pueden tener refresh vivos.
        assert db_session.execute(
            select(RefreshToken).where(RefreshToken.user_id == u.id)
        ).scalars().all() == []


class TestAuditLog:
    def test_actor_es_nullable_para_el_proveedor(self, db_session: Session):
        """El super admin no existe en `users`, asi que su auditoria va con
        `actor_user_id=NULL` y el username desnormalizado."""
        from app.models.user import AuditLog

        db_session.add(
            AuditLog(
                actor_user_id=None,
                actor_username="soporte@festivales",
                action="auth.login",
                ip="1.2.3.4",
                created_at=datetime.now(timezone.utc),
            )
        )
        db_session.flush()
        fila = db_session.execute(select(AuditLog)).scalar_one()
        assert fila.actor_user_id is None
        assert fila.actor_username == "soporte@festivales"