from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_consent_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Согласен", callback_data="consent:accept"),
                InlineKeyboardButton(text="❌ Не согласен", callback_data="consent:decline"),
            ]
        ]
    )


