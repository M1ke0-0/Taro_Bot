from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.db.user_dao import UserDAO
from src.keyboards.main_menu import get_return_to_main_menu_keyboard

router = Router(name="settings")

@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message, session_maker: async_sessionmaker) -> None:
    async with session_maker() as session:
        user = await UserDAO(session).get_by_telegram_id(message.from_user.id)
        is_pro = user and user.subscription_status == "pro"

    if not is_pro:
        await message.answer("⚠️ Настройки доступны только для пользователей с PRO-подпиской.")
        return

    text = (
        "⚙️ <b>Настройки PRO-аккаунта</b>\n\n"
        "Здесь вы сможете:\n"
        "• Изменить вашу доминирующую сферу\n"
        "• Настроить уведомления о недельных отчетах\n"
        "• Управлять подпиской\n\n"
        "<i>(Функционал находится в разработке)</i>"
    )
    await message.answer(text, reply_markup=get_return_to_main_menu_keyboard())
