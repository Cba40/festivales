-- ============================================================================
--  Verificacion e insercion de la permanencia de BANOS en service_configs
--
--  PARA: Neon -> SQL Editor. Pegar y ejecutar el bloque COMPLETO.
--
--  POR QUE
--  -------
--  `BathroomV1Model` calcula la ocupacion concurrente con Little's law:
--
--      concurrent_occupancy = v_expected x (average_duration_min / 60) / delta_hours
--
--  y `average_duration_min` viene de `service_configs`. Sin fila, el valor llega
--  en NULL al contexto, el modelo degrada y la zona de banos sale del
--  `EventStatusBar` (sin `saturation_level`). Con la fila, entra:
--
--      antes:  8/39 zonas  (solo estacionamientos)   = 21% del territorio
--      ahora: 17/39 zonas  (8 estacionamientos + 9 banos) = 44% del territorio
--
--  Que el modelo no se caiga si falta la fila es garantizado por el aislamiento
--  por zona de `execute_specialized_models`. Esta fila es lo que hace que los
--  banos MIDAN, no lo que evita que rompan.
--
--  CUAL ES EL VALOR DE 5
--  ---------------------
--  Es una visita tipica a un bano publico de festival (5 minutos), y es el valor
--  con el que se calibro el escenario sintetico de 39 zonas
--  (`tests/infrastructure/composition/test_territorial_intensity_by_phase.py`).
--  Es un default operativo, no una medicion: se cambia desde el dashboard en
--  "Configuracion de servicios" o con un UPDATE puntual. En un evento con
--  escuchando de 15 minutos se sube; con 2 minutos, se baja.
--
--  GARANTIAS DE SEGURIDAD
--    * No borra nada.
--    * No hace UPDATE ni ALTER: si la fila ya existe, no la toca (ni su valor).
--    * Es idempotente: correrlo N veces deja el mismo estado.
--    * No adivina el `zone_type_id`: lo resuelve con la MISMA precedencia que
--      `_resolve_zone_type_id` (prediction_module.py:121), o sea slug `servicios`
--      primero y slug `bano` de fallback. Si no encuentra ninguno de los dos,
--      NO inserta y avisa.
--    * Si la tabla no existe NO falla ni crea nada: avisa por NOTICE y hay que
--      correr la migracion `d4e5f6a7b8c9`.
--    * `event_day_id = NULL`: es el default GLOBAL. Las jornadas concretas se
--      configuran por override despues y no se tocan.
-- ============================================================================


-- ────────────────────────────────────────────────────────────────────────────
-- PASO 1 · DIAGNOSTICO (solo lectura). Ideal para correrlo primero solo.
-- ────────────────────────────────────────────────────────────────────────────
SELECT
    sc.zone_type_id,
    coalesce(zt_serv.slug, zt_bano.slug)                AS slug_resuelto,
    sc.subtipo,
    sc.event_day_id,
    sc.average_duration_min,
    CASE WHEN sc.event_day_id IS NULL
         THEN 'default global'
         ELSE 'override por jornada'
    END AS tipo,
    CASE WHEN sc.event_day_id IS NULL
              AND zt.id IS NOT NULL
         THEN 'OK'
         WHEN sc.event_day_id IS NULL
         THEN 'FALTA EL DEFAULT GLOBAL -> corra el Paso 2'
         ELSE 'OK (override; el modelo prioriza este sobre el default)'
    END AS accion
FROM public.service_configs sc
LEFT JOIN public.zone_types zt      ON zt.id = sc.zone_type_id
LEFT JOIN public.zone_types zt_serv ON zt_serv.slug = 'servicios'
LEFT JOIN public.zone_types zt_bano ON zt_bano.slug = 'bano'
WHERE lower(coalesce(sc.subtipo, '')) = 'banos';

-- Las tres cosas que tienen que estar bien para que esto funcione.
SELECT
    (to_regclass('public.service_configs') IS NOT NULL) AS existe_service_configs,
    (SELECT count(*) FROM public.zone_types WHERE slug = 'servicios') AS slug_servicios,
    (SELECT count(*) FROM public.zone_types WHERE slug = 'bano')       AS slug_bano,
    (SELECT count(*) FROM public.zones WHERE type = 'servicios' AND subtipo = 'banos')
        AS zonas_banos;


-- ────────────────────────────────────────────────────────────────────────────
-- PASO 2 · INSERCION. Inserta SOLO el default global que falte.
--
-- Nota de por que va en un bloque DO y no en un INSERT pelado: plpgsql parsea
-- cada sentencia justo antes de ejecutarla. Si la tabla no existe, la rama del
-- INSERT nunca se alcanza, nunca se parsea, y por lo tanto no da error.
--
-- `ON CONFLICT DO NOTHING` cubre los dos indices parciales
-- (`uq_service_config_default` y `uq_service_config_override`) sin tener que
-- nombrarlos: si ya hay fila, no inserta y no modifica la existente.
-- ────────────────────────────────────────────────────────────────────────────
DO $repair$
DECLARE
    v_zone_type_id text;
    v_insertados    integer;
BEGIN
    IF to_regclass('public.service_configs') IS NULL THEN
        RAISE NOTICE 'service_configs: la tabla NO EXISTE. Sin cambios. Corra alembic upgrade head.';
        RETURN;
    END IF;

    -- Misma precedencia que `_resolve_zone_type_id` (prediction_module.py:121):
    -- 1) el slug del `type` de la zona ("servicios"); 2) el slug mapeado desde
    -- el `subtipo` ("bano"). Sin esta precedencia el INSERT apuntaria a un
    -- zone_type_id distinto del que el motor resuelve y el modelo seguiría
    -- degradando sin dar error.
    SELECT id INTO v_zone_type_id
    FROM public.zone_types
    WHERE slug = 'servicios'
    LIMIT 1;

    IF v_zone_type_id IS NULL THEN
        SELECT id INTO v_zone_type_id
        FROM public.zone_types
        WHERE slug = 'bano'
        LIMIT 1;
    END IF;

    IF v_zone_type_id IS NULL THEN
        RAISE NOTICE
            'ATENCION: no hay zone_types con slug ''servicios'' ni ''bano''. '
            'Sin cambios. Sin esa fila el modelo de banos va a seguir degradando.';
        RETURN;
    END IF;

    INSERT INTO public.service_configs (
        id,
        zone_type_id,
        subtipo,
        event_day_id,
        average_duration_min
    ) VALUES (
        gen_random_uuid()::text,
        v_zone_type_id,
        'banos',
        NULL,
        5                    -- minutos de visita a un bano publico
    )
    ON CONFLICT DO NOTHING;

    GET DIAGNOSTICS v_insertados = ROW_COUNT;

    IF v_insertados = 0 THEN
        RAISE NOTICE
            'service_configs banos: ya existia una fila. Sin cambios (no se pisa su valor).';
    ELSE
        RAISE NOTICE
            'service_configs banos: default global insertado (zone_type_id=%, average_duration_min=5).',
            v_zone_type_id;
    END IF;
END
$repair$;


-- ────────────────────────────────────────────────────────────────────────────
-- PASO 3 · VERIFICACION FINAL. Debe devolver 1 fila con average_duration_min=5.
-- Con eso el EventStatusBar deberia mostrar 17/39 zonas y no 8/39.
-- ────────────────────────────────────────────────────────────────────────────
SELECT
    sc.id,
    sc.zone_type_id,
    coalesce(zt_serv.slug, zt_bano.slug) AS slug,
    sc.subtipo,
    sc.average_duration_min,
    sc.created_at
FROM public.service_configs sc
LEFT JOIN public.zone_types zt      ON zt.id = sc.zone_type_id
LEFT JOIN public.zone_types zt_serv ON zt_serv.slug = 'servicios'
LEFT JOIN public.zone_types zt_bano ON zt_bano.slug = 'bano'
WHERE lower(coalesce(sc.subtipo, '')) = 'banos'
  AND sc.event_day_id IS NULL;