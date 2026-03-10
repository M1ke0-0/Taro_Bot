from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_menu(is_pro: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="🃏 Сделать расклад")],
        [KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="⭐ PRO")],
        [KeyboardButton(text="📖 О методе"), KeyboardButton(text="💡 Предложить улучшение")],
    ]
    if is_pro:
        keyboard.insert(1, [KeyboardButton(text="📊 Недельный отчет")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
    )

def get_return_to_main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔙 Возврат в меню")]
        ],
        resize_keyboard=True,
    )
