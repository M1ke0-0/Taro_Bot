from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from src.keyboards.pro import get_pro_keyboard

from sqlalchemy.ext.asyncio import async_sessionmaker
from src.db.setting_dao import SettingDAO

router = Router(name="pro")

def get_pro_text(price: str) -> str:
    return (
        "🔮 <b>Подписка PRO</b>\n\n"
        "Открой полный доступ к возможностям бота и получай более глубокие и точные разборы.\n\n"
        "<b>Что входит в PRO:</b>\n\n"
        "✨ <b>Полные AI-разборы карт</b>\n"
        "— подробное объяснение значения карты именно для твоей ситуации\n\n"
        "📊 <b>Недельный AI-отчёт</b>\n"
        "— анализ твоего эмоционального состояния, тенденций и советов на неделю\n\n"
        "🃏 <b>Безлимитные расклады</b>\n"
        "— больше карт и более глубокие комбинации\n\n"
        "🧠 <b>Персонализированные рекомендации</b>\n"
        "— бот учитывает твои предыдущие расклады\n\n"
        "⚡️ <b>Быстрый доступ ко всем функциям без ограничений</b>\n\n"
        f"💎 <b>Стоимость:</b> <i>{price} руб / месяц</i>\n\n"
        "Нажми кнопку ниже, чтобы открыть полный потенциал бота."
    )


@router.message(F.text == "⭐ PRO")
async def show_pro_info_message(message: Message, session_maker: async_sessionmaker) -> None:
    async with session_maker() as session:
        price = await SettingDAO(session).get_setting("pro_sub_price", "500")
    await message.answer(get_pro_text(price), reply_markup=get_pro_keyboard())


@router.callback_query(F.data == "profile:buy_pro")
async def show_pro_info_callback(callback: CallbackQuery, session_maker: async_sessionmaker) -> None:
    async with session_maker() as session:
        price = await SettingDAO(session).get_setting("pro_sub_price", "500")
    await callback.message.answer(get_pro_text(price), reply_markup=get_pro_keyboard())
    await callback.answer()


@router.callback_query(F.data == "pro:buy")
async def process_buy_pro(callback: CallbackQuery) -> None:
    await callback.answer("🚧 Интеграция оплаты в разработке...", show_alert=True)
