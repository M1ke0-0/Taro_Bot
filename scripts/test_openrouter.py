import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

import aiohttp
from src.config import settings


async def main():
    api_key = settings.OPENROUTER_API_KEY
    model = settings.OPENROUTER_MODEL

    print(f"API Key: {'Установлен' if api_key else 'ПУСТОЙ!'}")
    print(f"Model: {model}")

    if not api_key:
        print("ОШИБКА: API ключ не найден в .env")
        return

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Скажи 'Привет'"}],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    print("\nОтправляем тестовый запрос к OpenRouter...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=payload,
                headers=headers,
            ) as response:
                print(f"HTTP Status: {response.status}")
                text = await response.text()
                
                if response.status == 200:
                    print(f"УСПЕХ! Ответ AI: {text}")
                elif response.status == 401:
                    print(f"ОШИБКА 401: Неверный API ключ.\nПодробности: {text}")
                elif response.status == 404:
                    print(f"ОШИБКА 404: Модель '{model}' не найдена или недоступна.\nПодробности: {text}")
                elif response.status == 402:
                    print(f"ОШИБКА 402: Недостаточно средств или лимит исчерпан.\nПодробности: {text}")
                else:
                    print(f"ОШИБКА {response.status}: {text}")

    except Exception as e:
        print(f"ОШИБКА СОЕДИНЕНИЯ: {e}")


if __name__ == "__main__":
    asyncio.run(main())
