"""Catálogo canónico de permisos y roles.

Este módulo es la **única fuente de verdad** de los códigos. Deben coincidir
exactamente con lo que siembra `alembic/versions/a7c8e9f0a1b2_rbac_*.py`.

Por qué un catálogo en código y no leerlo solo de la base
--------------------------------------------------------
`require_permission("observations:write")` escribe el código como string en el
código. Si ese string no existiera en `permissions`, el endpoint quedaría
inaccesible para todos y la única señal sería un 403 en producción, sin validación
que lo anticipara en el CI.

Por eso el catálogo vive acá, en Python, y hay un test (`test_permissions.py`) que
compara este conjunto contra lo que la migración siembra y contra lo que hay en la
base. Un permiso escrito a mano en un endpoint pero ausente del catálogo se
detecta en CI, no en producción.

Formato: `module:action`. `module` agrupa para la UI ("todos los permisos de
observations"), `action` es el verbo.
"""

from __future__ import annotations

# ── Roles ────────────────────────────────────────────────────────────────────

ROLE_SUPER_ADMIN = "SUPER_ADMIN"
ROLE_MUNICIPAL_ADMIN = "MUNICIPAL_ADMIN"
ROLE_OPERADOR_CAMPO = "OPERADOR_CAMPO"
ROLE_ANALISTA = "ANALISTA"

ALL_ROLES = (
    ROLE_SUPER_ADMIN,
    ROLE_MUNICIPAL_ADMIN,
    ROLE_OPERADOR_CAMPO,
    ROLE_ANALISTA,
)

# ── Permisos ─────────────────────────────────────────────────────────────────

# Identidad
USERS_READ = "users:read"
USERS_WRITE = "users:write"
ROLES_READ = "roles:read"
AUDIT_READ = "audit:read"

# Eventos y configuracion territorial
EVENTS_READ = "events:read"
EVENTS_WRITE = "events:write"

# Operacion en campo
OBSERVATIONS_READ = "observations:read"
OBSERVATIONS_WRITE = "observations:write"
COUNTS_WRITE = "counts:write"

# Configuracion operativa
CONFIG_READ = "config:read"
CONFIG_WRITE = "config:write"
PROTOCOLS_READ = "protocols:read"
PROTOCOLS_WRITE = "protocols:write"
EMERGENCY_READ = "emergency:read"
EMERGENCY_WRITE = "emergency:write"
# Protocolos de emergencia, que son un catálogo DISTINTO al de los Protocolos de
# Control de Observaciones. No se reutiliza `protocols:*` a proposito: ese prefijo
# ya lo usa el modulo de observacion, y compartirlo haria que un usuario con
# lectura de protocolos de observacion ganara tambien los de emergencia, que son
# otra cosa y otro modulo.
EMERGENCY_PROTOCOLS_READ = "emergency_protocols:read"
EMERGENCY_PROTOCOLS_WRITE = "emergency_protocols:write"

# Analisis
REPORTS_READ = "reports:read"
ANALYTICS_READ = "analytics:read"
ANALYTICS_WRITE = "analytics:write"
AUDIT_LOG_READ = "audit_log:read"

# Tupla (code, module, action, description). Tiene que reflejar 1:1 la siembra de
# la migración.
PERMISSION_CATALOG: tuple[tuple[str, str, str, str], ...] = (
    (USERS_READ, "users", "read", "Ver usuarios y sus roles"),
    (USERS_WRITE, "users", "write", "Crear y editar usuarios y asignaciones de rol"),
    (ROLES_READ, "roles", "read", "Ver roles y permisos"),
    (AUDIT_READ, "audit", "read", "Leer la bitacora de operaciones"),
    (EVENTS_READ, "events", "read", "Ver eventos, jornadas y zonas"),
    (EVENTS_WRITE, "events", "write", "Crear y editar eventos, jornadas y zonas"),
    (OBSERVATIONS_READ, "observations", "read", "Ver observaciones"),
    (OBSERVATIONS_WRITE, "observations", "write", "Registrar y editar observaciones"),
    (COUNTS_WRITE, "counts", "write", "Cargar conteos de personas y vehiculos"),
    (CONFIG_READ, "config", "read", "Ver configuracion operativa"),
    (CONFIG_WRITE, "config", "write", "Editar configuracion operativa"),
    (PROTOCOLS_READ, "protocols", "read", "Ver protocolos de control ySugerencias"),
    (PROTOCOLS_WRITE, "protocols", "write", "Gestionar protocolos de control"),
    (EMERGENCY_READ, "emergency", "read", "Ver emergencias y protocolos"),
    (EMERGENCY_WRITE, "emergency", "write", "Gestionar emergencias y protocolos"),
    (
        EMERGENCY_PROTOCOLS_READ,
        "emergency_protocols",
        "read",
        "Ver el catalogo de protocolos de emergencia",
    ),
    (
        EMERGENCY_PROTOCOLS_WRITE,
        "emergency_protocols",
        "write",
        "Gestionar el catalogo de protocolos de emergencia",
    ),
    (REPORTS_READ, "reports", "read", "Ver reportes globales"),
    (ANALYTICS_READ, "analytics", "read", "Ver analytics y recomendaciones"),
    (ANALYTICS_WRITE, "analytics", "write", "Resolver recomendaciones"),
    (AUDIT_LOG_READ, "audit_log", "read", "Ver la bitacora de recomendaciones"),
)

ALL_PERMISSIONS: frozenset[str] = frozenset(c for c, _m, _a, _d in PERMISSION_CATALOG)

# Qué permisos tiene cada rol. Debe reflejar 1:1 la siembra de la migración.
ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    # Acceso total. Ojo: este mapa documenta qué llevaría el rol si estuviera en
    # la tabla, pero el super admin real NO se resuelve por acá: entra por
    # variables de entorno y su token trae `perms=["*"]`. Ver `app/api/deps.py`.
    ROLE_SUPER_ADMIN: tuple(sorted(ALL_PERMISSIONS)),
    ROLE_MUNICIPAL_ADMIN: (
        USERS_READ, USERS_WRITE, ROLES_READ, AUDIT_READ,
        EVENTS_READ, EVENTS_WRITE,
        OBSERVATIONS_READ, OBSERVATIONS_WRITE, COUNTS_WRITE,
        CONFIG_READ, CONFIG_WRITE,
        PROTOCOLS_READ, PROTOCOLS_WRITE,
        EMERGENCY_READ, EMERGENCY_WRITE,
        EMERGENCY_PROTOCOLS_READ, EMERGENCY_PROTOCOLS_WRITE,
        REPORTS_READ, ANALYTICS_READ, ANALYTICS_WRITE, AUDIT_LOG_READ,
    ),
    ROLE_OPERADOR_CAMPO: (
        EVENTS_READ,
        OBSERVATIONS_READ, OBSERVATIONS_WRITE,
        COUNTS_WRITE,
        # `emergency_protocols:read` acompana a `emergency:read`: los dos dejan
        # consultar el procedimiento. El GET que ahora exige este permiso era
        # PUBLICO hasta esta migracion, asi que no otorgarselo le quitaria al
        # operador un acceso que ya tenia. Least privilege aca quiere decir "no
        # darle MAS de lo que ya podia", no "dejarlo afuera de algo que ya leia".
        EMERGENCY_READ, EMERGENCY_PROTOCOLS_READ,
    ),
    ROLE_ANALISTA: (
        EVENTS_READ, OBSERVATIONS_READ, COUNTS_WRITE,
        REPORTS_READ, ANALYTICS_READ, AUDIT_LOG_READ,
        PROTOCOLS_READ, EMERGENCY_READ, EMERGENCY_PROTOCOLS_READ,
    ),
}

# Comodín del super admin del proveedor. No es un permiso de la tabla
# `permissions`: se reconoce directamente en `require_permission` para no meter
# una fila "mágica" en la base del cliente.
SUPER_PERMISSION_WILDCARD = "*"


def is_known_permission(code: str) -> bool:
    return code in ALL_PERMISSIONS


def parse_permission(code: str) -> tuple[str, str]:
    """Parte `module:action`. Lanza `ValueError` si el formato es inválido."""
    module, sep, action = code.partition(":")
    if not sep or not module or not action:
        raise ValueError(
            f"código de permiso inválido: {code!r}. Se espera 'module:action'."
        )
    return module, action