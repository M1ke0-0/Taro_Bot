from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def get_pro_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 Оплатить подписку", callback_data="pro:buy"
                )
            ]
        ]
    )
