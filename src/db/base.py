from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings
from src.db.models import Base


async def create_session_maker() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=100,       # базовый пул соединений
        max_overflow=150,    # дополнительные соединения при пике
        pool_timeout=40,     # сек ожидания свободного соединения
        pool_recycle=1800,   # пересоздавать соединения каждые 30 мин
    )

    # Создаём таблицы при старте (если не существуют)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        from src.services.alerts import alert
        await alert.send("Не удалось подключиться к PostgreSQL при старте", error=e, level="critical", source="db.base")
        raise

    return async_sessionmaker(engine, expire_on_commit=False)
