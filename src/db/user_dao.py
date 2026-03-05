from datetime import date
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
        gender: str,
        birth_date: date,
        phone: str,
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            name=name,
            gender=gender,
            birth_date=birth_date,
            phone=phone,
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
