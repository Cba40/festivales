-- ============================================================================
--  AUDITORIA DE PRODUCCION (solo lectura)
--
--  PARA: Neon -> SQL Editor. Pegar y ejecutar el bloque COMPLETO.
--
--  QUE ES Y QUE NO ES
--  ------------------
--  Este script NO escribe, NO inserta y NO altera nada: son 100% SELECT.
--  Sirve para saber en que estado esta produccion ANTES de correr
--  `repair_motor_configs.sql` o `repair_service_config_banos.sql`.
--
--  COMO LEERLO
--  -----------
--  Cada bloque tiene una columna `accion` que dice que hacer. Los tres que
--  importan son:
--
--    · `FALTA LA MIGRACION d2a4b6c8e0f1` -> correr alembic upgrade head.
--      OJO: esa migracion tambien REVOCA `events:read` a OPERADOR_CAMPO y
--      `counts:write` a ANALISTA. Ver BLOQUE 8.
--    · `VACIA -> hay que insertar`          -> correr repair_motor_configs.sql.
--    · `FALTA EL DEFAULT GLOBAL`            -> correr repair_service_config_banos.sql.
--      OJO: si `slug_servicios` y `slug_bano` dan 0, el script de reparacion
--      avisa por NOTICE y NO inserta. Ver BLOQUE 3.
--
--  LO QUE ESTE SCRIPT NO PUEDE DECIR
--  ----------------------------------
--  Cuantas zonas tienen `saturation_level` HOY. No hay forma de saberlo con
--  SQL: el campo se calcula en cada request y el endpoint publico llama a
--  `PredictionModule.execute(persist=False)`, o sea que no se escribe en
--  ninguna tabla. `predictions.zone_states_data` existe, pero solo la llenan
--  los flujos con `persist=True` y puede estar vieja.
--  Para el numero real hay que pegarle a GET /api/events/{id}/predictions y
--  contar los `saturation_level` no nulos. Ver BLOQUE 10.
-- ============================================================================


-- ────────────────────────────────────────────────────────────────────────────
-- BLOQUE 1 · MIGRACIONES APLICADAS
--
-- El repo tiene UN SOLO head: d2a4b6c8e0f1 (rbac_alerts_incidents_permissions).
-- Si produccion esta en esa revision, `alembic upgrade head` no hace nada.
-- Si esta en cualquiera de las dos anteriores, aplica exactamente UNA
-- migracion.
-- ────────────────────────────────────────────────────────────────────────────
SELECT
    version_num,
    CASE
        WHEN version_num = 'd2a4b6c8e0f1' THEN
            'AL DIA -> no hay nada que migrar (modulo 1 no aplica)'
        WHEN version_num IN ('b8d9e0f1a2b3', 'a7c8e9f0a1b2') THEN
            'FALTA LA MIGRACION d2a4b6c8e0f1 -> corra alembic upgrade head. Ojo: tambien revoca permisos (BLOQUE 8)'
        ELSE
            'REVISAR: revision inesperada. Corra `alembic current` y `alembic history` antes de migrar.'
    END AS accion
FROM alembic_version;


-- ────────────────────────────────────────────────────────────────────────────
-- BLOQUE 2 · CONFIG DEL MOTOR (lo que revienta /predictions con 500)
--
-- `KnowledgeModelSnapshotService.capture_current_snapshot()` corre en CADA
-- request a /predictions y levanta ValueError si alguna de estas dos esta
-- vacia. El error sube hasta el endpoint: 500 en toda la prediccion publica.
-- ────────────────────────────────────────────────────────────────────────────
SELECT
    t.tabla,
    CASE WHEN to_regclass('public.' || t.tabla) IS NULL
         THEN 'NO EXISTE -> corra alembic upgrade head'
         ELSE 'existe' END AS estado,
    CASE WHEN to_regclass('public.' || t.tabla) IS NULL
         THEN NULL
         ELSE (SELECT count(*) FROM public.recommendation_config) END AS filas,
    CASE
        WHEN to_regclass('public.' || t.tabla) IS NULL THEN 'FALTA LA TABLA'
        WHEN t.tabla = 'recommendation_config'
             AND (SELECT count(*) FROM public.recommendation_config) = 0
            THEN 'VACIA -> 500 en /predictions. Corra repair_motor_configs.sql'
        WHEN t.tabla = 'stage4_config'
             AND (SELECT count(*) FROM public.stage4_config) = 0
            THEN 'VACIA -> 500 en /predictions. Corra repair_motor_configs.sql'
        ELSE 'OK'
    END AS accion
FROM (VALUES ('recommendation_config'), ('stage4_config')) AS t(tabla);


-- ────────────────────────────────────────────────────────────────────────────
-- BLOQUE 3 · service_configs PARA BANOS
--
-- Sin esta fila, `BathroomV1Model` recibe `average_duration_min = None` y
-- degrada: la zona sale con `saturation_level = None` y el EventStatusBar
-- queda en 8/39. No hay error ni warning: es degradacion designed.
--
-- El `zone_type_id` correcto lo decide `_resolve_zone_type_id`
-- (prediction_module.py:121): primero el slug del `type` de la zona
-- ("servicios"), y solo si no existe ese, el slug mapeado desde el `subtipo`
-- ("bano"). Por eso el bloque de abajo resuelve con COALESCE en ese orden.
-- Si se inserta con el otro zone_type_id, el motor NO encuentra la fila y
-- los banos siguen degradando sin error visible.
-- ────────────────────────────────────────────────────────────────────────────
SELECT
    (to_regclass('public.service_configs') IS NOT NULL) AS existe_service_configs,
    (SELECT count(*) FROM public.zone_types WHERE slug = 'servicios') AS slug_servicios,
    (SELECT count(*) FROM public.zone_types WHERE slug = 'bano')       AS slug_bano,
    (SELECT count(*) FROM public.zones WHERE type = 'servicios' AND subtipo = 'banos')
        AS zonas_de_banos,
    COALESCE(
        (SELECT 'servicios' FROM public.zone_types WHERE slug = 'servicios' LIMIT 1),
        (SELECT 'bano'     FROM public.zone_types WHERE slug = 'bano'     LIMIT 1)
    ) AS slug_que_usaria_el_motor,
    CASE
        WHEN to_regclass('public.service_configs') IS NULL
            THEN 'FALTA LA TABLA -> corra alembic upgrade head (d4e5f6a7b8c9)'
        WHEN (SELECT count(*) FROM public.zone_types WHERE slug = 'servicios') = 0
         AND (SELECT count(*) FROM public.zone_types WHERE slug = 'bano') = 0
            THEN 'SIN CATALOGO -> repair_service_config_banos.sql NO va a insertar. Revisar zone_types primero'
        WHEN (SELECT count(*) FROM public.service_configs
              WHERE lower(coalesce(subtipo, '')) = 'banos'
                AND event_day_id IS NULL) > 0
            THEN 'OK -> el modelo de banos ya deberia calcular (indicador 17/39)'
        ELSE 'FALTA EL DEFAULT GLOBAL -> corra repair_service_config_banos.sql (indicador queda en 8/39 hasta entonces)'
    END AS accion;

-- Detalle de las filas de banos que ya existen (global + overrides por jornada).
SELECT
    sc.id,
    sc.zone_type_id,
    COALESCE(zt_serv.slug, zt_bano.slug) AS slug_del_zone_type,
    sc.subtipo,
    sc.event_day_id,
    CASE WHEN sc.event_day_id IS NULL
         THEN 'default global' ELSE 'override por jornada' END AS tipo,
    sc.average_duration_min
FROM public.service_configs sc
LEFT JOIN public.zone_types zt      ON zt.id = sc.zone_type_id
LEFT JOIN public.zone_types zt_serv ON zt_serv.slug = 'servicios'
LEFT JOIN public.zone_types zt_bano ON zt_bano.slug = 'bano'
WHERE lower(coalesce(sc.subtipo, '')) = 'banos'
ORDER BY sc.event_day_id NULLS FIRST;

-- Todas las service_configs, por si hay que configurar algo mas adelante
-- (hidratacion y descanso usan el mismo mecanismo).
SELECT
    COALESCE(zt.slug, '(zone_type_id huerfano: ' || sc.zone_type_id || ')') AS slug,
    sc.subtipo,
    sc.event_day_id,
    sc.average_duration_min
FROM public.service_configs sc
LEFT JOIN public.zone_types zt ON zt.id = sc.zone_type_id
ORDER BY slug, sc.subtipo NULLS FIRST, sc.event_day_id NULLS FIRST;


-- ────────────────────────────────────────────────────────────────────────────
-- BLOQUE 4 · CATALOGO zone_types
--
-- `zone_types` es la fuente de la resolucion slug-based. Si falta 'servicios'
-- o 'bano', `_load_zone_type_map` no puede resolver el zone_type_id de esas
-- zonas y `_load_zones` levanta ValueError -> 500 en /predictions.
-- ────────────────────────────────────────────────────────────────────────────
SELECT
    slug,
    name,
    CASE slug
        WHEN 'servicios' THEN 'LO USA el motor para zonas type=servicios (banos, hidratacion)'
        WHEN 'bano'      THEN 'FALLBACK del motor para subtipo=banos si no existe servicios'
        ELSE ''
    END AS rol
FROM public.zone_types
ORDER BY slug;


-- ────────────────────────────────────────────────────────────────────────────
-- BLOQUE 5 · ZONAS POR TIPO RESUELTO  (consulta CORREGIDA)
--
-- La version con `JOIN zone_types zt ON z.zone_type_id = zt.id` NO CORRE:
-- la tabla `zones` no tiene columna `zone_type_id` (ver app/models/zone.py).
-- Solo tiene `type` y `subtipo`.
--
-- Esta version replica `_resolve_zone_type_id` (prediction_module.py:121):
--   1) slug = z.type, si existe en zone_types
--   2) si no, slug = mapeo de z.subtipo  (banos->bano, hidratacion->hidratacion,
--      descanso->descanso)
--   3) si tampoco, slug = NULL = zona NO RESOLUBLE -> /predictions da 500
--
-- `slug_resuelto IS NULL` es la columna que hay que mirar: cualquier fila
-- ahi es un 500 waiting to happen.
--
-- IMPORTANTE sobre la columna `cobertura_del_indicador`: NO se deduce del
-- slug resuelto sino de (type, subtipo), porque eso es lo que miran los
-- modelos. `ParkingV1Model.supports` es `zone.type == 'estacionamiento'` y
-- `BathroomV1Model.supports` es `zone.type == 'servicios' and
-- zone.subtipo == 'banos'`: ninguno de los dos mira el zone_type_id. Un baño
-- puede resolver a slug 'servicios' y aun asi estar modelado.
-- ────────────────────────────────────────────────────────────────────────────
WITH resolucion AS (
    SELECT
        z.id,
        z.name,
        z.type,
        z.subtipo,
        z.capacity,
        z.status,
        e.name AS evento,
        COALESCE(zt_directo.slug, zt_subtipo.slug) AS slug_resuelto,
        CASE
            WHEN zt_directo.slug IS NOT NULL THEN '1) type como slug directo'
            WHEN zt_subtipo.slug IS NOT NULL THEN '2) slug mapeado desde subtipo'
            ELSE '3) SIN RESOLVER -> /predictions devuelve 500'
        END AS via_resolucion,
        CASE
            WHEN z.type = 'estacionamiento'
                THEN 'MODELO parking_v1 -> mide saturacion'
            WHEN z.type = 'servicios' AND z.subtipo = 'banos'
                THEN 'MODELO bathroom_v1 -> mide saturacion SI hay fila en service_configs'
            ELSE 'sin modelo -> NO aparece en el EventStatusBar'
        END AS cobertura_del_indicador
    FROM public.zones z
    LEFT JOIN public.events e          ON e.id = z.event_id
    LEFT JOIN public.zone_types zt_directo ON zt_directo.slug = z.type
    LEFT JOIN LATERAL (
        SELECT zt2.slug
        FROM public.zone_types zt2
        WHERE zt2.slug = CASE lower(coalesce(z.subtipo, ''))
            WHEN 'banos'       THEN 'bano'
            WHEN 'hidratacion' THEN 'hidratacion'
            WHEN 'descanso'    THEN 'descanso'
            ELSE NULL
        END
    ) zt_subtipo ON true
)
SELECT
    COALESCE(slug_resuelto, '(sin resolver)') AS slug_resuelto,
    type,
    subtipo,
    via_resolucion,
    cobertura_del_indicador,
    count(*)                                  AS total_zonas,
    count(*) FILTER (WHERE capacity > 0)      AS con_capacity,
    min(capacity)                             AS capacity_min,
    max(capacity)                             AS capacity_max
FROM resolucion
GROUP BY slug_resuelto, type, subtipo, via_resolucion, cobertura_del_indicador
ORDER BY total_zonas DESC;

-- Las zonas que el motor NO puede resolver. Deberia dar 0 filas: cualquiera
-- aca hace que `_load_zones` levante ValueError y /predictions devuelva 500.
SELECT z.id, z.name, z.type, z.subtipo, z.event_id
FROM public.zones z
LEFT JOIN public.zone_types zt_directo ON zt_directo.slug = z.type
LEFT JOIN LATERAL (
    SELECT zt2.slug FROM public.zone_types zt2
    WHERE zt2.slug = CASE lower(coalesce(z.subtipo, ''))
        WHEN 'banos' THEN 'bano'
        WHEN 'hidratacion' THEN 'hidratacion'
        WHEN 'descanso' THEN 'descanso'
        ELSE NULL END
) zt_subtipo ON true
WHERE zt_directo.slug IS NULL AND zt_subtipo.slug IS NULL
ORDER BY z.event_id, z.name;

-- El numero que decide el orden del deploy: cuantas zonas tiene el motor
-- especializado. Con 39 zonas y esta mezcla deberia dar 8 antes del script de
-- banos y 17 despues.
SELECT
    count(*) FILTER (WHERE type = 'estacionamiento')                       AS con_parking_v1,
    count(*) FILTER (WHERE type = 'servicios' AND subtipo = 'banos')        AS con_bathroom_v1,
    count(*) FILTER (
        WHERE type = 'estacionamiento'
           OR (type = 'servicios' AND subtipo = 'banos')
    )                                                                       AS zonas_modeladas,
    count(*)                                                               AS total_zonas,
    CASE
        WHEN count(*) FILTER (
            WHERE type = 'estacionamiento'
               OR (type = 'servicios' AND subtipo = 'banos')
        ) = count(*)
            THEN 'TODAS tienen modelo'
        ELSE 'indicador mostra ' || count(*) FILTER (
            WHERE type = 'estacionamiento'
               OR (type = 'servicios' AND subtipo = 'banos')
        ) || ' de ' || count(*) || ' zonas'
    END AS event_status_bar
FROM public.zones;


-- ────────────────────────────────────────────────────────────────────────────
-- BLOQUE 6 · INSUMOS DEL MOTOR QUE SI O SI TIENEN QUE ESTAR
--
-- ParkingV1 y BathroomV1 no calculan si falta esto, y degradan en silencio:
--   · event_days.estimated_vehicles  -> sin esto no hay parking
--   · event_days.average_parking_duration -> sin esto tampoco
--   · attendance_levels.max_people    -> sin esto no hay banos
--   · event_days.attendance_level_id  -> NULL = no hay nivel de asistencia
-- ────────────────────────────────────────────────────────────────────────────
SELECT
    ed.id                AS event_day_id,
    e.name               AS evento,
    ed.date,
    ed.attendance_level_id,
    al.max_people,
    ed.estimated_vehicles,
    ed.average_parking_duration,
    CASE
        WHEN ed.attendance_level_id IS NULL THEN 'FALTA asistencia -> bathrooms degrada'
        WHEN al.max_people IS NULL          THEN 'FALTA max_people -> bathrooms degrada'
        WHEN ed.estimated_vehicles IS NULL  THEN 'FALTA estimated_vehicles -> parking degrada'
        ELSE 'OK: ambos modelos pueden calcular'
    END AS estado
FROM public.event_days ed
LEFT JOIN public.events e             ON e.id = ed.event_id
LEFT JOIN public.attendance_levels al ON al.id = ed.attendance_level_id
ORDER BY ed.date DESC;


-- ────────────────────────────────────────────────────────────────────────────
-- BLOQUE 7 · PERMISOS (modulo 1)
--
-- `d2a4b6c8e0f1` hace TRES cosas, no una. Las dos agregaciones habilitan las
-- tarjetas "Alertas y Mensajes" y "Reportar Incidente" del Admin Municipal.
-- Las dos revocaciones son el riesgo real de correrla.
--
-- Que estos permisos no los exija ningun endpoint todavia es intentional: el
-- docstring de la migracion dice que `alert_admin.py` y `operational_events.py`
-- siguen con `verify_token`. O sea, la migracion no cambia la API, cambia que
-- ve la UI.
-- ────────────────────────────────────────────────────────────────────────────
SELECT
    r.code AS rol,
    p.code AS permiso,
    CASE
        WHEN p.code IN ('alerts:write', 'incidents:write')
            THEN 'lo AGREGA d2a4b6c8e0f1 -> habilita tarjetas del Admin'
        WHEN r.code = 'OPERADOR_CAMPO' AND p.code = 'events:read'
            THEN 'LO REVOCA d2a4b6c8e0f1 -> el operador pierde la pestana de predicciones'
        WHEN r.code = 'ANALISTA' AND p.code = 'counts:write'
            THEN 'LO REVOCA d2a4b6c8e0f1 -> ningun endpoint lo exige hoy'
        ELSE ''
    END AS efecto_de_la_migracion
FROM public.role_permissions rp
JOIN public.roles r       ON r.id = rp.role_id
JOIN public.permissions p ON p.id = rp.permission_id
WHERE p.code IN ('alerts:write', 'incidents:write', 'events:read', 'counts:write')
   OR r.code IN ('SUPER_ADMIN', 'MUNICIPAL_ADMIN', 'OPERADOR_CAMPO', 'ANALISTA')
ORDER BY r.code, p.code;

-- Los dos permisos nuevos, vista compacta. 2 filas = la migracion corrio.
SELECT
    p.code,
    p.module,
    p.action,
    (SELECT count(*) FROM public.role_permissions rp
      JOIN public.roles r ON r.id = rp.role_id
     WHERE rp.permission_id = p.id) AS roles_con_el_permiso
FROM public.permissions p
WHERE p.code IN ('alerts:write', 'incidents:write')
ORDER BY p.code;


-- ────────────────────────────────────────────────────────────────────────────
-- BLOQUE 8 · USUARIOS (para probar la demo con el rol correcto)
-- ────────────────────────────────────────────────────────────────────────────
SELECT
    u.username,
    u.email,
    u.is_active,
    u.is_superuser,
    string_agg(r.code, ', ' ORDER BY r.code) AS roles
FROM public.users u
LEFT JOIN public.user_roles ur ON ur.user_id = u.id
LEFT JOIN public.roles r       ON r.id = ur.role_id
GROUP BY u.id, u.username, u.email, u.is_active, u.is_superuser
ORDER BY u.username;


-- ────────────────────────────────────────────────────────────────────────────
-- BLOQUE 9 · OBSERVACIONES (modulo 2)
--
-- Si esto da 0, no hay nada que mostrar en los informes y hay que generar
-- datos. Ojo: `operational_observations.event_day_id` es NOT NULL y es FK a
-- event_days, asi que cualquier generador tiene que usar un event_day_id real
-- del BLOQUE 6.
--
-- Esta tabla la crea la migracion `f2a3b4c5d6e7` y NO esta en
-- `app.db.session.Base.metadata` (por eso `create_all` de los tests no la
-- hace). En produccion existe. Si este bloque da "relation does not exist",
-- no es un problema del script: los bloques 1 a 8 ya se ejecutaron y su
-- salida esta arriba.
-- ────────────────────────────────────────────────────────────────────────────
SELECT
    o.event_day_id,
    e.name AS evento,
    count(*)                     AS observaciones,
    count(DISTINCT o.zone_id)    AS zonas_observadas,
    count(DISTINCT o.observer_id) AS observadores,
    min(o.timestamp)             AS desde,
    max(o.timestamp)             AS hasta,
    min(o.observed_density)      AS densidad_min,
    max(o.observed_density)      AS densidad_max
FROM public.operational_observations o
LEFT JOIN public.event_days ed ON ed.id = o.event_day_id
LEFT JOIN public.events e      ON e.id = ed.event_id
GROUP BY o.event_day_id, e.name
ORDER BY observaciones DESC;


-- ────────────────────────────────────────────────────────────────────────────
-- BLOQUE 10 · QUE CONSULTAR EN EL ENDPOINT (no es SQL)
--
-- El numero de zonas con saturacion NO se puede leer de la base. Pegarle a:
--
--   GET /api/events/<event_id>/predictions
--
-- y contar. Este bloque no hace nada; es la nota de como verificar el
-- resultado despues de correr los scripts.
--
--   · 8 zonas con saturation_level no nula  -> falta service_configs de banos
--   · 17 zonas                              -> service_configs esta bien
--   · 500                                  -> recommendation_config o
--                                              stage4_config vacias (BLOQUE 2)
--
-- En logs, con el nivel INFO:
--
--   "Sin service_configs para (type='servicios', subtipo='banos')"
--       -> la fila no esta o el zone_type_id no es el que resuelve el motor
--   "El modelo especializado bathroom_v1 no calculo la zona ... por falta de datos"
--       -> llego al modelo pero sin average_duration_min
--
-- Ambas son degradation esperada, no errores. Un WARNING si seria un problema.
-- ────────────────────────────────────────────────────────────────────────────
SELECT 'endpoint' AS metodo, 'GET /api/events/<event_id>/predictions' AS que_correr
UNION ALL
SELECT 'contar', 'json -> zone_states[] -> saturation_level != null'
UNION ALL
SELECT 'esperado sin service_configs', '8'
UNION ALL
SELECT 'esperado con service_configs', '17';