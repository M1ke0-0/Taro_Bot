import html
import re
from datetime import date, datetime

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.db.user_dao import UserDAO
from src.keyboards.main_menu import get_main_menu
from src.keyboards.registration import get_consent_keyboard

router = Router(name="registration")

NAME_RE = re.compile(r"^[А-Яа-яЁёA-Za-z]{2,20}$")


class Registration(StatesGroup):
    consent = State()
    name = State()



@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session_maker: async_sessionmaker) -> None:
    async with session_maker() as session:
        dao = UserDAO(session)
        already_registered = await dao.exists(message.from_user.id)

    if already_registered:
        await message.answer(
            "С возвращением! Выберите действие:",
            reply_markup=get_main_menu(),
        )
        return

    await state.set_state(Registration.consent)
    await message.answer(
        "👋 Привет! Перед регистрацией необходимо ваше согласие на обработку персональных данных.\n\n"
        "📋 <b>Мы собираем:</b> ваше имя.\n"
        "Данные используются только для работы бота и не передаются третьим лицам.\n\n"
        "Вы согласны на сбор и обработку ваших персональных данных?",
        reply_markup=get_consent_keyboard(),
    )



@router.callback_query(Registration.consent, F.data == "consent:accept")
async def process_consent_accept(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Registration.name)
    await callback.message.edit_text("✅ Спасибо! Вы дали согласие на обработку данных.")
    await callback.message.answer("Пожалуйста, введите ваше имя:")
    await callback.answer()


@router.callback_query(Registration.consent, F.data == "consent:decline")
async def process_consent_decline(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "❌ Вы отказались от обработки персональных данных.\n\n"
        "К сожалению, без согласия мы не можем предоставить доступ к боту. "
        "Если передумаете — напишите /start."
    )
    await callback.answer()









@router.message(Registration.name, F.text)
async def process_name(message: Message, state: FSMContext, session_maker: async_sessionmaker) -> None:
    name = message.text.strip()
    if not NAME_RE.match(name):
        await message.answer(
            "⚠️ Имя должно содержать только русские или английские буквы "
            "и быть длиной от 2 до 20 символов. Попробуйте ещё раз:"
        )
        return

    await state.clear()
    
    async with session_maker() as session:
        dao = UserDAO(session)
        await dao.create(
            telegram_id=message.from_user.id,
            name=name,
            username=message.from_user.username,
        )

    await message.answer(
        f"Приятно познакомиться, {html.escape(name)}! 😊\n\n"
        "Я бот психологического Таро. Я помогаю анализировать состояние "
        "и находить внутренние ресурсы через архетипы карт.",
        reply_markup=get_main_menu(),
    )
