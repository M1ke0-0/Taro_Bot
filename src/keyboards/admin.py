from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Отчеты (Excel)", callback_data="admin:reports"))
    builder.row(InlineKeyboardButton(text="⚙️ Настройки и лимиты", callback_data="admin:settings"))
    builder.row(InlineKeyboardButton(text="📢 Массовая рассылка", callback_data="admin:broadcast"))
    builder.row(InlineKeyboardButton(text="👑 Выдать PRO", callback_data="admin:grant_pro"))
    return builder.as_markup()

def get_admin_reports_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Пользователи", callback_data="admin:report:users"))
    builder.row(InlineKeyboardButton(text="Расклады", callback_data="admin:report:spreads"))
    builder.row(InlineKeyboardButton(text="Подписки", callback_data="admin:report:subscriptions"))
    builder.row(InlineKeyboardButton(text="Платежи", callback_data="admin:report:payments"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back"))
    return builder.as_markup()

def get_admin_settings_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Лимит фри-раскладов", callback_data="admin:setting:free_spread_limit"))
    builder.row(InlineKeyboardButton(text="Цена PRO подписки", callback_data="admin:setting:pro_sub_price"))
    builder.row(InlineKeyboardButton(text="Цена разового расклада", callback_data="admin:setting:single_spread_price"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back"))
    return builder.as_markup()

def get_admin_back_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ В админ-панель", callback_data="admin:back"))
    return builder.as_markup()

def get_admin_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да", callback_data="admin:confirm_setting:yes"),
        InlineKeyboardButton(text="❌ Нет", callback_data="admin:confirm_setting:no")
    )
    return builder.as_markup()
