from datetime import datetime, timedelta
from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import SpreadHistory


class SpreadHistoryDAO:
    """
    Класс для работы с таблицей истории раскладов.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_history(
        self, user_id: int, topic: str, cards: str, stress_index: float
    ) -> SpreadHistory:
        """
        Записывает новый расклад в историю.
        """
        history = SpreadHistory(
            user_id=user_id,
            topic=topic,
            cards=cards,
            stress_index=stress_index
        )
        self.session.add(history)
        # Сохранение (commit) обычно происходит в хендлере, но для удобства можем сделать здесь, 
        # однако правильнее делать flush/commit выше.
        await self.session.flush()
        return history

    async def get_history_last_7_days(self, user_id: int) -> Sequence[SpreadHistory]:
        """
        Получает историю раскладов пользователя за последние 7 дней.
        """
        seven_days_ago = datetime.now() - timedelta(days=7)
        stmt = (
            select(SpreadHistory)
            .where(SpreadHistory.user_id == user_id)
            .where(SpreadHistory.created_at >= seven_days_ago)
            .order_by(SpreadHistory.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_today_spread_count(self, user_id: int) -> int:
        """
        Получает количество раскладов пользователя за сегодня.
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = (
            select(func.count(SpreadHistory.id))
            .where(SpreadHistory.user_id == user_id)
            .where(SpreadHistory.created_at >= today_start)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
