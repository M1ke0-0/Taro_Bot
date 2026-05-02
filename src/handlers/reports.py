import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.spread_history_dao import SpreadHistoryDAO
from src.db.user_dao import UserDAO
from src.services.openrouter import get_weekly_report_interpretation

logger = logging.getLogger(__name__)

router = Router(name="reports")


@router.message(F.text == "📊 Недельный отчет")
async def process_weekly_report(message: Message, session: AsyncSession) -> None:
    await _generate_and_send_report(message, message.from_user.id, session)


@router.callback_query(F.data == "report:generate")
async def process_weekly_report_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer("⏳ Анализирую...", show_alert=False)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await _generate_and_send_report(callback.message, callback.from_user.id, session)


async def _generate_and_send_report(message: Message, telegram_id: int, session: AsyncSession) -> None:
    user_dao = UserDAO(session)
    user = await user_dao.get_by_telegram_id(telegram_id)

    if not user or not user.is_pro_active:
        await message.answer("Эта функция доступна только по подписке ⭐ PRO.")
        return

    if user.cached_weekly_report and user.cached_weekly_report != "NOTIFIED" and user.last_report_date:
        now = datetime.now()
        diff_days = (now.astimezone() - user.last_report_date).days if user.last_report_date.tzinfo else (now - user.last_report_date).days
        if diff_days < 7:
            await message.answer(user.cached_weekly_report, parse_mode="HTML")
            return

    history_dao = SpreadHistoryDAO(session)
    history = await history_dao.get_history_last_7_days(user.id)

    if not history:
        await message.answer("У вас еще нет раскладов за последние 7 дней. Сделайте пару раскладов, чтобы ИИ мог собрать статистику!")
        return

    status_msg = await message.answer("⏳ Анализирую ваши расклады за неделю и готовлю отчет...")

    from collections import Counter
    topics = [h.topic for h in history]
    all_cards = []
    for h in history:
        all_cards.extend([c.strip() for c in h.cards.split(",")])
    total_stress = sum(h.stress_index for h in history)
    avg_stress = total_stress / len(history)
    card_counts = Counter(all_cards)
    top_cards = [card for card, _ in card_counts.most_common(3)]
    dominant_area = Counter(topics).most_common(1)[0][0]
    day_translation = {
        "Monday": "Понедельник", "Tuesday": "Вторник", "Wednesday": "Среда",
        "Thursday": "Четверг", "Friday": "Пятница", "Saturday": "Суббота", "Sunday": "Воскресенье"
    }
    days = [h.created_at.strftime("%A") for h in history]
    peak_day_eng = Counter(days).most_common(1)[0][0]
    peak_day = day_translation.get(peak_day_eng, peak_day_eng)

    stats = {
        "avg_stress": avg_stress,
        "dominant_area": dominant_area,
        "top_cards": top_cards,
        "peak_day": peak_day,
    }

    try:
        report_text = await get_weekly_report_interpretation(stats)

        final_text = (
            f"📊 <b>Ваш Недельный Отчет</b>\n\n"
            f"📈 <i>Раскладов за неделю: {len(history)}</i>\n"
            f"📉 <i>Средний уровень стресса: {avg_stress:.1f}</i>\n"
            f"🌀 <i>Частая сфера: {dominant_area}</i>\n"
            f"📅 <i>Пиковый день: {peak_day}</i>\n\n"
            f"{report_text}"
        )
        await status_msg.edit_text(final_text, parse_mode="HTML")

        await user_dao.save_weekly_report_cache(telegram_id, final_text)

    except Exception as e:
        logger.error("Error generating weekly report", exc_info=e)
        await status_msg.edit_text("⚠️ Возникла ошибка при создании отчета. Пожалуйста, попробуйте позже.")
