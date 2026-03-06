from aiogram.filters import BaseFilter
from aiogram.types import Message

from src.config import settings


class IsAdmin(BaseFilter):
    """
    Фильтр для проверки, является ли пользователь администратором.
    Сравнивает ID пользователя с ADMIN_ID из настроек.
    """
    
    async def __call__(self, message: Message) -> bool:
        return message.from_user is not None and message.from_user.id == settings.ADMIN_ID
