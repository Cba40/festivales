from __future__ import annotations

import inspect

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from src.infrastructure.db.config import (
    async_session_factory,
    engine,
    get_session,
)


class TestEngine:
    def test_engine_is_async_engine(self) -> None:
        assert isinstance(engine, AsyncEngine)

    def test_engine_url_uses_postgresql(self) -> None:
        url = str(engine.url)
        assert url.startswith("postgresql")


class TestSessionFactory:
    def test_session_factory_is_async_sessionmaker(self) -> None:
        assert isinstance(async_session_factory, async_sessionmaker)

    def test_session_factory_binds_async_session(self) -> None:
        assert async_session_factory.class_ is AsyncSession

    def test_session_factory_is_callable(self) -> None:
        assert callable(async_session_factory)


class TestGetSession:
    def test_get_session_is_async_generator_function(self) -> None:
        assert inspect.isasyncgenfunction(get_session)
