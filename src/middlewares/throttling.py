import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    """
    Простой middleware для предотвращения спама (Throttling).
    Ограничивает частоту сообщений и нажатий кнопок от одного пользователя.
    """
    def __init__(self, rate_limit: float = 1.0) -> None:
        self.rate_limit = rate_limit
        self.users: Dict[str, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Проверяем и Message и CallbackQuery
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
            key = f"msg_{user_id}"
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id
            key = f"cb_{user_id}"
        else:
            return await handler(event, data)

        current_time = time.time()

        # Базовая очистка словаря, чтобы не было утечки памяти
        if len(self.users) > 10000:
            self.users.clear()

        last_time = self.users.get(key)
        if last_time is not None:
            if current_time - last_time < self.rate_limit:
                # Слишком частые запросы, игнорируем событие
                if isinstance(event, CallbackQuery):
                    await event.answer("Слишком часто! Подождите немного ⏳")
                return

        self.users[key] = current_time
        return await handler(event, data)
