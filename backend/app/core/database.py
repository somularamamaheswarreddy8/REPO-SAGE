import logging
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.core.config import settings

logger = logging.getLogger(__name__)

# Determine active database URL (allow automatic SQLite fallback if Postgres is down)
active_db_url = settings.DATABASE_URL
is_sqlite = active_db_url.startswith("sqlite")

engine_args = {}
if is_sqlite:
    engine_args["connect_args"] = {"check_same_thread": False}
else:
    engine_args["pool_size"] = 10
    engine_args["max_overflow"] = 20

engine = create_async_engine(active_db_url, echo=settings.DEBUG, **engine_args)

class _AsyncSessionMakerProxy:
    """Dynamic proxy ensuring imported references to AsyncSessionLocal always use the active engine."""
    def __init__(self, maker):
        self._maker = maker

    def set_maker(self, maker):
        self._maker = maker

    def __call__(self, *args, **kwargs):
        return self._maker(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._maker, name)

_initial_sessionmaker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)
AsyncSessionLocal = _AsyncSessionMakerProxy(_initial_sessionmaker)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    """Initializes tables and extensions (e.g. pgvector if on PostgreSQL, with SQLite fallback)."""
    global engine, is_sqlite, active_db_url

    try:
        async with engine.begin() as conn:
            if not is_sqlite:
                try:
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                    logger.info("pgvector extension initialized or already exists.")
                except Exception as e:
                    logger.warning(f"Could not initialize pgvector extension: {e}")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables verified/created successfully.")
    except Exception as e:
        if not is_sqlite:
            logger.warning(f"PostgreSQL connection failed ({e}). Falling back to local SQLite database (reposage.db)...")
            active_db_url = "sqlite+aiosqlite:///./reposage.db"
            is_sqlite = True
            await engine.dispose()
            engine = create_async_engine(active_db_url, echo=settings.DEBUG, connect_args={"check_same_thread": False})
            new_maker = async_sessionmaker(
                bind=engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False
            )
            AsyncSessionLocal.set_maker(new_maker)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Local SQLite database initialized successfully.")
        else:
            raise


def check_is_sqlite() -> bool:
    return bool(is_sqlite)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
