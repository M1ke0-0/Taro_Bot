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
from aiogram.types import CallbackQuery, Message, FSInputFile
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.db.tarot_card_dao import TarotCardDAO
from src.db.user_dao import UserDAO
from src.keyboards.spread import get_topic_keyboard
from src.keyboards.main_menu import get_main_menu
from src.services.openrouter import get_spread_interpretation

logger = logging.getLogger(__name__)

router = Router(name="spread")

TOPIC_NAMES = {
    "love": "❤️ Любовь",
    "career": "💼 Карьера",
    "money": "💰 Деньги",
    "psy": "🧠 Состояние/Психика",
}

AREA_KEYS = {
    "love": "love_weight",
    "career": "career_weight",
    "money": "money_weight",
    "psy": "psy_weight",
}


class SpreadStates(StatesGroup):
    choosing_topic = State()
    typing_question = State()
    generating_spread = State()  # Защита от race condition (спама кнопками во время расклада)


# ─────────────── Точка входа ───────────────

@router.message(F.text == "🃏 Сделать расклад")
async def cmd_spread(message: Message, state: FSMContext, session_maker: async_sessionmaker) -> None:
    async with session_maker() as session:
        dao = TarotCardDAO(session)
        card_count = await dao.count()

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
    session_maker: async_sessionmaker,
) -> None:
    topic = callback.data.split(":")[1]  # love | career | money | psy | question
    await callback.answer()

    if topic == "question":
        await state.set_state(SpreadStates.typing_question)
        await callback.message.edit_text(
            "❓ <b>Введите ваш вопрос:</b>\n\n"
            "<i>Чем конкретнее вопрос — тем точнее психологический анализ.</i>"
        )
        return

    # Сохраняем тему и запускаем расклад
    await state.update_data(topic=topic, question=None)
    await callback.message.edit_text(
        f"Тема: <b>{TOPIC_NAMES.get(topic, topic)}</b>"
    )
    await _run_spread(callback.message, state, session_maker)


# ─────────────── Ввод вопроса ───────────────

@router.message(SpreadStates.typing_question, F.text)
async def process_question(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker,
) -> None:
    question = message.text.strip()
    if len(question) < 5:
        await message.answer("⚠️ Вопрос слишком короткий. Попробуйте ещё раз:")
        return

    await state.update_data(topic="question", question=question)
    await _run_spread(message, state, session_maker)


# ─────────────── Основная логика расклада ───────────────

async def _run_spread(
    message: Message,
    state: FSMContext,
    session_maker: async_sessionmaker,
) -> None:
    data = await state.get_data()
    topic: str = data["topic"]
    question: str | None = data.get("question")
    
    # Устанавливаем блокирующее состояние СРАЗУ ЖЕ, чтобы игнорировать двойные клики
    await state.set_state(SpreadStates.generating_spread)

    telegram_id = message.from_user.id

    # Запускаем получение пользователя и выбор карт одновременно
    # Важно: для параллельных запросов нужны РАЗНЫЕ сессии
    async def get_cards_and_user():
        async def fetch_cards():
            async with session_maker() as session:
                return await TarotCardDAO(session).get_random_cards(3)
                
        async def fetch_user():
            async with session_maker() as session:
                return await UserDAO(session).get_by_telegram_id(telegram_id)
                
        cards_task = asyncio.create_task(fetch_cards())
        user_task = asyncio.create_task(fetch_user())
        
        cards = await cards_task
        user = await user_task
        return cards, user
            
    cards, user = await get_cards_and_user()

    if len(cards) < 3:
        await message.answer("⚠️ Не удалось вытянуть карты. Попробуйте позже.")
        await state.clear()
        return

    is_pro = user and user.subscription_status == "pro"

    # Отправляем статус — тянем карты
    status_msg = await message.answer("⏳ <b>Карты тянутся...</b>")

    # Сразу запускаем запрос к AI (параллельно отправке картинок), чтобы сэкономить время
    card_names = [card.name for card in cards]
    ai_task = asyncio.create_task(
        get_spread_interpretation(
            card_names=card_names,
            topic=topic,
            question=question,
            is_pro=is_pro,
        )
    )

    # Отправляем фото почти мгновенно без жестких задержек
    for i, card in enumerate(cards):

        caption = f"🃏 <b>{card.name}</b>"

        if card.photo:
            try:
                # Если это локальный путь (не кэшированный), то шлем FSInputFile
                if card.photo.startswith("Tarot_cards/"):
                    if os.path.exists(card.photo):
                        photo_obj = FSInputFile(card.photo)
                        sent_msg = await message.answer_photo(photo=photo_obj, caption=caption)
                        # Кэшируем file_id в базу 
                        if sent_msg.photo:
                            file_id = sent_msg.photo[-1].file_id
                            async with session_maker() as session:
                                dao_update = TarotCardDAO(session)
                                await dao_update.update_photo(card.id, file_id)
                                await session.commit()
                    else:
                        await message.answer(caption)
                else:
                    # Иначе отправляем по уже закешированному file_id (мгновенно)
                    await message.answer_photo(photo=card.photo, caption=caption)
            except Exception as e:
                logger.error(f"Failed to send photo {card.photo} for id {card.id}: {e}")
                await message.answer(caption)
        else:
            await message.answer(caption)

    # Сообщение об анализе
    try:
        await status_msg.delete()
    except Exception:
        pass
        
    analyzing_msg = await message.answer("🔮 <b>Завершаю анализ расклада...</b>")

    # Ждём завершения AI-запроса (который начался ещё до отправки фото)
    interpretation = await ai_task

    try:
        await analyzing_msg.delete()
    except Exception:
        pass
    
    # Отправляем ответ без ParseMode (чтобы избежать ошибки при символах < >)
    await message.answer(interpretation, parse_mode=None)
    
    # Снимаем блокировку FSM
    await state.clear()

    # ─── Подсчёт статистики и обновление БД ───
    stress_index = sum(c.stress_weight for c in cards) / len(cards)

    # Определяем доминирующую сферу по теме расклада
    if topic in AREA_KEYS:
        dominant_area = topic
    else:
        # Для конкретного вопроса — считаем по весам карт
        area_scores = {
            "love": sum(c.love_weight for c in cards),
            "career": sum(c.career_weight for c in cards),
            "money": sum(c.money_weight for c in cards),
            "psy": sum(c.psy_weight for c in cards),
        }
        dominant_area = max(area_scores, key=area_scores.get)

    area_labels = {
        "love": "Любовь",
        "career": "Карьера",
        "money": "Деньги",
        "psy": "Психика",
    }

    async with session_maker() as session:
        user_dao = UserDAO(session)
        await user_dao.update_spread_stats(
            telegram_id=telegram_id,
            stress_index=round(stress_index, 2),
            dominant_area=area_labels.get(dominant_area, dominant_area),
        )

    logger.info(
        "Spread done for user %s | cards: %s | stress: %.2f | area: %s",
        telegram_id, card_names, stress_index, dominant_area,
    )
