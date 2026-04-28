import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from aiogram import Bot
from aiogram.types import FSInputFile
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.config import settings
from src.db.models import TarotCard, User


async def main():
    print("Подключение к боту и базе данных...")
    bot_session = AiohttpSession(timeout=300.0)
    bot = Bot(token=settings.BOT_TOKEN, session=bot_session, default=DefaultBotProperties(parse_mode="HTML"))
    engine = create_async_engine(settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        # Пытаемся взять ADMIN_ID, если нет — берём первого пользователя из БД
        target_id = settings.ADMIN_IDS[0] if settings.ADMIN_IDS else None
        if not target_id:
            user = (await session.execute(select(User).limit(1))).scalar_one_or_none()
            if user:
                target_id = user.telegram_id
            else:
                print("ОШИБКА: Нет ни ADMIN_ID, ни одного пользователя в БД для кэширования!")
                return
        
        result = await session.execute(select(TarotCard))
        cards = result.scalars().all()
        
        print(f"Найдено {len(cards)} карт. Начинаю загрузку в Telegram...")
        
        for idx, card in enumerate(cards, start=1):
            if not card.photo or not os.path.exists(card.photo):
                # Если это не локальный путь (уже загружено) или файл пропал
                print(f"[{idx}/{len(cards)}] Пропуск {card.name}: файл {card.photo} не найден локально (возможно, уже загружен).")
                continue
                
            print(f"[{idx}/{len(cards)}] Загрузка фото для карты: {card.name}...")
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    photo_obj = FSInputFile(card.photo)
                    # Отправляем админу, чтобы получить file_id
                    msg = await bot.send_photo(
                        chat_id=target_id, 
                        photo=photo_obj, 
                        caption=f"Кэширование карты: {card.name}",
                        disable_notification=True
                    )
                    
                    # Получаем максимальный размер картинки
                    file_id = msg.photo[-1].file_id
                    
                    # Сохраняем file_id в базу вместо локального пути
                    card.photo = file_id
                    session.add(card)
                    await session.commit()
                    
                    print(f" -> Успех! file_id сохранён.")
                    
                    # Сразу удаляем сообщение, чтобы не засорять чат админу
                    try:
                        await msg.delete()
                    except Exception:
                        pass
                        
                    break
                except Exception as e:
                    print(f" -> Ошибка на попытке {attempt+1}: {e}")
                    await asyncio.sleep(5)  # Пауза перед новой попыткой при ошибке сети
            
            # Небольшая пауза между картами, чтобы не спамить API Telegram
            await asyncio.sleep(1)

    # Закрываем ресурсы
    await bot.session.close()
    await engine.dispose()
    print("Все фото успешно кэшированы на серверах Telegram!")

if __name__ == "__main__":
    asyncio.run(main())
