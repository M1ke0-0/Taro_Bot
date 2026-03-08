import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from datetime import datetime, timezone
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config import settings
from src.db.base import create_session_maker
from src.handlers import setup_routers
from src.middlewares.throttling import ThrottlingMiddleware
from src.services.scheduler import check_and_send_weekly_reports


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())

    session_maker = await create_session_maker()
    dp["session_maker"] = session_maker

    from src.db.setting_dao import SettingDAO
    async with session_maker() as session:
        await SettingDAO(session).init_defaults()

    setup_routers(dp)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_and_send_weekly_reports, 
        trigger="interval", 
        hours=4, 
        args=[bot, session_maker],
        next_run_time=datetime.now(timezone.utc)
    )
    scheduler.start()

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
