from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.db.user_dao import UserDAO
from src.keyboards.main_menu import get_main_menu
from src.keyboards.profile import get_profile_actions_keyboard

router = Router(name="profile")


@router.message(F.text == "👤 Мой профиль")
async def show_profile(message: Message, session_maker: async_sessionmaker) -> None:
    async with session_maker() as session:
        dao = UserDAO(session)
        user = await dao.get_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer(
            "⚠️ Вы не зарегистрированы. Напишите /start для регистрации.",
            reply_markup=get_main_menu(),
        )
        return

    # Формируем строку статуса подписки
    if user.subscription_status == "pro" and user.subscription_end_date:
        end = user.subscription_end_date.strftime("%d.%m.%Y")
        subscription_text = f"⭐ PRO (до {end})"
    else:
        subscription_text = "🔒 Free (подписка не приобретена)"

    avg_stress = (
        f"{user.avg_stress_index:.1f}" if user.avg_stress_index is not None else "—"
    )
    dominant = user.dominant_area or "—"

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
async def profile_new_spread(callback: CallbackQuery) -> None:
    await callback.answer("🚧 Раздел в разработке", show_alert=True)


@router.callback_query(F.data == "profile:buy_pro")
async def profile_buy_pro(callback: CallbackQuery) -> None:
    await callback.answer("🚧 Раздел в разработке", show_alert=True)


@router.callback_query(F.data == "profile:back")
async def profile_back(callback: CallbackQuery) -> None:
    await callback.message.delete()
    await callback.message.answer("Выберите действие:", reply_markup=get_main_menu())
    await callback.answer()
