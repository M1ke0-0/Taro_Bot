from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import User


class UserDAO:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def exists(self, telegram_id: int) -> bool:
        result = await self._session.execute(
            select(User.id).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none() is not None

    async def create(
        self,
        telegram_id: int,
        name: str,
        username: str | None,
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            name=name,
            username=username,
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        result = await self._session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def update_spread_stats(
        self,
        telegram_id: int,
        stress_index: float,
        dominant_area: str,
    ) -> None:
        """Обновляет статистику пользователя после расклада."""
        result = await self._session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            return

        # Пересчёт скользящего среднего стресс-индекса
        prev_avg = user.avg_stress_index or 0.0
        n = user.total_spreads
        new_avg = (prev_avg * n + stress_index) / (n + 1) if n > 0 else stress_index

        user.total_spreads += 1
        user.avg_stress_index = round(new_avg, 2)
        user.dominant_area = dominant_area

        await self._session.commit()

    async def set_pro_status(self, telegram_id: int) -> None:
        """Устанавливает статус подписки PRO для пользователя."""
        result = await self._session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.subscription_status = "pro"
            await self._session.commit()

    async def update_last_report_date(self, telegram_id: int) -> None:
        """Обновляет дату последнего просмотра недельного отчета."""
        from datetime import datetime
        result = await self._session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.last_report_date = datetime.now()
            await self._session.commit()

    async def save_weekly_report_cache(self, telegram_id: int, report_text: str) -> None:
        """Сохраняет кеш недельного отчета и обновляет дату."""
        import logging
        logger = logging.getLogger(__name__)
        from datetime import datetime, timezone
        
        logger.info(f"Looking for user {telegram_id} to save cache.")
        result = await self._session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user:
            logger.info("User found, updating last_report_date and cached_weekly_report.")
            user.last_report_date = datetime.now(timezone.utc)
            user.cached_weekly_report = report_text
            await self._session.commit()
            logger.info("Commit successful.")
        else:
            logger.error(f"User {telegram_id} not found in save_weekly_report_cache!")

