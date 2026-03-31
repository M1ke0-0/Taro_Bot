"""
Хендлер для функции «Сделать расклад».
Флоу:
  1. Пользователь нажимает «🃏 Сделать расклад».
  2. Бот показывает inline-кнопки с темами.
  3. Пользователь выбирает тему (или вводит конкретный вопрос).
  4. Бот тянет 3 карты из БД, отправляет фото каждой (с задержкой 2 сек).
  5. Запрашивает AI, отправляет интерпретацию.
  6. Обновляет статистику пользователя.
"""

import asyncio
import logging
import os

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    Message, FSInputFile,
)
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.db.tarot_card_dao import TarotCardDAO
from src.db.user_dao import UserDAO
from src.db.spread_history_dao import SpreadHistoryDAO
from src.db.setting_dao import SettingDAO
from src.keyboards.spread import get_topic_keyboard, get_post_spread_keyboard
from src.keyboards.main_menu import get_main_menu
from src.enums import SpreadTopic

logger = logging.getLogger(__name__)

router = Router(name="spread")

TOPIC_NAMES = {
    SpreadTopic.LOVE: "❤️ Любовь",
    SpreadTopic.CAREER: "💼 Карьера",
    SpreadTopic.MONEY: "💰 Деньги",
    SpreadTopic.PSY: "🧠 Состояние/Психика",
}

AREA_KEYS = {
    SpreadTopic.LOVE: "love_weight",
    SpreadTopic.CAREER: "career_weight",
    SpreadTopic.MONEY: "money_weight",
    SpreadTopic.PSY: "psy_weight",
}


class SpreadStates(StatesGroup):
    choosing_topic = State()
    typing_question = State()
    generating_spread = State()


# ─────────────── Точка входа ───────────────

@router.message(F.text == "🃏 Сделать расклад")
async def cmd_spread(message: Message, state: FSMContext, session_maker: async_sessionmaker) -> None:
    current_state = await state.get_state()
    if current_state in (
        SpreadStates.generating_spread.state,
        SpreadStates.choosing_topic.state,
        SpreadStates.typing_question.state,
    ):
        await message.answer("⏳ Подождите, вы уже начали процесс. Если бот завис, выберите команду /start в меню для сброса.")
        return

    async with session_maker() as session:
        dao = TarotCardDAO(session)
        card_count = await dao.count()

        user_dao = UserDAO(session)
        user = await user_dao.get_by_telegram_id(message.from_user.id)

        if user and user.subscription_status != "pro":
            history_dao = SpreadHistoryDAO(session)
            today_count = await history_dao.get_today_spread_count(user.id)

            setting_dao = SettingDAO(session)
            free_limit_str = await setting_dao.get_setting("free_spread_limit", "1")
            try:
                free_limit = int(free_limit_str)
            except ValueError:
                free_limit = 1

            if today_count >= free_limit:
                from datetime import datetime, timedelta
                now = datetime.now()
                next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                time_left = next_midnight - now
                hours, remainder = divmod(int(time_left.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)

                await message.answer(
                    f"⚠️ <b>Лимит исчерпан</b>\n\n"
                    f"На сегодня лимит раскладов исчерпан, следующий расклад будет доступен через {hours} ч. {minutes} мин.\n"
                    f"Для снятия ограничений приобретите подписку ⭐ PRO.",
                    reply_markup=get_main_menu(is_pro=False)
                )
                return

    if card_count < 3:
        await message.answer(
            "⚠️ В базе данных недостаточно карт Таро для расклада.\n"
            "Обратитесь к администратору."
        )
        return

    await state.set_state(SpreadStates.choosing_topic)
    await message.answer(
        "🔮 <b>На какую тему нужен расклад?</b>",
        reply_markup=get_topic_keyboard(),
    )


# ─────────────── Выбор темы ───────────────

@router.callback_query(SpreadStates.choosing_topic, F.data.startswith("spread:"))
async def process_topic(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    topic = callback.data.split(":")[1]
    await callback.answer()

    await state.set_state(SpreadStates.typing_question)

    if topic == SpreadTopic.QUESTION:
        await state.update_data(topic=topic)
        await callback.message.edit_text(
            "❓ <b>Введите ваш вопрос:</b>\n\n"
            "<i>Чем конкретнее вопрос — тем точнее психологический анализ.</i>"
        )
    else:
        await state.update_data(topic=topic)
        topic_name = TOPIC_NAMES.get(topic, topic)
        await callback.message.edit_text(
            f"Тема: <b>{topic_name}</b>\n\n"
            f"❓ <b>Напишите ваш конкретный вопрос или ситуацию:</b>\n\n"
            f"<i>(Либо отправьте минус «-», чтобы получить общий расклад на эту тему)</i>"
        )


# ─────────────── Ввод вопроса ───────────────

@router.message(SpreadStates.typing_question, F.text)
async def process_question(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker,
) -> None:
    await state.set_state(SpreadStates.generating_spread)

    question = message.text.strip()
    data = await state.get_data()
    topic = data.get("topic")

    if len(question) < 5 and question != "-":
        await state.set_state(SpreadStates.typing_question)
        await message.answer("⚠️ Вопрос слишком короткий. Попробуйте ещё раз:")
        return

    if len(question) > 500:
        await state.set_state(SpreadStates.typing_question)
        await message.answer("⚠️ Вопрос слишком длинный. Пожалуйста, сформулируйте его короче (до 500 символов).")
        return

    if question == "-":
        question = None

    await state.update_data(question=question)

    if topic == SpreadTopic.QUESTION:
        await message.answer("🔮 Начинаем расклад...")
    else:
        await message.answer("🔮 Вытягиваю карты...")

    await _run_spread(message, message.from_user.id, state, session_maker)


# ─────────────── Основная логика расклада ───────────────

async def _run_spread(
    message: Message,
    user_id: int,
    state: FSMContext,
    session_maker: async_sessionmaker,
) -> None:
    data = await state.get_data()
    topic: str = data["topic"]
    question: str | None = data.get("question")
    telegram_id = user_id

    async with session_maker() as session:
        cards = await TarotCardDAO(session).get_random_cards(3)
        user = await UserDAO(session).get_by_telegram_id(telegram_id)
        single_price = await SettingDAO(session).get_setting("single_spread_price", "99")

    if len(cards) < 3:
        await message.answer("⚠️ Не удалось вытянуть карты. Попробуйте позже.")
        await state.clear()
        return

    is_pro = user and user.subscription_status == "pro"

    status_msg = await message.answer("⏳ <b>Карты тянутся...</b>")

    stress_index = sum(c.stress_weight for c in cards) / len(cards)
    card_names = [card.name for card in cards]
    if topic in AREA_KEYS:
        dominant_area = topic
    else:
        area_scores = {
            "love": sum(c.love_weight for c in cards),
            "career": sum(c.career_weight for c in cards),
            "money": sum(c.money_weight for c in cards),
            "psy": sum(c.psy_weight for c in cards),
        }
        dominant_area = max(area_scores, key=area_scores.get)

    import src.db.redis as redis_module

    if redis_module.arq_pool:
        await redis_module.arq_pool.enqueue_job(
            'generate_spread_and_send',
            telegram_id=telegram_id,
            card_names=card_names,
            topic=topic,
            question=question,
            is_pro=is_pro,
            single_price=single_price,
            stress_index=stress_index,
            dominant_area=dominant_area
        )
    else:
        from src.worker import generate_spread_and_send
        asyncio.create_task(
            generate_spread_and_send(
                {"bot": message.bot, "session_maker": session_maker},
                telegram_id=telegram_id,
                card_names=card_names,
                topic=topic,
                question=question,
                is_pro=is_pro,
                single_price=single_price,
                stress_index=stress_index,
                dominant_area=dominant_area
            )
        )

    await state.clear()

    for i, card in enumerate(cards):
        if i > 0:
            await asyncio.sleep(2)

        caption = f"🃏 <b>{card.name}</b>"

        if card.photo:
            try:
                if card.photo.startswith("Tarot_cards/"):
                    if os.path.exists(card.photo):
                        photo_obj = FSInputFile(card.photo)
                        sent_msg = await message.answer_photo(photo=photo_obj, caption=caption)
                        if sent_msg.photo:
                            file_id = sent_msg.photo[-1].file_id
                            async with session_maker() as s:
                                await TarotCardDAO(s).update_photo(card.id, file_id)
                                await s.commit()
                    else:
                        await message.answer(caption)
                else:
                    await message.answer_photo(photo=card.photo, caption=caption)
            except Exception as e:
                logger.error(f"Failed to send photo {card.photo} for id {card.id}: {e}")
                await message.answer(caption)
        else:
            await message.answer(caption)

    try:
        await status_msg.delete()
    except Exception:
        pass

    await message.answer("🔮 <b>Карты вытянуты! Интерпретирую их через призму саморефлексии и внутренних состояний...</b>\n\nСекунда — и всё будет готово.")

    logger.info("Spread queued for user %s | cards: %s", telegram_id, card_names)


# ─────────────── Дополнительные действия после расклада ───────────────

@router.callback_query(F.data == "spread:deep_dive")
async def process_deep_dive(callback: CallbackQuery) -> None:
    await callback.answer("🔄 Запускаю глубокий разбор...", show_alert=False)
    await callback.message.answer("Здесь будет функционал глубокого разбора для PRO 🔮 (в разработке)")


@router.callback_query(F.data == "spread:deep_dive_pay")
async def process_deep_dive_pay(callback: CallbackQuery, session_maker: async_sessionmaker) -> None:
    from src.config import settings
    from src.services.yookassa import create_payment

    async with session_maker() as session:
        setting_dao = SettingDAO(session)
        price_str = await setting_dao.get_setting("single_spread_price", "99")
        try:
            price = int(price_str)
        except ValueError:
            price = 99

    try:
        payment = await create_payment(
            amount=float(price),
            currency=settings.PAYMENT_CURRENCY,
            description="Разовый глубокий разбор",
            payload="single_spread",
            return_url=settings.YOOKASSA_RETURN_URL,
            telegram_id=callback.from_user.id,
        )
        await callback.message.answer(
            f"💳 <b>Оплата глубокого разбора</b>\n\n"
            f"Сумма: <b>{price} ₽</b>\n\n"
            f"Нажмите кнопку ниже для перехода на страницу оплаты.\n"
            f"После оплаты вернитесь в бот — разбор будет активирован автоматически.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Перейти к оплате", url=payment["confirmation_url"])]
            ]),
        )
    except Exception as e:
        await callback.message.answer("❌ Не удалось создать платёж. Попробуйте позже.")
        logger.error("YooKassa payment creation failed for single_spread: %s", e)

    await callback.answer()
