"""Precedencia de `service_configs` cuando el endpoint recibe `event_day_id`.

Verifica que la jornada explicita manda sobre el default global, que es lo que
permite que el dashboard vea la configuracion de la jornada que esta mirando.
No depende de la hora del reloj: el `event_day_id` se pasa explicito.
"""
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from src.infrastructure.composition.prediction_module import (
    _resolve_bathroom_use_rate,
    _resolve_service_duration,
)

EVENT_ID = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
DAY_A = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
DAY_B = "11111111-1111-4111-8111-111111111111"
ZT_SERVICIOS = "0ae81004-90eb-4826-a6f4-0d616e628066"

GLOBAL_DUR, GLOBAL_RATE = 10, 0.02
DAY_A_DUR, DAY_A_RATE = 25, 0.5


def _async_url(url: str) -> str:
    import re

    return re.sub(r"^postgresql\+[a-z0-9_]+://", "postgresql+psycopg://", url)


@pytest.fixture(scope="module")
async def engine():
    url = settings.TEST_DATABASE_URL or settings.DATABASE_URL
    eng = create_async_engine(_async_url(url), poolclass=NullPool)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine, test_engine):
    """`test_engine` se pide solo para garantizar que el schema existe."""
    async with AsyncSession(engine) as s:
        yield s


@pytest.fixture
async def service_configs(engine, session):
    """Default global + override de DAY_A. Se limpia al final."""

    async def ensure_zone_type():
        """`test_engine` crea el schema con `create_all`, sin los sembrados de
        las migraciones. `service_configs` tiene FK a `zone_types` y a
        `event_days`, asi que hay que sembrar la cadena minima.
        """
        import datetime as _dt
        import uuid as _uuid

        await session.execute(
            text(
                "INSERT INTO zone_types (id, name, slug, icon, description, default_factors) "
                "VALUES (:z, 'Servicios', 'servicios', 'wc', 'Baños', '{}') "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"z": ZT_SERVICIOS},
        )
        await session.execute(
            text(
                "INSERT INTO events (id, name) VALUES (:e, 'Evento prueba') "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"e": EVENT_ID},
        )
        # Nombre unico por corrida: el perfil se crea una vez por test y el
        # schema no se limpia entre tests de este archivo.
        pid = str(_uuid.uuid4())
        await session.execute(
            text(
                "INSERT INTO operational_profiles (id, name) "
                "VALUES (:p, :n)"
            ),
            {"p": pid, "n": f"Perfil prueba {pid[:8]}"},
        )
        for day_id, offset in ((DAY_A, 0), (DAY_B, 1)):
            await session.execute(
                text(
                    "INSERT INTO event_days (id, event_id, date, day_of_week, is_active, "
                    " operational_profile_id, operational_start_min, operational_end_min) "
                    "VALUES (:i, :e, :d, 'LUNES', true, :p, 0, 1440) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {
                    "i": day_id,
                    "e": EVENT_ID,
                    "d": (_dt.date.today() + _dt.timedelta(days=offset)).isoformat(),
                    "p": pid,
                },
            )
        await session.commit()

    await ensure_zone_type()

    async def put(day_id, dur, rate):
        if day_id is None:
            await session.execute(
                text(
                    "DELETE FROM service_configs "
                    "WHERE zone_type_id=:z AND subtipo='banos' AND event_day_id IS NULL"
                ),
                {"z": ZT_SERVICIOS},
            )
            if dur is not None:
                await session.execute(
                    text(
                        "INSERT INTO service_configs "
                        "(id, zone_type_id, subtipo, event_day_id, average_duration_min, "
                        " bathroom_use_rate_per_person_hour) "
                        "VALUES (gen_random_uuid()::text, :z, 'banos', NULL, :d, :r)"
                    ),
                    {"z": ZT_SERVICIOS, "d": dur, "r": rate},
                )
        else:
            await session.execute(
                text("DELETE FROM service_configs WHERE event_day_id=:d"),
                {"d": day_id},
            )
            if dur is not None:
                await session.execute(
                    text(
                        "INSERT INTO service_configs "
                        "(id, zone_type_id, subtipo, event_day_id, average_duration_min, "
                        " bathroom_use_rate_per_person_hour) "
                        "VALUES (gen_random_uuid()::text, :z, 'banos', :d, :dur, :r)"
                    ),
                    {"z": ZT_SERVICIOS, "d": day_id, "dur": dur, "r": rate},
                )
        await session.commit()

    await put(None, GLOBAL_DUR, GLOBAL_RATE)
    await put(DAY_A, DAY_A_DUR, DAY_A_RATE)
    yield put
    await put(None, None, None)
    await put(DAY_A, None, None)


async def _resolve(session, event_day_id):
    dur = await _resolve_service_duration(
        session,
        zone_type_id=UUID(ZT_SERVICIOS),
        subtipo="banos",
        event_day_id=event_day_id,
    )
    rate = await _resolve_bathroom_use_rate(
        session,
        zone_type_id=UUID(ZT_SERVICIOS),
        event_day_id=event_day_id,
    )
    return dur, rate


class TestPrecedenciaDeEventDay:
    async def test_la_jornada_explicita_gana_al_default(self, session, service_configs):
        dur, rate = await _resolve(session, DAY_A)
        assert dur == DAY_A_DUR
        assert rate == pytest.approx(DAY_A_RATE)

    async def test_otra_jornada_sin_override_va_al_default(self, session, service_configs):
        dur, rate = await _resolve(session, DAY_B)
        assert dur == GLOBAL_DUR
        assert rate == pytest.approx(GLOBAL_RATE)

    async def test_sin_event_day_id_va_al_default(self, session, service_configs):
        dur, rate = await _resolve(session, None)
        assert dur == GLOBAL_DUR
        assert rate == pytest.approx(GLOBAL_RATE)

    async def test_el_override_mueve_el_modelo(self, session, service_configs):
        """Control de impacto: si el valor se ignorara, ambas jornadas darian
        el mismo resultado."""
        a = await _resolve(session, DAY_A)
        b = await _resolve(session, DAY_B)
        assert a[0] != b[0]
        assert a[1] != b[1]

    async def test_el_salto_de_override_usa_el_default(
        self, session, service_configs
    ):
        """Quitar el override devuelve la jornada al default global."""
        await service_configs(DAY_A, None, None)
        dur, rate = await _resolve(session, DAY_A)
        assert dur == GLOBAL_DUR
        assert rate == pytest.approx(GLOBAL_RATE)