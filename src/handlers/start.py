import html
import os
import re
from datetime import date, datetime

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.db.user_dao import UserDAO
from src.keyboards.main_menu import get_main_menu
from src.keyboards.registration import get_consent_keyboard

router = Router(name="registration")

NAME_RE = re.compile(r"^[А-Яа-яЁёA-Za-z]{2,20}$")

_REGDOCS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "RegDocs")
)


class Registration(StatesGroup):
    consent = State()
    name = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session_maker: async_sessionmaker) -> None:
    await state.clear()

    async with session_maker() as session:
        dao = UserDAO(session)
        user = await dao.get_by_telegram_id(message.from_user.id)
        already_registered = user is not None

    if already_registered:
        is_pro = user.is_pro_active
        await message.answer(
            "С возвращением! Выберите действие:",
            reply_markup=get_main_menu(is_pro=is_pro),
        )
        return

    await state.set_state(Registration.consent)
    await message.answer(
        "Добро пожаловать!\n\n"
        "Перед началом использования бота, пожалуйста, ознакомься с условиями:\n\n"
        "Продолжая использование, ты подтверждаешь, что:\n\n"
        "— ознакомился(ась) и принимаешь условия сервиса\n"
        "— соглашаешься с обработкой персональных данных\n"
        "— понимаешь, что сервис носит информационный характер\n\n"
        "Нажми кнопку ниже, чтобы продолжить 👇",
        reply_markup=get_consent_keyboard(),
    )


@router.callback_query(Registration.consent, F.data == "consent:docs")
async def process_view_docs(callback: CallbackQuery) -> None:
    if os.path.isdir(_REGDOCS_DIR):
        doc_files = sorted([
            f for f in os.listdir(_REGDOCS_DIR)
            if os.path.isfile(os.path.join(_REGDOCS_DIR, f))
        ])
        if not doc_files:
            await callback.answer("Документы временно недоступны 😔", show_alert=True)
            return

        for filename in doc_files:
            filepath = os.path.join(_REGDOCS_DIR, filename)
            await callback.message.answer_document(FSInputFile(filepath))

        await callback.answer("Все документы отправлены! 📄")
    else:
        await callback.answer("Папка с документами не найдена ❌", show_alert=True)


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
        "Я бот — инструмент для саморефлексии и анализа жизненных ситуаций с помощью символики карт Таро и AI-интерпретаций.\n\n"
        "Здесь ты можешь:\n\n"
        "🃏 посмотреть на свою ситуацию под новым углом \n"
        "🧠 лучше понять свои мысли и эмоции\n"
        "🤖 получить более глубокий AI-разбор \n"
        "Карты не дают «готовых ответов» — они помогают увидеть то, что уже есть внутри тебя.\n\n"
        "👇 С чего начать:\n\n"
        "Нажми «🃏 Сделать расклад»\n"
        "Сформулируй свой вопрос\n"
        "Получи интерпретацию и новые идеи для размышления\n",
        reply_markup=get_main_menu(is_pro=False),
    )
