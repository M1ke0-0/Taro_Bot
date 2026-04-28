import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from datetime import datetime, timezone
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from arq import create_pool

from src.config import settings
from src.db.base import create_session_maker
from src.handlers import setup_routers
from src.middlewares.throttling import ThrottlingMiddleware
from src.services.scheduler import check_and_send_weekly_reports
from src.services.alerts import alert, TelegramAlertHandler


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logging.getLogger().addHandler(TelegramAlertHandler())

    # --- Proxy support ---
    proxy_url = os.getenv("PROXY_URL")  # e.g. socks5://user:pass@host:port
    if proxy_url:
        logging.getLogger(__name__).info("Using proxy: %s", proxy_url)
        session = AiohttpSession(proxy=proxy_url)
    else:
        session = AiohttpSession()


    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )
    alert.configure(bot_token=settings.BOT_TOKEN)

    # RedisStorage — если REDIS_URL задан (production), иначе MemoryStorage (dev)
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            from aiogram.fsm.storage.redis import RedisStorage
            storage = RedisStorage.from_url(redis_url)
            logging.getLogger(__name__).info("FSM storage: Redis (%s)", redis_url)
        except Exception as e:
            logging.getLogger(__name__).warning("Redis unavailable, fallback to MemoryStorage: %s", e)
            storage = MemoryStorage()
    else:
        storage = MemoryStorage()
        logging.getLogger(__name__).info("FSM storage: MemoryStorage (REDIS_URL not set)")

    dp = Dispatcher(storage=storage)
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())

    session_maker = await create_session_maker()
    dp["session_maker"] = session_maker

    from src.db.setting_dao import SettingDAO
    async with session_maker() as session:
        await SettingDAO(session).init_defaults()

    import src.db.redis as redis_module
    if redis_url:
        try:
            from arq.connections import RedisSettings
            redis_module.arq_pool = await create_pool(RedisSettings.from_dsn(redis_url))
            logging.getLogger(__name__).info("ARQ pool initialized")
        except Exception as e:
            logging.getLogger(__name__).warning("Failed to init ARQ pool: %s", e)

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

    # Запускаем aiohttp-сервер для webhook ЮKassa
    if settings.YOOKASSA_SHOP_ID and settings.YOOKASSA_SECRET_KEY:
        from src.services.yookassa_webhook import setup_yookassa_webhook
        yk_app = web.Application()
        setup_yookassa_webhook(yk_app, bot, session_maker)
        yk_runner = web.AppRunner(yk_app)
        await yk_runner.setup()
        yk_site = web.TCPSite(yk_runner, host="0.0.0.0", port=settings.YOOKASSA_WEBHOOK_PORT)
        await yk_site.start()
        logging.getLogger(__name__).info(
            "YooKassa webhook listening on port %s", settings.YOOKASSA_WEBHOOK_PORT
        )

    webhook_url = os.getenv("WEBHOOK_URL")

    if webhook_url:
        async def on_startup(bot: Bot):
            await bot.set_webhook(f"{webhook_url}/webhook")
        dp.startup.register(on_startup)

        app = web.Application()
        webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
        webhook_requests_handler.register(app, path="/webhook")
        setup_application(app, dp, bot=bot)

        logging.info(f"Starting webhook server on port {os.getenv('WEBHOOK_PORT', 8080)}")
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=os.getenv("WEBHOOK_HOST", "0.0.0.0"), port=int(os.getenv("WEBHOOK_PORT", 8080)))
        await site.start()
        
        # Keep the process running
        await asyncio.Event().wait()
    else:
        logging.info("Starting polling mode (WEBHOOK_URL not set)")
        retry_delay = 15  # seconds
        max_delay = 300   # 5 minutes
        attempt = 0
        while True:
            try:
                await bot.delete_webhook(drop_pending_updates=True)
                break  # connected — exit retry loop
            except Exception as e:
                attempt += 1
                delay = min(retry_delay * attempt, max_delay)
                logging.getLogger(__name__).error(
                    "Cannot reach Telegram (attempt %d): %s. Retrying in %ds...",
                    attempt, e, delay
                )
                await asyncio.sleep(delay)
        try:
            await dp.start_polling(bot)
        finally:
            await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
