"""Database session and engine configuration."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from .config import get_settings
from .models import Base

_settings = get_settings()
_engine = create_async_engine(_settings.database_url, echo=_settings.debug, future=True)
_SessionFactory = async_sessionmaker(
    bind=_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency providing an `AsyncSession`."""

    async with _SessionFactory() as session:
        yield session


async def init_db() -> None:
    """Create tables in development/test environments if not present."""

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_sync_session() -> Session:
    """Helper for CLI or scripts requiring synchronous session access."""

    raise NotImplementedError("Use async sessions; sync access will be added if needed.")
