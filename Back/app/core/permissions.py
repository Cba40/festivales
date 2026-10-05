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

# Acciones de campo: reportar un incidente y publicar una alerta o un mensaje al
# publico. NO son `emergency:*`.
#
# Por que un prefijo nuevo y no reusar `emergency:write`
# ------------------------------------------------------
# `emergency:write` protege el CRUD del catalogo de PUNTOS de emergencia y de
# ciudades (`app/api/routes/emergency_admin.py`), que es configuracion de
# infraestructura. Las acciones de campo son otra cosa: son escritura del operador
# sobre la operacion del evento. Meterlas en `emergency:write` obligaria a elegir
# entre dos cosas incompatibles: o el operador no puede reportar nada, o puede
# crear y borrar puntos de emergencia. Por eso son codigos aparte, y por eso
# `emergency:write` sigue reservado a quien administra la infraestructura.
#
# Sin pareja `:read` a proposito, igual que `counts:write`. Las lecturas de
# alertas y mensajes siguen exigiendo solo token (`alert_admin.py` usa
# `verify_token` en `list_by_event` y `get`), asi que un permiso de lectura no
# restringiria nada: pasaria a ser otro permiso que todos los roles con
# `alerts:write` ya tienen.
#
# `ALERTS_WRITE` si se aplica: las 9 escrituras de `alert_admin.py` (crear,
# actualizar, desactivar y eliminar alertas; crear, actualizar, publicar, cancelar
# y eliminar mensajes) exigen `require_permission("alerts:write")`. Antes solo
# pedian token, con lo que cualquier cuenta autenticada -incluido ANALISTA, que es
# de solo lectura- podia publicar o borrar avisos de seguridad al publico. Los
# operadores de campo lo tienen (`ROLE_OPERADOR_CAMPO`), asi que el panel sigue
# funcionando.
#
# `INCIDENTS_WRITE` sigue sin uso: no hay endpoints de incidentes que lo pidan
# (`operational_events.py` expone `is_incident` como dato, no como recurso). Si
# alguna vez los hay, es el momento de agregar tambien `incidents:read`.
ALERTS_WRITE = "alerts:write"
INCIDENTS_WRITE = "incidents:write"

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
    (ALERTS_WRITE, "alerts", "write", "Publicar y gestionar alertas y mensajes al publico"),
    (INCIDENTS_WRITE, "incidents", "write", "Reportar y gestionar incidentes operativos"),
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
        ALERTS_WRITE, INCIDENTS_WRITE,
        REPORTS_READ, ANALYTICS_READ, ANALYTICS_WRITE, AUDIT_LOG_READ,
    ),
    ROLE_OPERADOR_CAMPO: (
        # `observations:read` sigue aunque la accion de campo sea
        # `observations:write`: la tarjeta "Registrar Observacion" lleva a la
        # pantalla de observaciones, y sin lectura esa pantalla no se abre. Es la
        # lectura que ya tenia, no un permiso nuevo.
        OBSERVATIONS_READ, OBSERVATIONS_WRITE,
        COUNTS_WRITE,
        # Reportar incidentes y publicar alertas: las dos acciones de campo que lo
        # justifican. Le dan acceso a `/dashboard/operational-events` y
        # `/dashboard/alerts`, que hoy solo exigen token.
        ALERTS_WRITE, INCIDENTS_WRITE,
        # `emergency:read` y `emergency_protocols:read` acompanan al operador para
        # que pueda consultar el procedimiento de emergencia cuando lo necesita.
        # El GET de protocolos era PUBLICO hasta `b8d9e0f1a2b3`, asi que no
        # otorgarselo le quitaria un acceso que ya tenia. Least privilege aca
        # quiere decir "no darle MAS de lo que ya podia", no "dejarlo afuera de algo
        # que ya leia". `emergency:write` NO va aca: es configuracion de
        # infraestructura, no operacion de campo.
        EMERGENCY_READ, EMERGENCY_PROTOCOLS_READ,
        # Sin `events:read` a proposito: con el, el operador habilita la pestaña de
        # predicciones del motor, que es analisis y no carga de campo. Los
        # permisos de analisis (`reports:read`, `analytics:read`) tampoco estan, y
        # por la misma razon.
    ),
    ROLE_ANALISTA: (
        # Rol de solo lectura sobre lo que analiza. Ni `counts:write` ni ningun
        # otro `:write`: cargar conteos o publicar una alerta es operacion de
        # campo, no analisis.
        EVENTS_READ, OBSERVATIONS_READ,
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