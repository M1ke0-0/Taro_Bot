import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.config import settings
from src.db.models import Base, TarotCard

# All 78 cards with basic psychological values and photo paths
CARDS_DATA = [
    # Major Arcana
    {"name": "Шут", "photo": "Tarot_cards/Tarot_00_Fool.jpg", "love_weight": 1.0, "career_weight": 2.0, "money_weight": 1.0, "psy_weight": 3.0},
    {"name": "Маг", "photo": "Tarot_cards/Tarot_01_Magician.jpg", "love_weight": 1.0, "career_weight": 3.0, "money_weight": 2.0, "psy_weight": 2.0},
    {"name": "Жрица", "photo": "Tarot_cards/Tarot_02_High_Priestess.jpg", "love_weight": 2.0, "career_weight": 1.0, "money_weight": 0.0, "psy_weight": 3.0},
    {"name": "Императрица", "photo": "Tarot_cards/Tarot_03_Empress.jpg", "love_weight": 3.0, "career_weight": 1.0, "money_weight": 2.0, "psy_weight": 2.0},
    {"name": "Император", "photo": "Tarot_cards/Tarot_04_Emperor.jpg", "love_weight": 1.0, "career_weight": 3.0, "money_weight": 3.0, "psy_weight": 2.0},
    {"name": "Иерофант", "photo": "Tarot_cards/Tarot_05_Hierophant.jpg", "love_weight": 2.0, "career_weight": 2.0, "money_weight": 1.0, "psy_weight": 2.0},
    {"name": "Влюбленные", "photo": "Tarot_cards/Tarot_06_Lovers.jpg", "love_weight": 3.0, "career_weight": 1.0, "money_weight": 1.0, "psy_weight": 2.0},
    {"name": "Колесница", "photo": "Tarot_cards/Tarot_07_Chariot.jpg", "love_weight": 1.0, "career_weight": 3.0, "money_weight": 2.0, "psy_weight": 2.0},
    {"name": "Сила", "photo": "Tarot_cards/Tarot_08_Strength.jpg", "love_weight": 2.0, "career_weight": 2.0, "money_weight": 1.0, "psy_weight": 3.0},
    {"name": "Отшельник", "photo": "Tarot_cards/Tarot_09_Hermit.jpg", "love_weight": 1.0, "career_weight": 1.0, "money_weight": 0.0, "psy_weight": 3.0},
    {"name": "Колесо Фортуны", "photo": "Tarot_cards/Tarot_10_Wheel_of_Fortune.jpg", "love_weight": 1.0, "career_weight": 2.0, "money_weight": 2.0, "psy_weight": 2.0},
    {"name": "Справедливость", "photo": "Tarot_cards/Tarot_11_Justice.jpg", "love_weight": 2.0, "career_weight": 2.0, "money_weight": 2.0, "psy_weight": 2.0},
    {"name": "Повешенный", "photo": "Tarot_cards/Tarot_12_Hanged_Man.jpg", "love_weight": 1.0, "career_weight": 1.0, "money_weight": 1.0, "psy_weight": 3.0},
    {"name": "Смерть", "photo": "Tarot_cards/Tarot_13_Death.jpg", "love_weight": 2.0, "career_weight": 2.0, "money_weight": 2.0, "psy_weight": 3.0},
    {"name": "Умеренность", "photo": "Tarot_cards/Tarot_14_Temperance.jpg", "love_weight": 2.0, "career_weight": 1.0, "money_weight": 1.0, "psy_weight": 3.0},
    {"name": "Дьявол", "photo": "Tarot_cards/Tarot_15_Devil.jpg", "love_weight": 2.0, "career_weight": 2.0, "money_weight": 3.0, "psy_weight": 3.0},
    {"name": "Башня", "photo": "Tarot_cards/Tarot_16_Tower.jpg", "love_weight": 1.0, "career_weight": 2.0, "money_weight": 2.0, "psy_weight": 3.0},
    {"name": "Звезда", "photo": "Tarot_cards/Tarot_17_Star.jpg", "love_weight": 2.0, "career_weight": 1.0, "money_weight": 1.0, "psy_weight": 3.0},
    {"name": "Луна", "photo": "Tarot_cards/Tarot_18_Moon.jpg", "love_weight": 2.0, "career_weight": 1.0, "money_weight": 1.0, "psy_weight": 3.0},
    {"name": "Солнце", "photo": "Tarot_cards/Tarot_19_Sun.jpg", "love_weight": 3.0, "career_weight": 2.0, "money_weight": 2.0, "psy_weight": 2.0},
    {"name": "Суд", "photo": "Tarot_cards/Tarot_20_Judgement.jpg", "love_weight": 1.0, "career_weight": 2.0, "money_weight": 1.0, "psy_weight": 3.0},
    {"name": "Мир", "photo": "Tarot_cards/Tarot_21_World.jpg", "love_weight": 2.0, "career_weight": 2.0, "money_weight": 2.0, "psy_weight": 2.0},
    
    # Wands (Жезлы)
    {"name": "Туз Жезлов", "photo": "Tarot_cards/Wands01.jpg", "psy_weight": 0.4},
    {"name": "Двойка Жезлов", "photo": "Tarot_cards/Wands02.jpg", "psy_weight": 0.5},
    {"name": "Тройка Жезлов", "photo": "Tarot_cards/Wands03.jpg", "psy_weight": 0.4},
    {"name": "Четверка Жезлов", "photo": "Tarot_cards/Wands04.jpg", "psy_weight": 0.3},
    {"name": "Пятерка Жезлов", "photo": "Tarot_cards/Wands05.jpg", "psy_weight": 0.6},
    {"name": "Шестерка Жезлов", "photo": "Tarot_cards/Wands06.jpg", "psy_weight": 0.4},
    {"name": "Семерка Жезлов", "photo": "Tarot_cards/Wands07.jpg", "psy_weight": 0.7},
    {"name": "Восьмерка Жезлов", "photo": "Tarot_cards/Wands08.jpg", "psy_weight": 0.5},
    {"name": "Девятка Жезлов", "photo": "Tarot_cards/Tarot_Nine_of_Wands.jpg", "psy_weight": 0.8},
    {"name": "Десятка Жезлов", "photo": "Tarot_cards/Wands10.jpg", "psy_weight": 0.9},
    {"name": "Паж Жезлов", "photo": "Tarot_cards/Wands11.jpg", "psy_weight": 0.5},
    {"name": "Рыцарь Жезлов", "photo": "Tarot_cards/Wands12.jpg", "psy_weight": 0.4},
    {"name": "Королева Жезлов", "photo": "Tarot_cards/Wands13.jpg", "psy_weight": 0.6},
    {"name": "Король Жезлов", "photo": "Tarot_cards/Wands14.jpg", "psy_weight": 0.5},

    # Cups (Кубки)
    {"name": "Туз Кубков", "photo": "Tarot_cards/Cups01.jpg", "psy_weight": 0.7},
    {"name": "Двойка Кубков", "photo": "Tarot_cards/Cups02.jpg", "psy_weight": 0.6},
    {"name": "Тройка Кубков", "photo": "Tarot_cards/Cups03.jpg", "psy_weight": 0.5},
    {"name": "Четверка Кубков", "photo": "Tarot_cards/Cups04.jpg", "psy_weight": 0.8},
    {"name": "Пятерка Кубков", "photo": "Tarot_cards/Cups05.jpg", "psy_weight": 0.9},
    {"name": "Шестерка Кубков", "photo": "Tarot_cards/Cups06.jpg.webp", "love_weight": 0.6, "career_weight": 0.25, "money_weight": 0.25, "psy_weight": 0.6},
    {"name": "Семерка Кубков", "photo": "Tarot_cards/Cups07.jpg.webp", "love_weight": 0.8, "career_weight": 0.25, "money_weight": 0.25, "psy_weight": 0.8},
    {"name": "Восьмерка Кубков", "photo": "Tarot_cards/Cups08.jpg", "love_weight": 0.9, "career_weight": 0.25, "money_weight": 0.25, "psy_weight": 0.9},
    {"name": "Девятка Кубков", "photo": "Tarot_cards/Cups09.jpg", "love_weight": 0.4, "career_weight": 0.25, "money_weight": 0.25, "psy_weight": 0.4},
    {"name": "Десятка Кубков", "photo": "Tarot_cards/Cups10.jpg", "love_weight": 0.3, "career_weight": 0.25, "money_weight": 0.25, "psy_weight": 0.3},
    {"name": "Паж Кубков", "photo": "Tarot_cards/Cups11.jpg.webp", "love_weight": 0.6, "career_weight": 0.25, "money_weight": 0.25, "psy_weight": 0.6},
    {"name": "Рыцарь Кубков", "photo": "Tarot_cards/Cups12.jpg.webp", "love_weight": 0.6, "career_weight": 0.25, "money_weight": 0.25, "psy_weight": 0.6},
    {"name": "Королева Кубков", "photo": "Tarot_cards/Cups13.jpg", "psy_weight": 0.8},
    {"name": "Король Кубков", "photo": "Tarot_cards/Cups14.jpg", "psy_weight": 0.7},

    # Swords (Мечи)
    {"name": "Туз Мечей", "photo": "Tarot_cards/Swords01.jpg", "psy_weight": 0.7},
    {"name": "Двойка Мечей", "photo": "Tarot_cards/Swords02.jpg", "psy_weight": 0.8},
    {"name": "Тройка Мечей", "photo": "Tarot_cards/Swords03.jpg", "psy_weight": 0.9},
    {"name": "Четверка Мечей", "photo": "Tarot_cards/Swords04.jpg.webp", "love_weight": 0.8, "career_weight": 0.25, "money_weight": 0.25, "psy_weight": 0.8},
    {"name": "Пятерка Мечей", "photo": "Tarot_cards/Swords05.jpg", "psy_weight": 0.8},
    {"name": "Шестерка Мечей", "photo": "Tarot_cards/Swords06.jpg", "psy_weight": 0.7},
    {"name": "Семерка Мечей", "photo": "Tarot_cards/Swords07.jpg", "psy_weight": 0.8},
    {"name": "Восьмерка Мечей", "photo": "Tarot_cards/Swords08.jpg", "psy_weight": 0.9},
    {"name": "Девятка Мечей", "photo": "Tarot_cards/Swords09.jpg", "psy_weight": 0.9},
    {"name": "Десятка Мечей", "photo": "Tarot_cards/Swords10.jpg", "psy_weight": 0.9},
    {"name": "Паж Мечей", "photo": "Tarot_cards/Swords11.jpg", "psy_weight": 0.6},
    {"name": "Рыцарь Мечей", "photo": "Tarot_cards/Swords12.jpg", "psy_weight": 0.6},
    {"name": "Королева Мечей", "photo": "Tarot_cards/Swords13.jpg", "psy_weight": 0.7},
    {"name": "Король Мечей", "photo": "Tarot_cards/Swords14.jpg", "psy_weight": 0.6},

    # Pentacles (Пентакли)
    {"name": "Туз Пентаклей", "photo": "Tarot_cards/Pents01.jpg", "psy_weight": 0.3},
    {"name": "Двойка Пентаклей", "photo": "Tarot_cards/Pents02.jpg", "psy_weight": 0.5},
    {"name": "Тройка Пентаклей", "photo": "Tarot_cards/Pents03.jpg", "psy_weight": 0.4},
    {"name": "Четверка Пентаклей", "photo": "Tarot_cards/Pents04.jpg.webp", "love_weight": 0.7, "career_weight": 0.25, "money_weight": 0.25, "psy_weight": 0.7},
    {"name": "Пятерка Пентаклей", "photo": "Tarot_cards/Pents05.jpg", "psy_weight": 0.8},
    {"name": "Шестерка Пентаклей", "photo": "Tarot_cards/Pents06.jpg", "psy_weight": 0.5},
    {"name": "Семерка Пентаклей", "photo": "Tarot_cards/Pents07.jpg", "psy_weight": 0.6},
    {"name": "Восьмерка Пентаклей", "photo": "Tarot_cards/Pents08.jpg", "psy_weight": 0.4},
    {"name": "Девятка Пентаклей", "photo": "Tarot_cards/Pents09.jpg", "psy_weight": 0.3},
    {"name": "Десятка Пентаклей", "photo": "Tarot_cards/Pents10.jpg", "psy_weight": 0.3},
    {"name": "Паж Пентаклей", "photo": "Tarot_cards/Pents11.jpg", "psy_weight": 0.4},
    {"name": "Рыцарь Пентаклей", "photo": "Tarot_cards/Pents12.jpg", "psy_weight": 0.4},
    {"name": "Королева Пентаклей", "photo": "Tarot_cards/Pents13.jpg", "psy_weight": 0.5},
    {"name": "Король Пентаклей", "photo": "Tarot_cards/Pents14.jpg", "psy_weight": 0.4},
]

async def seed():
    engine = create_async_engine(settings.database_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        # Очищаем старые карты
        await session.execute(delete(TarotCard))
        
        for card_data in CARDS_DATA:
            card = TarotCard(
                name=card_data["name"],
                photo=card_data["photo"],
                psy_weight=card_data.get("psy_weight", 0.5),
                resource="Ресурс: стандартное значение",
                shadow="Тень: стандартное значение",
                stress_weight=card_data.get("psy_weight", 0.5),
                activity_type="active",
                love_weight=card_data.get("love_weight", 0.25),
                career_weight=card_data.get("career_weight", 0.25),
                money_weight=card_data.get("money_weight", 0.25),
            )
            session.add(card)
        await session.commit()

    print(f"Очищена таблица и добавлено {len(CARDS_DATA)} карт.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed())
