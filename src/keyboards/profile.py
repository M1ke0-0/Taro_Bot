from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_profile_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🃏 Новый расклад", callback_data="profile:new_spread")],
            [InlineKeyboardButton(text="⭐ Подключить PRO подписку", callback_data="profile:buy_pro")],
            [InlineKeyboardButton(text="◀️ Вернуться в меню", callback_data="profile:back")],
        ]
    )
