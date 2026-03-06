from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_topic_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❤️ Любовь", callback_data="spread:love"),
                InlineKeyboardButton(text="💼 Карьера", callback_data="spread:career"),
            ],
            [
                InlineKeyboardButton(text="💰 Деньги", callback_data="spread:money"),
                InlineKeyboardButton(text="🧠 Состояние/Психика", callback_data="spread:psy"),
            ],
            [
                InlineKeyboardButton(text="❓ Конкретный вопрос", callback_data="spread:question"),
            ],
        ]
    )
