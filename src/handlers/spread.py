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
from src.db.spread_history_dao import SpreadHistoryDAO
from src.db.setting_dao import SettingDAO
from src.keyboards.spread import get_topic_keyboard, get_post_spread_keyboard
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
    session_maker: async_sessionmaker,
) -> None:
    topic = callback.data.split(":")[1]  # love | career | money | psy | question
    await callback.answer()

    await state.set_state(SpreadStates.typing_question)
    
    if topic == "question":
        # Свой вопрос (без конкретной темы)
        await state.update_data(topic=topic)
        await callback.message.edit_text(
            "❓ <b>Введите ваш вопрос:</b>\n\n"
            "<i>Чем конкретнее вопрос — тем точнее психологический анализ.</i>"
        )
    else:
        # Выбрана конкретная тема
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
    # Защита от race condition: сразу ставим статус
    await state.set_state(SpreadStates.generating_spread)
    
    question = message.text.strip()
    data = await state.get_data()
    topic = data.get("topic")

    # Если пользователь ввел короткий текст, но это не минус
    if len(question) < 5 and question != "-":
        await state.set_state(SpreadStates.typing_question)
        await message.answer("⚠️ Вопрос слишком короткий. Попробуйте ещё раз:")
        return
        
    # Если вопрос слишком длинный
    if len(question) > 500:
        await state.set_state(SpreadStates.typing_question)
        await message.answer("⚠️ Вопрос слишком длинный. Пожалуйста, сформулируйте его короче (до 500 символов).")
        return

    # Если отправлен минус, значит вопроса нет
    if question == "-":
        question = None

    await state.update_data(question=question)
    
    # Отправляем сообщение о начале, если тема не была "question" (там нет edit_text сверху)
    if topic == "question":
        await message.answer("🔮 Начинаем расклад...")
    else:
        # Чтобы убрать клавиатуру или дать фидбек
        await message.answer(f"🔮 Принято. Делаю расклад...")

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

    # Fetch single spread price
    async with session_maker() as session:
        setting_dao = SettingDAO(session)
        single_price = await setting_dao.get_setting("single_spread_price", "99")

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

    # Отправляем фото с задержкой 2 сек между картами для эффекта присутствия
    for i, card in enumerate(cards):
        if i > 0:
            await asyncio.sleep(2)

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
    
    # Разбиваем длинный текст на части (лимит Telegram 4096 символов)
    max_length = 4000
    paragraphs = interpretation.split('\n')
    current_chunk = ""
    chunks = []
    
    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) + 1 > max_length:
            chunks.append(current_chunk)
            current_chunk = paragraph
        else:
            if current_chunk:
                current_chunk += "\n" + paragraph
            else:
                current_chunk = paragraph
    
    if current_chunk:
        chunks.append(current_chunk)

    for i, chunk in enumerate(chunks):
        # Клавиатуру добавляем только к последнему сообщению
        reply_markup = get_post_spread_keyboard(is_pro=is_pro, price=single_price) if i == len(chunks) - 1 else None
        
        # Отправляем ответ без ParseMode (чтобы избежать ошибки при HTML тегах)
        await message.answer(
            chunk, 
            parse_mode=None, 
            reply_markup=reply_markup
        )
    
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
        user = await user_dao.get_by_telegram_id(telegram_id)
        
        await user_dao.update_spread_stats(
            telegram_id=telegram_id,
            stress_index=round(stress_index, 2),
            dominant_area=area_labels.get(dominant_area, dominant_area),
        )
        
        if user:
            history_dao = SpreadHistoryDAO(session)
            await history_dao.add_history(
                user_id=user.id,
                topic=area_labels.get(topic, topic),
                cards=", ".join([c.name for c in cards]),
                stress_index=round(stress_index, 2)
            )
            await session.commit()

    logger.info(
        "Spread done for user %s | cards: %s | stress: %.2f | area: %s",
        telegram_id, card_names, stress_index, dominant_area,
    )

# ─────────────── Дополнительные действия после расклада ───────────────

@router.callback_query(F.data == "spread:deep_dive")
async def process_deep_dive(callback: CallbackQuery) -> None:
    await callback.answer("🔄 Запускаю глубокий разбор...", show_alert=False)
    await callback.message.answer("Здесь будет функционал глубокого разбора для PRO 🔮 (в разработке)")

@router.callback_query(F.data == "spread:deep_dive_pay")
async def process_deep_dive_pay(callback: CallbackQuery, session_maker: async_sessionmaker) -> None:
    async with session_maker() as session:
        setting_dao = SettingDAO(session)
        price = await setting_dao.get_setting("single_spread_price", "99")
    await callback.answer(f"🚧 Оплатите {price} руб для разового глубокого разбора. (Интеграция оплаты в разработке).", show_alert=True)
