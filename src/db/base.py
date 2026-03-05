from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings
from src.db.models import Base


async def _migrate(engine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_date DATE"
        ))
        await conn.execute(text(
            "ALTER TABLE users DROP COLUMN IF EXISTS age"
        ))


async def create_session_maker() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _migrate(engine)

    return async_sessionmaker(engine, expire_on_commit=False)
