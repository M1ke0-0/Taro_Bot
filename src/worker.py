import logging
import os
from arq.connections import RedisSettings
from aiogram import Bot

from src.config import settings
from src.services.openrouter import get_spread_interpretation
from src.keyboards.spread import get_post_spread_keyboard
from src.db.base import create_session_maker
from src.db.user_dao import UserDAO
from src.db.spread_history_dao import SpreadHistoryDAO

logger = logging.getLogger(__name__)

async def generate_spread_and_send(ctx, telegram_id: int, card_names: list[str], topic: str, question: str | None, is_pro: bool, single_price: str, stress_index: float, dominant_area: str):
    logger.info(f"Worker started spread generation for user {telegram_id}")
    bot: Bot = ctx['bot']
    session_maker = ctx['session_maker']
    
    # Generate interpretation via AI
    try:
        interpretation = await get_spread_interpretation(
            card_names=card_names,
            topic=topic,
            question=question,
            is_pro=is_pro,
        )
    except Exception as e:
        logger.error(f"Worker failed to get interpretation: {e}")
        await bot.send_message(telegram_id, "⚠️ Произошла ошибка при анализе расклада нейросетью. Попробуйте еще раз позже.")
        return

    # Split and send
    max_length = 4000
    paragraphs = interpretation.split('\n')
    current_chunk = ""
    chunks = []
    
    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) + 1 > max_length:
            chunks.append(current_chunk)
            current_chunk = paragraph
        else:
            if current_chunk:
                current_chunk += "\n" + paragraph
            else:
                current_chunk = paragraph
    
    if current_chunk:
        chunks.append(current_chunk)

    for i, chunk in enumerate(chunks):
        reply_markup = get_post_spread_keyboard(is_pro=is_pro, price=single_price) if i == len(chunks) - 1 else None
        
        try:
            await bot.send_message(
                telegram_id,
                chunk, 
                parse_mode=None, 
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Failed to send chunk to {telegram_id}: {e}")

    # Update DB stats
    area_labels = {
        "love": "Любовь",
        "career": "Карьера",
        "money": "Деньги",
        "psy": "Психика",
    }
    
    try:
        async with session_maker() as session:
            user_dao = UserDAO(session)
            user = await user_dao.get_by_telegram_id(telegram_id)
            
            await user_dao.update_spread_stats(
                telegram_id=telegram_id,
                stress_index=round(stress_index, 2),
                dominant_area=area_labels.get(dominant_area, dominant_area),
            )
            
            if user:
                history_dao = SpreadHistoryDAO(session)
                await history_dao.add_history(
                    user_id=user.id,
                    topic=area_labels.get(topic, topic),
                    cards=", ".join(card_names),
                    stress_index=round(stress_index, 2)
                )
                await session.commit()
    except Exception as e:
        logger.error(f"Worker failed to update DB stats for {telegram_id}: {e}")
        
    logger.info(f"Worker finished spread for user {telegram_id}")


async def startup(ctx):
    ctx['bot'] = Bot(token=settings.BOT_TOKEN)
    ctx['session_maker'] = await create_session_maker()
    logger.info("Worker started up")

async def shutdown(ctx):
    await ctx['bot'].session.close()
    logger.info("Worker shutting down")

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

class WorkerSettings:
    functions = [generate_spread_and_send]
    redis_settings = RedisSettings.from_dsn(redis_url)
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 50
