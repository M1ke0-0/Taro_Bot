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

def get_post_spread_keyboard(is_pro: bool, price: str = "99") -> InlineKeyboardMarkup | None:
    if is_pro:
        # Для PRO подписки дополнительных кнопок покупки нет
        return None
    else:
        # Для Free кнопки "Разобрать глубже"
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"🔍 Разобрать глубже (разово - {price} руб)", callback_data="spread:deep_dive_pay")]
            ]
        )
