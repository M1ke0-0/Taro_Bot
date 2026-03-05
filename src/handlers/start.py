import re
from datetime import date, datetime

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.db.user_dao import UserDAO
from src.keyboards.main_menu import get_main_menu
from src.keyboards.registration import get_consent_keyboard, get_gender_keyboard, get_phone_keyboard

router = Router(name="registration")

NAME_RE = re.compile(r"^[А-Яа-яЁёA-Za-z]{2,20}$")


class Registration(StatesGroup):
    consent = State()
    phone = State()
    name = State()
    gender = State()
    age = State()



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
        "📋 <b>Мы собираем:</b> имя, пол, возраст и номер телефона.\n"
        "Данные используются только для работы бота и не передаются третьим лицам.\n\n"
        "Вы согласны на сбор и обработку ваших персональных данных?",
        reply_markup=get_consent_keyboard(),
    )



@router.callback_query(Registration.consent, F.data == "consent:accept")
async def process_consent_accept(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Registration.phone)
    await callback.message.edit_text("✅ Спасибо! Вы дали согласие на обработку данных.")
    await callback.message.answer(
        "Для продолжения регистрации поделитесь своим номером телефона:",
        reply_markup=get_phone_keyboard(),
    )
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



@router.message(Registration.phone, F.contact)
async def process_phone(message: Message, state: FSMContext) -> None:
    phone = message.contact.phone_number
    await state.update_data(phone=phone)
    await state.set_state(Registration.name)
    await message.answer(
        "✅ Номер получен!\n\nВведите ваше имя:",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Registration.phone)
async def process_phone_wrong(message: Message) -> None:
    await message.answer(
        "⚠️ Пожалуйста, воспользуйтесь кнопкой «Поделиться номером» ниже.",
        reply_markup=get_phone_keyboard(),
    )



@router.message(Registration.name, F.text)
async def process_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not NAME_RE.match(name):
        await message.answer(
            "⚠️ Имя должно содержать только русские или английские буквы "
            "и быть длиной от 2 до 20 символов. Попробуйте ещё раз:"
        )
        return

    await state.update_data(name=name)
    await state.set_state(Registration.gender)
    await message.answer(
        f"Приятно познакомиться, {name}! 😊\n\nВыберите ваш пол:",
        reply_markup=get_gender_keyboard(),
    )



@router.callback_query(Registration.gender, F.data.startswith("gender:"))
async def process_gender(callback: CallbackQuery, state: FSMContext) -> None:
    gender = callback.data.split(":")[1]  
    gender_label = "👨 Мужской" if gender == "male" else "👩 Женский"
    await state.update_data(gender=gender)
    await state.set_state(Registration.age)
    await callback.message.edit_text(f"Ваш пол: <b>{gender_label}</b>")
    await callback.message.answer("Введите дату рождения в формате ДД.ММ.ГГГГ:")
    await callback.answer()



@router.message(Registration.age, F.text)
async def process_age(message: Message, state: FSMContext, session_maker: async_sessionmaker) -> None:
    text = message.text.strip()

    try:
        birth_date = datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        await message.answer(
            "⚠️ Неверный формат. Введите дату рождения в формате <b>ДД.ММ.ГГГГ</b>\n"
            "Например: <code>15.03.1995</code>"
        )
        return

    today = date.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    if birth_date > today:
        await message.answer("⚠️ Дата рождения не может быть в будущем. Попробуйте ещё раз:")
        return
    if age < 14:
        await message.answer("⚠️ Возраст должен быть не менее 14 лет. Попробуйте ещё раз:")
        return
    if age > 120:
        await message.answer("⚠️ Введите корректную дату рождения. Попробуйте ещё раз:")
        return

    data = await state.get_data()
    await state.clear()

    async with session_maker() as session:
        dao = UserDAO(session)
        await dao.create(
            telegram_id=message.from_user.id,
            name=data["name"],
            gender=data["gender"],
            birth_date=birth_date,
            phone=data["phone"],
        )

    await message.answer(
        "Привет! Я бот психологического Таро. Я помогаю анализировать состояние "
        "и находить внутренние ресурсы через архетипы карт.",
        reply_markup=get_main_menu(),
    )
