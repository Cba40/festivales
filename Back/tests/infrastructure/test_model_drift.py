# backend/tests/infrastructure/test_model_drift.py
# Guard anti-drift entre las dos capas de modelos ORM.
#
# CONTEXTO
# Hay dos `Base` declarativos apuntando a la misma base:
#   - `app.db.session.Base` (26 tablas)          → la que materializa el árbol de migraciones
#   - `src.infrastructure.db.base.Base` (13)     → incluye 9 tablas fantasma + 4 reales
#
# Las 9 tablas fantasma son un diseño P3.0 abandonado que NUNCA se migró. No son
# "el mismo esquema con otro estilo": son otro esquema. Ejemplos, todos
# verificables contra `Back/alembic/versions/`:
#   - `zones` pasa de 30 columnas a 6: se pierde `event_id`, `type`, `saturation`,
#     `status`, `available_capacity` y la columna PostGIS `geometry`.
#   - `event_days.date` se renombra a `event_date`, y `event_date` no existe en la base.
#   - `operational_events.zone_id` → `target_zone_id` y `effect_value` → `impact_value`.
#   - `zone_behaviors` pierde los cuatro factores `Numeric(6,2)` que son el corazon
#     del modelo, y cambia `flow_restriction` de `String(20)` a un `SAEnum`.
# Es decir: estas clases no pueden ejecutar un solo SELECT contra la base real.
#
# POR QUE ESTE TEST EXISTE AUN ASI
# `alembic/env.py:69-74` ya resuelve el conflicto a favor de `app/` (copia AppBase
# primero y salta SrcBase en colision de nombre), asi que el riesgo de `drop_table`
# esta mitigado. Este test es el siguiente anillo: evita que la deuda vuelva a
# crecer, y sobre todo hace visible CUAL es la deuda, para que la Fase 2 (borrar
# los 9 fantasmas) sea una decision informada y no un acto de fe.
#
# QUE HACE Y QUE NO HACE
# - Congela la capa `src/`: cualquier columna que se agregue, quite o renombre en
#   un modelo fantasma rompe este test, que es exactamente el pedido.
# - Falla si aparece una tabla duplicada que no este registrada, sea en `src/` o en
#   `app/`: una tabla duplicada no registrada es una de las que rompe el merge de
#   `env.py` sin que nadie la mire.
# - Congela tambien la superficie legitima de `src/` (las 4 tablas que si existen
#   en la base), para que no crezca por descuido.
#
# NO congela la capa `app/`. A proposito: `app/` es la capa viva y tiene que poder
# crecer. Fijar sus columnas haria que cada migracion legitima (agregar una
# columna, por ejemplo) rompa un test que no esta probando nada. La proteccion
# relevante es que `src/` no se mueva, porque de ahi es de donde viene el riesgo.
#
# FASE 2
# Cuando se borren los 9 modelos fantasma hay que borrar `PHANTOM_TABLES` y
# `SRC_ONLY_TABLES` de este archivo. El test esta escrito para que ese borrado sea
# obligatorio: si se borra un modelo sin tocar el registro, `test_registro_refleja_la_realidad`
# falla diciendo exactamente cual. Ese es el mecanismo de transicion.

import pytest
from app.db.session import Base as AppBase
from src.infrastructure.db.base import Base as SrcBase

# Debe importarse el modulo por tabla: una clase solo se registra en su MetaData
# cuando su modulo se importa. Sin estos imports, `AppBase.metadata.tables` no
# tiene `zones` ni nada, y las comparaciones de abajo compararian vacios.
import app.models.attendance_level  # noqa: F401
import app.models.event_day  # noqa: F401
import app.models.event_day_phase  # noqa: F401
import app.models.operational_event  # noqa: F401
import app.models.operational_phase  # noqa: F401
import app.models.operational_profile  # noqa: F401
import app.models.zone  # noqa: F401
import app.models.zone_behavior  # noqa: F401
import app.models.zone_type  # noqa: F401
import src.infrastructure.persistence.models.attendance_level  # noqa: F401
import src.infrastructure.persistence.models.event_day  # noqa: F401
import src.infrastructure.persistence.models.event_day_phase  # noqa: F401
import src.infrastructure.persistence.models.operational_event  # noqa: F401
import src.infrastructure.persistence.models.operational_phase  # noqa: F401
import src.infrastructure.persistence.models.operational_profile  # noqa: F401
import src.infrastructure.persistence.models.zone  # noqa: F401
import src.infrastructure.persistence.models.zone_behavior  # noqa: F401
import src.infrastructure.persistence.models.zone_type  # noqa: F401

# Las 4 tablas que `src/` modela y que SI existen en la base. Esta es la
# superficie legitima de la capa: no debe crecer sin una migracion que la respalde.
SRC_ONLY_TABLES = frozenset(
    {
        "knowledge_model_versions",
        "operational_observations",
        "predictions",
        "zone_recommendations",
    }
)

# Deuda conocida: tabla -> (columnas del modelo fantasma, columnas que NO existen
# en `app/`). La segunda tupla es la que delata que no son un espejo: son columnas
# renombradas o inventadas, y por lo tanto consultas que romperían en la base.
PHANTOM_TABLES = {
    "zones": (
        ("capacity", "created_at", "id", "name", "updated_at", "zone_type_id"),
        ("zone_type_id",),
    ),
    "event_days": (
        (
            "attendance_level_id",
            "average_parking_duration",
            "created_at",
            "estimated_vehicles",
            "event_date",
            "id",
            "operational_end_min",
            "operational_profile_id",
            "operational_start_min",
            "updated_at",
        ),
        ("event_date",),
    ),
    "operational_events": (
        (
            "created_at",
            "end_timestamp",
            "id",
            "impact_value",
            "is_incident",
            "start_timestamp",
            "target_zone_id",
            "updated_at",
        ),
        ("impact_value", "target_zone_id"),
    ),
    "zone_types": (
        ("created_at", "id", "name", "updated_at"),
        ("updated_at",),
    ),
    "attendance_levels": (
        ("created_at", "id", "max_people", "min_people", "name", "updated_at"),
        ("created_at", "updated_at"),
    ),
    "operational_phases": (
        (
            "created_at",
            "id",
            "name",
            "operational_profile_id",
            "sequence_order",
            "updated_at",
        ),
        ("sequence_order",),
    ),
    "zone_behaviors": (
        (
            "created_at",
            "density_factor",
            "flow_restriction",
            "id",
            "operational_phase_id",
            "updated_at",
            "zone_type_id",
        ),
        (),
    ),
    "event_day_phases": (
        (
            "created_at",
            "end_min",
            "event_day_id",
            "id",
            "intensity",
            "operational_phase_id",
            "start_min",
            "updated_at",
        ),
        (),
    ),
    "operational_profiles": (
        ("created_at", "id", "name", "updated_at"),
        (),
    ),
}


def _columns(metadata, table: str) -> frozenset:
    return frozenset(metadata.tables[table].columns.keys())


def _shape(metadata, table: str) -> frozenset:
    """Nombre, tipo, nullability y pk de cada columna.

    El tipo va como string porque se compara el tipo que SQLAlchemy declaro, no el
    de Postgres: `UUID` se compila a `CHAR(32)`, que es como se distingue el
    modelo fantasma (UUID) del real (VARCHAR(36)) sin pegarle a la base.
    """
    return frozenset(
        (c.name, str(c.type), c.nullable, c.primary_key)
        for c in metadata.tables[table].columns
    )


def _duplicated() -> set:
    return set(AppBase.metadata.tables) & set(SrcBase.metadata.tables)


class TestNoNewDuplicates:
    """Lo mas importante: que la deuda de 9 tablas no crezca."""

    def test_no_hay_duplicadas_fuera_del_registro(self) -> None:
        """Ninguna tabla duplicada fuera de `PHANTOM_TABLES` puede aparecer.

        Este es el test que protege el merge de `alembic/env.py:69-74`. Ese merge
        resuelve colisiones por nombre y gana `app/`, asi que una tabla duplicada
        no registrada no rompe el autogenerate de hoy... pero queda arreglada de
        forma invisible, y el proximo que lea el codigo no tiene forma de saber
        que hay dos definiciones de la misma tabla.
        """
        registradas = set(PHANTOM_TABLES)
        no_registradas = _duplicated() - registradas
        assert not no_registradas, (
            "Tablas duplicadas entre app/ y src/ que no estan en PHANTOM_TABLES: "
            f"{sorted(no_registradas)}. Si es intencional, agregarlas al registro "
            "con su firma de columnas; si no, es una reintroduction de la deuda "
            "que este archivo existe para frenar."
        )

    def test_la_deuda_conocida_sigue_siendo_9(self) -> None:
        """Si este numero cambia, el resto de los tests hay que releerlo."""
        assert len(PHANTOM_TABLES) == 9


class TestPhantomModelsAreFrozen:
    """La capa `src/` no se toca. Agregar una columna a un fantasma rompe esto."""

    @pytest.mark.parametrize("tabla", sorted(PHANTOM_TABLES))
    def test_firma_de_columnas_no_cambio(self, tabla: str) -> None:
        esperadas, _ = PHANTOM_TABLES[tabla]
        actuales = tuple(sorted(_columns(SrcBase.metadata, tabla)))
        assert actuales == esperadas, (
            f"La firma de columnas de src/.../models para '{tabla}' cambio.\n"
            f"  antes: {esperadas}\n"
            f"  ahora: {actuales}\n"
            "Si el cambio es intencional, actualizar PHANTOM_TABLES en este mismo "
            "commit. Si no lo es, se acaba de Agriar la distancia entre el modelo "
            "fantasma y la tabla real."
        )

    @pytest.mark.parametrize("tabla", sorted(PHANTOM_TABLES))
    def test_columnas_fantasma_no_existen_en_app(self, tabla: str) -> None:
        """Las columnas que `src/` inventa no deben aparecer en `app/`.

        Es la verificacion de que estas dos capas siguen siendo esquemas
        distintos y no dos estilos del mismo. Si alguna apareciera en `app/`,
        alguien estariaguiando el modelo real hacia el diseño P3.0 abandonado, que
        es justo el resultado que hay que evitar.
        """
        _, fantasma = PHANTOM_TABLES[tabla]
        if not fantasma:
            pytest.skip(f"'{tabla}' no tiene columnas exclusivas de src/")
        en_app = _columns(AppBase.metadata, tabla)
        assert not (set(fantasma) & en_app), (
            f"'{tabla}': columnas del modelo fantasma que aparecieron en app/: "
            f"{sorted(set(fantasma) & en_app)}. La columna real en la base se llama "
            "distinto; revisar la migracion antes de tocar app/models/."
        )

    @pytest.mark.parametrize("tabla", sorted(PHANTOM_TABLES))
    def test_el_fantasma_no_es_un_espejo(self, tabla: str) -> None:
        """Un fantasma que se vuelve espejo sería indistinguible del bueno.

        Compara la FORMA completa de la tabla (nombre, tipo, nullability y pk de
        cada columna), no solo los nombres. Hace falta la forma porque hay
        tablas donde los nombres coinciden y lo que difiere es el tipo:
        `event_day_phases.event_day_id` es `VARCHAR(36)` en `app/` y `UUID` en
        `src/`, y un `db.get(EventDayPhaseModel, ...)` contra la base real falla
        justamente por ahi, no por una columna que falte.

        Si en algún momento `src/` llegara a ser identico a `app/`, la
        duplicacion ya no aporta nada y habria que eliminarla, no congelarla.
        Este test obliga a esa decision explicita en vez de dejarla pasar.
        """
        forma_src = _shape(SrcBase.metadata, tabla)
        forma_app = _shape(AppBase.metadata, tabla)
        assert forma_src != forma_app, (
            f"'{tabla}': el modelo de src/ quedo identico al de app/. La tabla ya no "
            "esta en PHANTOM_TABLES: sacala de ahi y tractala como unica."
        )


class TestRegistryMatchesReality:
    """El registro tiene que reflejar la realidad, en los dos sentidos.

    Asi la Fase 2 no puede quedar a medias: si borran un modelo sin tocar este
    archivo, falla acá diciendo cual. Y si agregan un duplicado, falla el otro
    test y no se registra en silencio.
    """

    def test_registro_refleja_la_realidad(self) -> None:
        registradas = set(PHANTOM_TABLES)
        reales = _duplicated()
        assert registradas == reales, (
            "PHANTOM_TABLES no coincide con las tablas realmente duplicadas.\n"
            f"  registradas y ausentes: {sorted(registradas - reales)}\n"
            f"  duplicadas y no registradas: {sorted(reales - registradas)}\n"
            "Si se borro un modelo fantasma (Fase 2), borrar tambien su entrada "
            "aca. Si se agrego uno, agregarlo con su firma de columnas."
        )

    def test_superficie_legitima_de_src_no_crecio(self) -> None:
        solo_src = set(SrcBase.metadata.tables) - set(AppBase.metadata.tables)
        assert solo_src == set(SRC_ONLY_TABLES), (
            "Las tablas que solo existen en src/ cambiaron.\n"
            f"  esperadas: {sorted(SRC_ONLY_TABLES)}\n"
            f"  actuales:  {sorted(solo_src)}\n"
            "Una tabla nueva en src/ necesita una migracion que la cree en el arbol "
            "activo; sin ella, el autogenerate la va a proponer como drop_table."
        )


class TestAppLayerIsTheRealOne:
    """Documenta cual de las dos capas manda, que es la pregunta del encargo.

    El caso mas caro de todos los dos: la primary key. Cuatro de estas tablas
    tienen `id VARCHAR(36)` en `app/` y `id UUID` en `src/`. No es un detalle
    cosmético: si alguien "moderniza" el modelo real a UUID para parecerse al
    fantasma, SQLAlchemy empieza a comparar contra un `uuid` de Postgres donde
    la columna es `varchar(36)`, y el fallo aparece en runtime, en produccion,
    como "invalid input syntax for type uuid" en vez de como un error de modelo.
    """

    # Tipo de la PK segun lo que declara el arbol de migraciones activo, en la
    # forma en que SQLAlchemy lo compila para postgres (por eso `UUID` aparece
    # como `CHAR(32)` y no como `UUID`).
    # VARCHAR(36) viene de `1e040f8557ec` (zones) y `0f9f11bbb377` (event_days);
    # UUID viene de `d0e1f2a3b4c5` y `e5f6a7b8c9d0`.
    APP_PK_TYPES = {
        "zones": "VARCHAR(36)",
        "event_days": "VARCHAR(36)",
        "zone_types": "VARCHAR(36)",
        "attendance_levels": "VARCHAR(36)",
        "operational_events": "CHAR(32)",  # uuid
        "operational_phases": "CHAR(32)",  # uuid
        "zone_behaviors": "CHAR(32)",  # uuid
        "event_day_phases": "CHAR(32)",  # uuid
        "operational_profiles": "CHAR(32)",  # uuid
    }

    @pytest.mark.parametrize("tabla", sorted(PHANTOM_TABLES))
    def test_pk_de_app_es_la_de_la_migracion(self, tabla: str) -> None:
        pk = list(AppBase.metadata.tables[tabla].primary_key.columns)
        assert len(pk) == 1, f"'{tabla}' deberia tener una sola columna pk, tiene {len(pk)}"
        assert str(pk[0].type) == self.APP_PK_TYPES[tabla], (
            f"'{tabla}': el tipo de la pk en app/models/ cambio a {pk[0].type}. "
            "Las migraciones declaran "
            f"{self.APP_PK_TYPES[tabla]}. Si el cambio es correcto, es porque una "
            "migracion lo materializo y hay que actualizar esta tabla; si no, lo mas "
            "probable es que se haya copiado el modelo fantasma de src/."
        )
