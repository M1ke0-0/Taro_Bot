import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.db.base import create_session_maker
from src.db.models import Base


async def clear_db() -> None:
    session_maker = await create_session_maker()
    async with session_maker() as session:
        async with session.begin():
            for table in reversed(Base.metadata.sorted_tables):
                if table.name == "tarot_cards":
                    print(f"⏳ Пропуск таблицы {table.name} (кэшированные карты)")
                    continue
                await session.execute(table.delete())
    print("✅ Выбранные таблицы очищены.")


if __name__ == "__main__":
    confirm = input("⚠️  Удалить все данные из БД? (yes/no): ").strip().lower()
    if confirm == "yes":
        asyncio.run(clear_db())
    else:
        print("Отменено.")
