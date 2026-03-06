import random
from typing import List

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import TarotCard


class TarotCardDAO:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_random_cards(self, n: int = 3) -> List[TarotCard]:
        """Возвращает n случайных карт из таблицы."""
        result = await self._session.execute(
            select(TarotCard).order_by(func.random()).limit(n)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        """Возвращает количество карт в таблице."""
        result = await self._session.execute(
            select(func.count(TarotCard.id))
        )
        return result.scalar_one()

    async def update_photo(self, card_id: int, file_id: str) -> None:
        """Обновляет путь к фото или file_id для карты."""
        await self._session.execute(
            update(TarotCard).where(TarotCard.id == card_id).values(photo=file_id)
        )
