from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🃏 Сделать расклад")],
            [KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="⭐ PRO")],
            [KeyboardButton(text="📖 О методе")],
        ],
        resize_keyboard=True,
    )
