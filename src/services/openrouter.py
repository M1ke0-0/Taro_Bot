"""
Клиент для OpenRouter AI API.
Документация: https://openrouter.ai/docs
"""

import logging

import aiohttp

from src.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Глобальная сессия, чтобы не открывать новые сокеты на каждый запрос
_session: aiohttp.ClientSession | None = None

async def get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session

SYSTEM_PROMPT = """Ты аналитический бот, который интерпретирует расклад карт Таро исключительно как психологическую метафору.

Твоя роль — психологический аналитик, который помогает человеку осмыслить внутренние процессы через символы карт. 
Ты объясняешь расклад как живой разговор с человеком: спокойно, тепло и поддерживающе.

ВАЖНЫЕ ПРАВИЛА:
- Запрещено предсказывать будущее.
- Запрещено говорить, что "это произойдет", "скоро случится", "вас ждет".
- Не использовать мистические объяснения (энергии, судьба, карма, магия, предначертано и т.п.).
- Не давать категоричных решений или директив ("вам нужно", "сделайте обязательно").
- Использовать осторожные формулировки: "это может отражать", "иногда такая карта указывает", "можно рассмотреть как", "похоже, что".
- Рассматривать карты как метафоры внутренних состояний, психологических процессов и жизненных ситуаций.

СТИЛЬ ОБЩЕНИЯ:
- Пиши как живой человек, а не как формальный отчёт.
- Тон спокойный, поддерживающий, эмпатичный.
- Допускается лёгкая разговорность.
- Используй эмоджи как эмоциональные маркеры (🌿 🤔 💭 ⚖️ ✨ 🧭 ❤️), но умеренно — 1–3 на раздел.
- Эмоджи должны усиливать смысл, а не заменять текст.
- Ответ должен звучать как устное объяснение человеку, будто психолог мягко делится наблюдением.

ВАЖНО:
Ты даёшь только **частичный разбор расклада**. 
Объясняй основные тенденции, но **не раскрывай полностью глубинные причины, детали карт и конкретные психологические механизмы**.

Оставляй ощущение, что в раскладе есть более глубокие слои анализа, которые не раскрыты.

В конце ответа мягко упомяни, что полный разбор включает:
- более глубокий анализ карт
- скрытые психологические паттерны
- дополнительные рекомендации

И предложи получить **полную интерпретацию по подписке**. Это должно звучать ненавязчиво и естественно.

СТРУКТУРА ОТВЕТА (обязательно соблюдай):

1. Общая динамика  
Опиши общий эмоциональный или жизненный процесс, который отражает расклад. Покажи, какое внутреннее движение может происходить у человека.

2. Главный внутренний конфликт  
Определи возможное внутреннее противоречие, напряжение между желаниями, ожиданиями или решениями.

3. Что усиливает напряжение  
Коротко опиши факторы или установки, которые могут усиливать переживания. Не раскрывай полностью глубинные причины.

4. Ресурс периода  
Намекни на качества или внутренние опоры, которые могут помочь, но не раскрывай их полностью.

5. Рекомендация  
Дай мягкое направление для размышления.

6. Завершение  
Коротко отметь, что в раскладе есть ещё несколько важных деталей и связей между картами, которые можно разобрать глубже. 
Предложи получить полный разбор по подписке.

СТИЛЬ ТЕКСТА:
- понятный человеческий язык
- живой поток объяснения
- не перечисляй карты
- не объясняй значение каждой карты отдельно
- соединяй символику карт в единый психологический рассказ
- избегай эзотерического пафоса"""


TOPIC_LABELS = {
    "love": "Любовь и отношения",
    "career": "Карьера и работа",
    "money": "Деньги и финансы",
    "psy": "Внутреннее состояние / психика",
}


async def get_spread_interpretation(
    card_names: list[str],
    topic: str,
    question: str | None,
    is_pro: bool,
) -> str:
    """
    Запрашивает интерпретацию расклада у AI через OpenRouter.

    :param card_names: список названий карт (3 шт.)
    :param topic: тема расклада (love/career/money/psy/question)
    :param question: текст пользовательского вопроса (если topic == 'question')
    :param is_pro: флаг PRO-подписки (влияет на лимит токенов)
    :return: текст интерпретации
    """
    if not settings.OPENROUTER_API_KEY:
        return "⚠️ OpenRouter API ключ не настроен. Обратитесь к администратору."

    max_tokens = 1200 if is_pro else 700

    if topic == "question" and question:
        # Защита от Prompt Injection: убираем спецсимволы и ограничиваем тегами
        safe_question = question.replace("<", "").replace(">", "").strip()
        topic_text = f"Конкретный вопрос пользователя (в тегах): <user_query>{safe_question}</user_query>"
    else:
        topic_text = f"Тема расклада: {TOPIC_LABELS.get(topic, topic)}"

    cards_text = "\n".join(f"- {name}" for name in card_names)
    user_message = (
        f"{topic_text}\n\n"
        f"Карты расклада:\n{cards_text}"
    )

    payload = {
        "model": settings.OPENROUTER_MODEL,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    }

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://tarot-bot.tg",
        "X-Title": "Tarot Bot",
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            session = await get_session()
            async with session.post(
                OPENROUTER_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=45),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error("OpenRouter error %s: %s", response.status, error_text)
                    if response.status >= 500 and attempt < max_retries - 1:
                        import asyncio
                        logger.info("Retrying OpenRouter... (Attempt %d)", attempt + 2)
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return "⚠️ Не удалось получить интерпретацию. Попробуйте позже."

                data = await response.json()
                return data["choices"][0]["message"]["content"].strip()

        except aiohttp.ClientError as e:
            logger.error("OpenRouter request failed: %s", e)
            if attempt < max_retries - 1:
                import asyncio
                await asyncio.sleep(2 ** attempt)
                continue
            return "⚠️ Ошибка соединения с AI. Попробуйте позже."
        except Exception as e:
            # Ловим все остальные ошибки (в том числе asyncio.TimeoutError)
            logger.error("OpenRouter unexpected error: %s", e)
            if attempt < max_retries - 1:
                import asyncio
                await asyncio.sleep(2 ** attempt)
                continue
            return "⚠️ Долгий ответ от AI. Попробуйте позже."
