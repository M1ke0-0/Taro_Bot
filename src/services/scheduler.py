import logging
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.db.user_dao import UserDAO

logger = logging.getLogger(__name__)

async def check_and_send_weekly_reports(bot: Bot, session_maker: async_sessionmaker) -> None:
    logger.info("Starting automated weekly reports check.")
    now = datetime.now(timezone.utc)
    users_to_report = []

    # 1. Сначала находим всех пользователей, которым пора отправлять отчет
    async with session_maker() as session:
        # Получаем всех PRO пользователей
        from sqlalchemy import select
        from src.db.models import User
        result = await session.execute(select(User).where(User.subscription_status == "pro"))
        pro_users = result.scalars().all()

        for user in pro_users:
            if user.last_report_date is None:
                users_to_report.append(user.telegram_id)
            else:
                diff_days = (now.astimezone() - user.last_report_date).days if user.last_report_date.tzinfo else (now.replace(tzinfo=None) - user.last_report_date).days
                if diff_days >= 7:
                    users_to_report.append(user.telegram_id)

    logger.info(f"Found {len(users_to_report)} users eligible for weekly reports.")

    # 2. Отправляем уведомления
    for telegram_id in users_to_report:
        try:
            from aiogram.types import InlineKeyboardButton
            from aiogram.utils.keyboard import InlineKeyboardBuilder
            
            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(text="📊 Посмотреть отчет", callback_data="report:generate"))
            
            await bot.send_message(
                telegram_id, 
                "🌟 <b>У вас готов новый еженедельный отчет!</b>\n\n"
                "Прошла неделя! Искусственный интеллект проанализировал ваши свежие расклады и подготовил новую аналитику. Хотите посмотреть?",
                reply_markup=builder.as_markup()
            )

            # Обновляем БД и сохраняем кеш как NOTIFIED, чтобы не спамить
            async with session_maker() as session:
                await UserDAO(session).save_weekly_report_cache(telegram_id, "NOTIFIED")
                
            logger.info(f"Successfully sent automated notification to {telegram_id}.")

        except TelegramForbiddenError:
            logger.warning(f"User {telegram_id} blocked the bot.")
        except Exception as e:
            logger.error(f"Error sending automated notification to {telegram_id}: {e}", exc_info=True)
