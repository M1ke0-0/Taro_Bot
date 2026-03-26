import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.config import settings
from src.db.models import TarotCard

async def check():
    engine = create_async_engine(settings.database_url, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        result = await session.execute(select(TarotCard))
        cards = result.scalars().all()
        
        uncached = []
        cached = []
        
        for card in cards:
            # Если photo начинается с Tarot_cards/ - значит это локальный путь, он НЕ кэширован
            if card.photo and card.photo.startswith("Tarot_cards/"):
                uncached.append(card)
            else:
                cached.append(card)
                
        print(f"Успешно кэшировано (имеют file_id): {len(cached)} карт из 78.")
        
        if uncached:
            print(f"НЕ кэшировано (остались локальные пути): {len(uncached)} карт.")
            print("Список некэшированных карт:")
            for c in uncached:
                print(f"  - {c.name} ({c.photo})")
        else:
            print(f"Все карты полностью загружены на сервера Telegram! Можно пользоваться ботом.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
