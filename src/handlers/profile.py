import html

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.db.tarot_card_dao import TarotCardDAO
from src.db.user_dao import UserDAO
from src.db.spread_history_dao import SpreadHistoryDAO
from src.handlers.spread import SpreadStates
from src.keyboards.main_menu import get_main_menu
from src.keyboards.profile import get_profile_actions_keyboard
from src.keyboards.spread import get_topic_keyboard

router = Router(name="profile")


@router.message(F.text == "👤 Мой профиль")
async def show_profile(message: Message, session_maker: async_sessionmaker) -> None:
    async with session_maker() as session:
        dao = UserDAO(session)
        user = await dao.get_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer(
            "⚠️ Вы не зарегистрированы. Напишите /start для регистрации.",
            reply_markup=get_main_menu(is_pro=False),
        )
        return

    # Формируем строку статуса подписки
    if user.subscription_status == "pro":
        if user.subscription_end_date:
            end = user.subscription_end_date.strftime("%d.%m.%Y")
            subscription_text = f"⭐ PRO (до {end})"
        else:
            subscription_text = "⭐ PRO (безлимит)"
    else:
        subscription_text = "🔒 Free (подписка не приобретена)"

    avg_stress = (
        f"{user.avg_stress_index:.1f}" if user.avg_stress_index is not None else "—"
    )
    dominant = html.escape(user.dominant_area) if user.dominant_area else "—"

    text = (
        f"👤 <b>Ваш профиль</b>\n\n"
        f"📊 Количество раскладов: <b>{user.total_spreads}</b>\n"
        f"😓 Средний стресс-индекс: <b>{avg_stress}</b>\n"
        f"🌀 Доминирующая сфера: <b>{dominant}</b>\n\n"
        f"💳 Статус подписки: <b>{subscription_text}</b>"
    )

    await message.answer(text, reply_markup=get_profile_actions_keyboard())


# ─────────────── Действия из профиля ───────────────

@router.callback_query(F.data == "profile:new_spread")
async def profile_new_spread(callback: CallbackQuery, state: FSMContext, session_maker: async_sessionmaker) -> None:
    async with session_maker() as session:
        dao = TarotCardDAO(session)
        card_count = await dao.count()
        
        user_dao = UserDAO(session)
        user = await user_dao.get_by_telegram_id(callback.from_user.id)
        
        if user and user.subscription_status != "pro":
            history_dao = SpreadHistoryDAO(session)
            today_count = await history_dao.get_today_spread_count(user.id)
            if today_count >= 1:
                from datetime import datetime, timedelta
                now = datetime.now()
                next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                time_left = next_midnight - now
                hours, remainder = divmod(int(time_left.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)

                await callback.answer(
                    f"⚠️ На сегодня лимит раскладов исчерпан, следующий расклад будет доступен через {hours} ч. {minutes} мин.",
                    show_alert=True
                )
                return

    if card_count < 3:
        await callback.answer(
            "⚠️ В базе данных недостаточно карт Таро для расклада. Обратитесь к администратору.",
            show_alert=True
        )
        return

    await state.set_state(SpreadStates.choosing_topic)
    await callback.message.answer(
        "🔮 <b>На какую тему нужен расклад?</b>",
        reply_markup=get_topic_keyboard(),
    )
    await callback.message.delete()
    await callback.answer()



@router.callback_query(F.data == "profile:back")
async def profile_back(callback: CallbackQuery, session_maker: async_sessionmaker) -> None:
    async with session_maker() as session:
        user = await UserDAO(session).get_by_telegram_id(callback.from_user.id)
        is_pro = user and user.subscription_status == "pro"

    await callback.message.delete()
    await callback.message.answer("Выберите действие:", reply_markup=get_main_menu(is_pro=is_pro))
    await callback.answer()
