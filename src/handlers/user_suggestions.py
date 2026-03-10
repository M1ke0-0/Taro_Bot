import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.config import settings
from src.db.models import Suggestion
from src.db.user_dao import UserDAO
from src.keyboards.main_menu import get_return_to_main_menu_keyboard, get_main_menu

logger = logging.getLogger(__name__)

router = Router(name="user_suggestions")

class SuggestionStates(StatesGroup):
    waiting_for_suggestion = State()

@router.message(F.text == "💡 Предложить улучшение")
async def process_suggest_improvement(message: Message, state: FSMContext) -> None:
    await state.set_state(SuggestionStates.waiting_for_suggestion)
    await message.answer(
        "💡 Напишите ваше предложение по улучшению бота.\n"
        "Мы внимательно читаем все отзывы и стараемся сделать сервис лучше!\n\n"
        "Если вы передумали, нажмите «🔙 Возврат в меню».",
        reply_markup=get_return_to_main_menu_keyboard()
    )


@router.message(SuggestionStates.waiting_for_suggestion, F.text)
async def process_suggestion_text(message: Message, state: FSMContext, session_maker: async_sessionmaker) -> None:
    if message.text == "🔙 Возврат в меню":
        await state.clear()
        
        async with session_maker() as session:
            user_dao = UserDAO(session)
            user = await user_dao.get_by_telegram_id(message.from_user.id)
            is_pro = user.subscription_status == "pro" if user else False
            
        await message.answer(
            "Вы вернулись в главное меню.",
            reply_markup=get_main_menu(is_pro=is_pro)
        )
        return

    suggestion_text = message.text.strip()
    
    async with session_maker() as session:
        user_dao = UserDAO(session)
        user = await user_dao.get_by_telegram_id(message.from_user.id)
        
        if not user:
            # User might not exist yet, though extremely unlikely if they have the menu
            user_id = 0 # Default fallback or error handling
            logger.warning("User not found when creating suggestion: %s", message.from_user.id)
        else:
            user_id = user.id

        suggestion = Suggestion(
            user_id=user_id,
            text=suggestion_text
        )
        session.add(suggestion)
        await session.commit()
        
    await state.clear()
    
    async with session_maker() as session:
        user_dao = UserDAO(session)
        user = await user_dao.get_by_telegram_id(message.from_user.id)
        is_pro = user.subscription_status == "pro" if user else False

    await message.answer(
        "✅ <b>Спасибо за ваше предложение!</b>\n\nМы обязательно рассмотрим его.",
        reply_markup=get_main_menu(is_pro=is_pro)
    )
    
    # Notify admins
    for admin_id in settings.ADMIN_IDS:
        try:
            await message.bot.send_message(
                admin_id,
                f"💡 <b>Новое предложение по улучшению!</b>\n\n"
                f"От пользователя: <a href='tg://user?id={message.from_user.id}'>{message.from_user.full_name}</a>\n"
                f"Текст:\n<i>{suggestion_text}</i>"
            )
        except Exception as e:
            logger.error("Failed to notify admin %s about suggestion: %s", admin_id, e)
