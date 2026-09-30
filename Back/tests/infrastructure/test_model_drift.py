# backend/tests/infrastructure/test_model_drift.py
# Guard anti-drift entre las dos capas de modelos ORM.
#
# CONTEXTO
# Hay dos `Base` declarativos apuntando a la misma base:
#   - `app.db.session.Base` (26 tablas)  → la que materializa el árbol de migraciones
#   - `src.infrastructure.db.base.Base` (4) → operational_observations, predictions,
#     zone_recommendations y knowledge_model_versions
#
# Los dos conjuntos son disjuntos, y ese es el invariante que este archivo vigila.
#
# HISTORIA (por qué este archivo existe)
# Hubo 9 tablas presentes en AMBAS capas: zones, event_days, operational_events,
# zone_types, attendance_levels, operational_phases, zone_behaviors, event_day_phases
# y operational_profiles. Las de `src/` eran un diseño P3.0 abandonado que NUNCA se
# migró, y no eran "el mismo esquema con otro estilo": eran otro esquema. Ejemplos,
# todos verificables contra `Back/alembic/versions/`:
#   - `zones` pasaba de 30 columnas a 6: se perdían `event_id`, `type`, `saturation`,
#     `status`, `available_capacity` y la columna PostGIS `geometry`.
#   - `event_days.date` se renombraba a `event_date`, y `event_date` no existe.
#   - `operational_events.zone_id` → `target_zone_id`, `effect_value` → `impact_value`.
#   - `zone_behaviors` perdía los cuatro factores `Numeric(6,2)` que son el corazón
#     del modelo, y `flow_restriction` pasaba de `String(20)` a un `SAEnum`.
# Es decir: esas clases no podían ejecutar un solo SELECT contra la base real.
#
# La deuda se saldó en tres fases: 1) el único uso en producción
# (`metric_service.py`) pasó al modelo de `app/`; 2) se borraron seeds,
# implementaciones SQL de repositorios y sus tests; 3) se borraron los 9 modelos
# y los 9 mappers, y `alembic/env.py` dejo de necesitar la regla de desempate por
# nombre de tabla. Este archivo quedo como el anillo que impide que vuelva.
#
# QUE HACE ESTE TEST
# Las dos capas no deben compartir ninguna tabla. Hoy el conjunto es disjunto y eso
# es lo unico que hace falta vigilar. Si alguien reintroduce un modelo duplicado
# en cualquiera de las dos capas, estos tests lo dicen con el nombre de la tabla.
# Eso importa porque el merge de `alembic/env.py:67-78` resuelve colisiones por
# nombre quedandose con la de `app/`: una duplicada no registrada no rompe nada
# hoy, pero queda resuelta de forma invisible, y el proximo que lea el codigo no
# tiene forma de saber que hay dos definiciones de la misma tabla.

from src.infrastructure.db.base import Base as SrcBase
from app.db.session import Base as AppBase

# Deben importarse los modulos para que las clases se registren en su MetaData: una
# clase solo aparece en `metadata.tables` cuando su modulo se importa. Sin esto las
# comparaciones de abajo compararian conjuntos vacios y pasarian siempre.
#
# No alcanza con importar el barrel de `src/.../models/`: ese `__init__` lista las
# 4 clases legitimas, asi que un archivo NUEVO agregado a ese directorio (un
# `zone.py` reintroducido, por ejemplo) no se registraria y el guard no lo veria.
# Se veria como si la capa estuviera limpia, que es exactamente el falso negativo
# que este archivo existe para evitar. Por eso se recorren e importan todos los
# modulos del paquete, no solo los conocidos.
import importlib
import pkgutil

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

import src.infrastructure.persistence.models as _src_models_pkg

for _module_info in pkgutil.iter_modules(_src_models_pkg.__path__):
    importlib.import_module(f"{_src_models_pkg.__name__}.{_module_info.name}")

# En `app/` alcanza con el barrel: `app/models/__init__.py` existe, pero se importa
# cada modulo modesto para no depender de que ese barrel este completo.
import importlib as _importlib
import pkgutil as _pkgutil

import app.models as _app_models_pkg

for _module_info in _pkgutil.iter_modules(_app_models_pkg.__path__):
    _importlib.import_module(f"{_app_models_pkg.__name__}.{_module_info.name}")

# Tablas que solo existen en `src/`. Esta es su superficie legitima: 4 modelos que
# el árbol de migraciones activo sí materializa. No debe crecer sin una migración
# que respalde la tabla nueva.
#
# Ojo con el nombre del directorio: `src/infrastructure/persistence/models/` tambien
# aloja `configuration_recommendation.py` y `recommendation_audit_entry.py`, pero
# esas dos clases registran sobre `app.db.session.Base`, NO sobre `SrcBase`. Son de
# la capa `app/` a pesar de la ruta. Por eso no aparecen acá, y por eso el conteo de
# `src/` es 4 y no 6.
SRC_ONLY_TABLES = frozenset(
    {
        "knowledge_model_versions",
        "operational_observations",
        "predictions",
        "zone_recommendations",
    }
)

# Deuda conocida: tabla -> (columnas del modelo fantasma, columnas que NO existen
# en `app/`). Vacio: la deuda se saldo en la Fase 2.3.
#
# Este diccionario no se borro, se dejo vacio a proposito. Cumple dos funciones:
#
# 1. Es el registro de "tablas duplicadas conocidas". Si alguien reintroduce una
#    duplicada que no este aca, `test_no_hay_duplicadas_fuera_del_registro` falla
#    nombrandola. Si la duplica a proposito y quiere que el test lo tolere, la
#    agrega aca con su firma de columnas, y queda documentada en vez de oculta.
# 2. Es la lista de lo que hay que auditar si vuelve a aparecer una duplicada.
#    While 9 registros con esto, cada uno era una tabla distinta con una
#    discrepancia distinta, y "arreglar la deuda" no era una accion mecanica.
#
# Antes tenia 9 entradas y un test que congelaba la capa `src/`. Esa parte se
# elimino junto con los modelos: sin duplicadas no hay nada que congelar, y
# mantenerla era un test que comparaba contra un registro permanentemente vacio.
PHANTOM_TABLES: dict = {}


def _duplicated() -> set:
    return set(AppBase.metadata.tables) & set(SrcBase.metadata.tables)


class TestNoNewDuplicates:
    """Lo unico que hace falta vigilar: las capas no se solapan."""

    def test_no_hay_duplicadas_fuera_del_registro(self) -> None:
        """Ninguna tabla duplicada fuera de `PHANTOM_TABLES` puede aparecer.

        Este es el test que protege el merge de `alembic/env.py:67-78`. Ese merge
        resuelve colisiones por nombre y se queda con la de `app/`, asi que una
        tabla duplicada no registrada no rompe el autogenerate de hoy... pero
        queda arreglada de forma invisible.
        """
        registradas = set(PHANTOM_TABLES)
        no_registradas = _duplicated() - registradas
        assert not no_registradas, (
            "Tablas duplicadas entre app/ y src/ que no estan en PHANTOM_TABLES: "
            f"{sorted(no_registradas)}. Si es intencional, agregarlas al registro "
            "con su firma de columnas; si no, se esta reintroduciendo la deuda que "
            "las Fases 1 a 2.3 cerraron."
        )

    def test_la_deuda_conocida_sigue_siendo_cero(self) -> None:
        """Si este numero deja de ser 0, hay que auditar antes de continuar."""
        assert len(PHANTOM_TABLES) == 0, (
            "PHANTOM_TABLES no esta vacio. Agregar una entrada es una decision "
            "consciente, no un efecto secundario: significa que una tabla volvió a "
            "estar duplicada y hay que decidir quien se queda con ella."
        )

    def test_las_capas_no_se_solapan(self) -> None:
        """Version sin registro: el conjunto compartido tiene que estar vacio."""
        assert not _duplicated(), (
            f"Las dos capas comparten tablas: {sorted(_duplicated())}."
        )


class TestRegistryMatchesReality:
    """El registro tiene que reflejar la realidad, en los dos sentidos."""

    def test_registro_refleja_la_realidad(self) -> None:
        registradas = set(PHANTOM_TABLES)
        reales = _duplicated()
        assert registradas == reales, (
            "PHANTOM_TABLES no coincide con las tablas realmente duplicadas.\n"
            f"  registradas y ausentes: {sorted(registradas - reales)}\n"
            f"  duplicadas y no registradas: {sorted(reales - registradas)}\n"
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


class TestSrcLayerCanEmitDdl:
    """Guard de la regresión que perdió una FK cross-registry.

    `ZoneRecommendationModel` declaraba `ForeignKey("zones.id")` y
    `PredictionModel` declaraba `ForeignKey("event_days.id")`, con las dos tablas
    referenciadas en `AppBase` y los dos modelos en `SrcBase`. SQLAlchemy resuelve
    el string de una FK dentro del MetaData donde se define la tabla, así que en
    cuanto alguien compila el DDL de esas tablas (un `alembic autogenerate`, un
    test que arme el schema, cualquier cosa que llame a `create_all`) revienta con
    NoReferencedTableError.

    No se rompía al escribir filas ni al leer: por eso pasó inadvertido y solo
    exploto en los endpoints de recomendacion, que son los que llegan a
    reconstruir el schema. Y no lo detectaba ningun test de la suite.

    Compilar el DDL de las 4 tablas de `src/` es la forma barata de cerrar eso.
    """

    def test_las_tablas_de_src_emiten_ddl(self) -> None:
        dialect = postgresql.dialect()
        for name, table in sorted(SrcBase.metadata.tables.items()):
            try:
                str(CreateTable(table).compile(dialect=dialect))
            except Exception as exc:  # pragma: no cover - solo se ejecuta al fallar
                pytest.fail(
                    f"La tabla src/ '{name}' no compila su DDL: "
                    f"{type(exc).__name__}: {exc}\n"
                    "Casi siempre es una ForeignKey que apunta a una tabla de la "
                    "capa app/, que no esta en SrcBase.metadata. La columna se "
                    "declara sin ForeignKey y la integridad la siguen aplicando "
                    "las ForeignKeyConstraint de las migraciones, en Postgres. "
                    "Ver comment en el modelo."
                )

    def test_src_no_declara_fks_hacia_app(self) -> None:
        """Las FK de `src/` no pueden apuntar a tablas de `app/`. Nunca.

        Es la misma comprobacion que el test de arriba, pero sobre la causa y no
        sobre el síntoma: si algún día se autoriza una FK cross-registry, este
        test dice por qué no, en el punto donde se escribe, en vez de dejar que se
        descubra en runtime.
        """
        tablas_app = set(AppBase.metadata.tables)
        for name, table in sorted(SrcBase.metadata.tables.items()):
            for fk in table.foreign_keys:
                tabla_destino = fk.column.table.name
                if tabla_destino in tablas_app and tabla_destino not in SrcBase.metadata.tables:
                    pytest.fail(
                        f"La columna '{name}.{fk.parent.name}' declara FK a "
                        f"'{tabla_destino}', que es una tabla de la capa app/ y no "
                        "esta en SrcBase.metadata. Compilar el DDL de esa tabla "
                        "falla con NoReferencedTableError. Dejalo como columna "
                        "simple: la integridad la aplica la constraint de la "
                        "migracion, en la base."
                    )


class TestAppPrimaryKeys:
    """Fijado contra las migraciones activas, porque es la trampa mas cara.

    Cuatro tablas tienen `id VARCHAR(36)` en `app/`: zones, event_days, zone_types y
    attendance_levels. El resto de la base usa `uuid`. No es cosmético: si alguien
    "moderniza" una PK varchar a UUID para parecerse al modelo, SQLAlchemy pasa a
    comparar contra un `uuid` de Postgres donde la columna es `varchar(36)`, y el
    fallo aparece en runtime, en produccion, como "invalid input syntax for type
    uuid" en vez de como un error de modelo.

    Este test se conserva desde la Fase 0, cuando la amenaza era "copiar el diseño
    UUID del modelo fantasma". Ese modelo ya no existe, pero el riesgo no: las
    migraciones son la fuente de verdad y no cambian solas.
    """

    # Tipo de la PK segun lo que declara el arbol de migraciones activo, en la
    # forma en que SQLAlchemy lo compila para postgres (por eso `UUID` aparece
    # como `CHAR(32)` y no como `UUID`).
    # VARCHAR(36) viene de `1e040f8557ec` (zones) y `0f9f11bbb377` (event_days);
    # UUID viene de `d0e1f2a3b4c5` y `e5f6a7b8c9d0`.
    APP_PK_TYPES = {
        "attendance_levels": "VARCHAR(36)",
        "event_days": "VARCHAR(36)",
        "event_day_phases": "CHAR(32)",  # uuid
        "operational_events": "CHAR(32)",  # uuid
        "operational_phases": "CHAR(32)",  # uuid
        "operational_profiles": "CHAR(32)",  # uuid
        "zone_behaviors": "CHAR(32)",  # uuid
        "zone_types": "VARCHAR(36)",
        "zones": "VARCHAR(36)",
    }

    def test_tipos_de_pk_siguen_las_migraciones(self) -> None:
        for tabla, esperado in self.APP_PK_TYPES.items():
            pk = list(AppBase.metadata.tables[tabla].primary_key.columns)
            assert len(pk) == 1, (
                f"'{tabla}' deberia tener una sola columna pk, tiene {len(pk)}"
            )
            assert str(pk[0].type) == esperado, (
                f"'{tabla}': el tipo de la pk en app/models/ cambio a {pk[0].type}. "
                f"Las migraciones declaran {esperado}. Si el cambio es correcto, es "
                "porque una migracion lo materializo y hay que actualizar esta "
                "tabla; si no, casi seguro se toco el modelo sin migracion."
            )
