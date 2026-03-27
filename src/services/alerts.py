"""
Сервис алертов — отправляет уведомления об ошибках администратору в Telegram.

Использование:
    from src.services.alerts import alert

    await alert.send("Критическая ошибка в БД", error=e)

Также подключается автоматически через TelegramAlertHandler к logging —
все ERROR и CRITICAL логи уходят в Telegram без дополнительного кода.
"""

import asyncio
import logging
import os
import traceback
from datetime import datetime, timezone

import aiohttp

logger = logging.getLogger(__name__)

ADMIN_CHAT_ID = 1199681092

# Иконки по уровню severity
_ICONS = {
    "critical": "🚨",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
}

# Глобальный флаг чтобы не слать алерты из самого сервиса алертов (рекурсия)
_sending = False


class AlertService:
    """Отправляет форматированные алерты администратору через Telegram Bot API."""

    def __init__(self) -> None:
        self._bot_token: str | None = None
        self._chat_id: int = ADMIN_CHAT_ID
        self._session: aiohttp.ClientSession | None = None
        # Очередь для алертов, которые пришли до инициализации токена
        self._queue: list[str] = []

    def configure(self, bot_token: str, chat_id: int = ADMIN_CHAT_ID) -> None:
        """Вызвать один раз при старте приложения."""
        self._bot_token = bot_token
        self._chat_id = chat_id

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _do_send(self, text: str) -> None:
        if not self._bot_token:
            return
        global _sending
        if _sending:
            return
        _sending = True
        try:
            session = await self._get_session()
            url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
            payload = {
                "chat_id": self._chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning("Alert send failed (%s): %s", resp.status, body)
        except Exception as exc:
            logger.warning("Alert send exception: %s", exc)
        finally:
            _sending = False

    async def send(
        self,
        message: str,
        *,
        level: str = "error",
        error: Exception | None = None,
        source: str | None = None,
    ) -> None:
        """
        Отправить алерт.

        :param message: Краткое описание проблемы
        :param level: "critical" | "error" | "warning" | "info"
        :param error: Исключение (трейсбек добавится автоматически)
        :param source: Метка модуля/компонента
        """
        icon = _ICONS.get(level, "❌")
        env = os.getenv("APP_ENV", "production")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        lines = [
            f"{icon} <b>[{level.upper()}]</b> {f'[{env}]' if env != 'production' else ''}",
            f"⏰ {now}",
        ]
        if source:
            lines.append(f"📍 <code>{source}</code>")
        lines.append(f"\n{message}")

        if error is not None:
            tb = traceback.format_exception(type(error), error, error.__traceback__)
            tb_text = "".join(tb).strip()
            # Telegram message limit — 4096 chars; оставляем хвост трейсбека
            max_tb = 1500
            if len(tb_text) > max_tb:
                tb_text = "..." + tb_text[-max_tb:]
            lines.append(f"\n<pre>{_escape_html(tb_text)}</pre>")

        text = "\n".join(lines)
        # Обрезаем до лимита Telegram
        if len(text) > 4096:
            text = text[:4090] + "\n..."

        if not self._bot_token:
            # Буферизуем до configure()
            self._queue.append(text)
            return

        # Отправляем накопленное из очереди
        while self._queue:
            queued = self._queue.pop(0)
            await self._do_send(queued)

        await self._do_send(text)

    def send_sync(self, message: str, *, level: str = "error", error: Exception | None = None, source: str | None = None) -> None:
        """Синхронная обёртка — планирует send() в текущем event loop если он есть."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.send(message, level=level, error=error, source=source))
        except RuntimeError:
            # Нет running loop — создаём новый (например, в потоке или при shutdown)
            try:
                asyncio.run(self.send(message, level=level, error=error, source=source))
            except Exception:
                pass


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# Глобальный синглтон
alert = AlertService()


class TelegramAlertHandler(logging.Handler):
    """
    Logging handler: автоматически шлёт алерты в Telegram
    для всех записей уровня ERROR и выше.

    Подключается один раз в main():
        logging.getLogger().addHandler(TelegramAlertHandler())
    """

    # Модули, которые не нужно дублировать в алерты (слишком шумные)
    _IGNORED_LOGGERS = {
        "aiogram",
        "aiogram.event",
        "aiohttp",
        "apscheduler",
        "sqlalchemy.pool",
        "src.services.alerts",  # сам себя не алертим
    }

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno < logging.ERROR:
            return

        # Пропускаем шумные библиотеки
        for ignored in self._IGNORED_LOGGERS:
            if record.name.startswith(ignored):
                return

        level = "critical" if record.levelno >= logging.CRITICAL else "error"
        message = self.format(record)

        error: Exception | None = None
        if record.exc_info and record.exc_info[1]:
            error = record.exc_info[1]

        alert.send_sync(
            message=record.getMessage(),
            level=level,
            error=error,
            source=record.name,
        )
