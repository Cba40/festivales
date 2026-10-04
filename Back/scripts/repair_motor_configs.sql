-- ============================================================================
--  Verificacion y reparacion de recommendation_config / stage4_config
--
--  PARA: Neon -> SQL Editor. Pegar y ejecutar el bloque COMPLETO.
--
--  POR QUE: GET /api/events/{event_id}/predictions llama a
--  KnowledgeModelSnapshotService.capture_current_snapshot() en CADA request,
--  y ese metodo hace:
--      select ... from recommendation_config  -> si no hay fila: ValueError
--      select ... from stage4_config          -> si no hay fila: ValueError
--  El ValueError sube hasta el endpoint y TODA la prediccion publica responde
--  500, no solo un informe.
--
--  GARANTIAS DE SEGURIDAD
--    * No borra nada.
--    * No hace UPDATE ni ALTER: no toca filas que ya existan.
--    * Es idempotente: correrlo N veces deja el mismo estado.
--    * Si la tabla no existe NO falla ni crea nada: avisa por NOTICE y hay que
--      correr la migracion.
-- ============================================================================


-- ────────────────────────────────────────────────────────────────────────────
-- PASO 1 · DIAGNOSTICO (solo lectura). Ideal para correrlo primero solo.
-- ────────────────────────────────────────────────────────────────────────────
SELECT
    t.tabla,
    (to_regclass('public.' || t.tabla) IS NOT NULL) AS existe_la_tabla,
    CASE
        WHEN to_regclass('public.' || t.tabla) IS NULL THEN NULL
        WHEN t.tabla = 'recommendation_config' THEN
            (SELECT count(*) FROM public.recommendation_config)
        ELSE
            (SELECT count(*) FROM public.stage4_config)
    END AS filas,
    CASE
        WHEN to_regclass('public.' || t.tabla) IS NULL
            THEN 'FALTA LA TABLA -> corra alembic upgrade head'
        WHEN t.tabla = 'recommendation_config' AND
             (SELECT count(*) FROM public.recommendation_config) = 0
            THEN 'VACIA -> hay que insertar (Paso 2)'
        WHEN t.tabla = 'stage4_config' AND
             (SELECT count(*) FROM public.stage4_config) = 0
            THEN 'VACIA -> hay que insertar (Paso 2)'
        ELSE 'OK'
    END AS accion
FROM (VALUES ('recommendation_config'), ('stage4_config')) AS t(tabla);


-- ────────────────────────────────────────────────────────────────────────────
-- PASO 2 · REPARACION. Inserta SOLO si la tabla existe y esta vacia.
--
-- Nota de por que va en un bloque DO y no en un INSERT pelado: plpgsql parsea
-- cada sentencia justo antes de ejecutarla. Si la tabla no existe, la rama del
-- INSERT nunca se alcanza, nunca se parsea, y por lo tanto no da error. Un
-- `INSERT INTO ... SELECT ... WHERE to_regclass(...) IS NOT NULL` pelado SI
-- fallaria, porque el parser resuelve el nombre de tabla antes de mirar el
-- WHERE.
-- ────────────────────────────────────────────────────────────────────────────
DO $repair$
BEGIN
    -- recommendation_config
    IF to_regclass('public.recommendation_config') IS NULL THEN
        RAISE NOTICE 'recommendation_config: la tabla NO EXISTE. Sin cambios. Corra alembic upgrade head.';
    ELSIF NOT EXISTS (SELECT 1 FROM public.recommendation_config) THEN
        INSERT INTO public.recommendation_config (
            id,
            low_density_saturation_threshold,
            low_density_reasoning_threshold,
            regulated_penalty,
            vip_bonus,
            staff_bonus,
            mobility_penalty
        ) VALUES (
            1,
            0.5,   -- default de app/models/motor_config.py
            0.3,
            0.3,
            0.1,
            0.2,
            0.15
        );
        RAISE NOTICE 'recommendation_config: fila por defecto insertada (id=1).';
    ELSE
        RAISE NOTICE 'recommendation_config: ya tiene filas. Sin cambios.';
    END IF;

    -- stage4_config
    IF to_regclass('public.stage4_config') IS NULL THEN
        RAISE NOTICE 'stage4_config: la tabla NO EXISTE. Sin cambios. Corra alembic upgrade head.';
    ELSIF NOT EXISTS (SELECT 1 FROM public.stage4_config) THEN
        INSERT INTO public.stage4_config (
            id,
            saturation_high_threshold,
            saturation_moderate_threshold
        ) VALUES (
            1,
            0.9,   -- default de app/models/motor_config.py
            0.5
        );
        RAISE NOTICE 'stage4_config: fila por defecto insertada (id=1).';
    ELSE
        RAISE NOTICE 'stage4_config: ya tiene filas. Sin cambios.';
    END IF;
END
$repair$;


-- ────────────────────────────────────────────────────────────────────────────
-- PASO 3 · VERIFICACION FINAL. Debe devolver 1 fila por tabla, filas >= 1.
-- ────────────────────────────────────────────────────────────────────────────
SELECT 'recommendation_config' AS tabla, count(*) AS filas,
       (SELECT saturation_moderate_threshold FROM public.stage4_config LIMIT 1)
           AS stage4_moderate
FROM public.recommendation_config
UNION ALL
SELECT 'stage4_config', count(*), NULL FROM public.stage4_config;
