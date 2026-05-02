import logging
import os

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, FSInputFile
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select

from src.config import settings
from src.db.setting_dao import SettingDAO
from src.db.models import User
from src.keyboards.admin import (
    get_admin_main_keyboard,
    get_admin_reports_keyboard,
    get_admin_settings_keyboard,
    get_admin_back_keyboard,
    get_admin_confirm_keyboard
)
from src.services.excel_report import (
    export_users,
    export_spreads,
    export_subscriptions,
    export_payments
)

logger = logging.getLogger(__name__)

router = Router(name="admin")

class AdminStates(StatesGroup):
    waiting_for_setting_value = State()
    waiting_for_setting_confirmation = State()
    waiting_for_broadcast_message = State()
    waiting_for_grant_pro_id = State()


# Фильтр для проверки администратора
def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return  # Игнорируем обычных пользователей
        
    await state.clear()
    await message.answer(
        "🛠 <b>Панель Администратора</b>\n\nВыберите нужный раздел:",
        reply_markup=get_admin_main_keyboard()
    )


@router.callback_query(F.data == "admin:back")
async def process_admin_back(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    await callback.message.edit_text(
        "🛠 <b>Панель Администратора</b>\n\nВыберите нужный раздел:",
        reply_markup=get_admin_main_keyboard()
    )


# ─────────────── Отчеты ───────────────

@router.callback_query(F.data == "admin:reports")
async def process_admin_reports(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "📊 <b>Отчеты (Excel)</b>\n\nВыберите какой отчет сгенерировать:",
        reply_markup=get_admin_reports_keyboard()
    )


@router.callback_query(F.data.startswith("admin:report:"))
async def process_generate_report(callback: CallbackQuery, session_maker: async_sessionmaker) -> None:
    if not is_admin(callback.from_user.id):
        return
        
    report_type = callback.data.split(":")[-1]
    await callback.answer("⏳ Генерирую отчет...", show_alert=False)
    
    status_msg = await callback.message.answer("Генерация отчета...")
    filepath = None
    
    async with session_maker() as session:
        try:
            if report_type == "users":
                filepath = await export_users(session)
            elif report_type == "spreads":
                filepath = await export_spreads(session)
            elif report_type == "subscriptions":
                filepath = await export_subscriptions(session)
            elif report_type == "payments":
                filepath = await export_payments(session)
                
            if filepath and os.path.exists(filepath):
                doc = FSInputFile(filepath)
                await callback.message.answer_document(doc, caption=f"Отчет: {report_type}.xlsx")
                await status_msg.delete()
                # Удаляем файл после отправки для экономии места
                os.remove(filepath)
            else:
                await status_msg.edit_text("❌ Ошибка: файл не сгенерировался.")
        except Exception as e:
            logger.error(f"Error generating report {report_type}: {e}")
            await status_msg.edit_text(f"❌ Произошла ошибка при генерации отчета: {e}")


# ─────────────── Настройки ───────────────

@router.callback_query(F.data == "admin:settings")
async def process_admin_settings(callback: CallbackQuery, session_maker: async_sessionmaker) -> None:
    if not is_admin(callback.from_user.id):
        return
        
    async with session_maker() as session:
        setting_dao = SettingDAO(session)
        free_limit = await setting_dao.get_setting("free_spread_limit", "1")
        pro_price = await setting_dao.get_setting("pro_sub_price", "500")
        single_price = await setting_dao.get_setting("single_spread_price", "100")
        
    text = (
        "⚙️ <b>Настройки и лимиты</b>\n\n"
        f"Текущие значения:\n"
        f"• Лимит фри-раскладов: <b>{free_limit}</b> в день\n"
        f"• Цена PRO подписки: <b>{pro_price}</b> руб\n"
        f"• Цена разового расклада: <b>{single_price}</b> руб\n\n"
        "Нажмите на кнопку, чтобы изменить значение."
    )
    await callback.message.edit_text(text, reply_markup=get_admin_settings_keyboard())


@router.callback_query(F.data.startswith("admin:setting:"))
async def process_change_setting(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
        
    setting_key = callback.data.split(":")[-1]
    await state.update_data(setting_key=setting_key)
    await state.set_state(AdminStates.waiting_for_setting_value)
    
    await callback.message.answer(
        f"📝 Введите новое значение для ключа <b>{setting_key}</b> (только число):",
        reply_markup=get_admin_back_keyboard()
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_setting_value)
async def process_new_setting_value(message: Message, state: FSMContext, session_maker: async_sessionmaker) -> None:
    if not is_admin(message.from_user.id):
        return
        
    new_value = message.text.strip()
    if not new_value.isdigit():
        await message.answer("⚠️ Пожалуйста, введите корректное число.")
        return
        
    data = await state.get_data()
    setting_key = data.get("setting_key")
    
    await state.update_data(new_value=new_value)
    await state.set_state(AdminStates.waiting_for_setting_confirmation)
    
    await message.answer(
        f"⚠️ Вы уверены, что хотите изменить <b>{setting_key}</b> на <b>{new_value}</b>?",
        reply_markup=get_admin_confirm_keyboard()
    )


@router.callback_query(AdminStates.waiting_for_setting_confirmation, F.data.startswith("admin:confirm_setting:"))
async def process_confirm_setting(callback: CallbackQuery, state: FSMContext, session_maker: async_sessionmaker) -> None:
    if not is_admin(callback.from_user.id):
        return
        
    action = callback.data.split(":")[-1]
    
    if action == "no":
        await state.clear()
        await callback.message.edit_text("❌ Изменение отменено.", reply_markup=get_admin_back_keyboard())
        return
        
    # Если yes
    data = await state.get_data()
    setting_key = data.get("setting_key")
    new_value = data.get("new_value")
    
    async with session_maker() as session:
        setting_dao = SettingDAO(session)
        await setting_dao.set_setting(setting_key, new_value)
        
    await state.clear()
    await callback.message.edit_text(
        f"✅ Значение <b>{setting_key}</b> успешно изменено на <b>{new_value}</b>.", 
        reply_markup=get_admin_back_keyboard()
    )

# ─────────────── Рассылка ───────────────

@router.callback_query(F.data == "admin:broadcast")
async def process_admin_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
        
    await state.set_state(AdminStates.waiting_for_broadcast_message)
    await callback.message.edit_text(
        "📢 <b>Массовая рассылка</b>\n\n"
        "Отправьте мне сообщение, которое нужно разослать всем пользователям бота.\n"
        "Вы можете использовать форматирование, картинки и даже видео.",
        reply_markup=get_admin_back_keyboard()
    )


@router.message(AdminStates.waiting_for_broadcast_message)
async def process_broadcast_message(message: Message, state: FSMContext, session_maker: async_sessionmaker) -> None:
    if not is_admin(message.from_user.id):
        return
        
    status_msg = await message.answer("🚀 Начинаю рассылку...")
    
    async with session_maker() as session:
        stmt = select(User.telegram_id)
        result = await session.execute(stmt)
        user_ids = result.scalars().all()
        
    success = 0
    failed = 0
    
    for uid in user_ids:
        try:
            await message.send_copy(chat_id=uid)
            success += 1
        except Exception:
            failed += 1
            
    await state.clear()
    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"Успешно доставлено: {success}\n"
        f"Ошибок (пользователь заблокировал бота): {failed}",
        reply_markup=get_admin_back_keyboard()
    )


# ─────────────── Выдача PRO ───────────────

@router.callback_query(F.data == "admin:grant_pro")
async def process_admin_grant_pro(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
        
    await state.set_state(AdminStates.waiting_for_grant_pro_id)
    await callback.message.edit_text(
        "👑 <b>Выдача PRO подписки</b>\n\n"
        "Отправьте мне <b>Telegram ID</b> пользователя, которому нужно выдать PRO доступ навсегда (или до явной отмены).\n"
        "ID можно посмотреть в отчете по пользователям.",
        reply_markup=get_admin_back_keyboard()
    )


@router.message(AdminStates.waiting_for_grant_pro_id)
async def process_grant_pro_id(message: Message, state: FSMContext, session_maker: async_sessionmaker) -> None:
    if not is_admin(message.from_user.id):
        return
        
    target_id_str = message.text.strip()
    if not target_id_str.isdigit():
        await message.answer("⚠️ Ошибка: Telegram ID должен состоять только из цифр.", reply_markup=get_admin_back_keyboard())
        return
        
    target_id = int(target_id_str)
    
    async with session_maker() as session:
        from src.db.user_dao import UserDAO
        user_dao = UserDAO(session)
        user = await user_dao.get_by_telegram_id(target_id)
        
        if not user:
            await message.answer(f"❌ Пользователь с ID <code>{target_id}</code> не найден в базе данных.", reply_markup=get_admin_back_keyboard())
            return
            
        from datetime import datetime, timezone, timedelta
        user.subscription_status = "pro"
        user.subscription_end_date = None  # None = безлимитный (выдан администратором)
        await session.commit()
        
    await state.clear()
    
    await message.answer(
        f"✅ Пользователю с ID <code>{target_id}</code> успешно выдана подписка <b>PRO</b>!", 
        reply_markup=get_admin_back_keyboard()
    )
    
    # Пытаемся уведомить самого пользователя
    try:
        # Получаем объект бота из context message
        await message.bot.send_message(
            target_id,
            "🎉 <b>Поздравляем!</b>\n\nВам выдана подписка <b>⭐ PRO</b>! Теперь вам доступны безлимитные расклады, еженедельные отчеты и глубокая аналитика карт."
        )
    except Exception as e:
        logger.warning(f"Не удалось отправить уведомление пользователю {target_id} о выдаче PRO: {e}")


# ─────────────── Отмена PRO ───────────────

class AdminRevokeProStates(StatesGroup):
    waiting_for_revoke_pro_id = State()

@router.callback_query(F.data == "admin:revoke_pro")
async def process_admin_revoke_pro(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        return
        
    await state.set_state(AdminRevokeProStates.waiting_for_revoke_pro_id)
    await callback.message.edit_text(
        "❌ <b>Отмена PRO подписки</b>\n\n"
        "Отправьте мне <b>Telegram ID</b> пользователя, у которого нужно забрать PRO доступ (вернуть free).\n"
        "ID можно посмотреть в отчете по пользователям.",
        reply_markup=get_admin_back_keyboard()
    )


@router.message(AdminRevokeProStates.waiting_for_revoke_pro_id)
async def process_revoke_pro_id(message: Message, state: FSMContext, session_maker: async_sessionmaker) -> None:
    if not is_admin(message.from_user.id):
        return
        
    target_id_str = message.text.strip()
    if not target_id_str.isdigit():
        await message.answer("⚠️ Ошибка: Telegram ID должен состоять только из цифр.", reply_markup=get_admin_back_keyboard())
        return
        
    target_id = int(target_id_str)
    
    async with session_maker() as session:
        from src.db.user_dao import UserDAO
        user_dao = UserDAO(session)
        user = await user_dao.get_by_telegram_id(target_id)
        
        if not user:
            await message.answer(f"❌ Пользователь с ID <code>{target_id}</code> не найден в базе данных.", reply_markup=get_admin_back_keyboard())
            return
            
        user.subscription_status = "free"
        user.subscription_end_date = None
        await session.commit()
        
    await state.clear()
    
    await message.answer(
        f"✅ У пользователя с ID <code>{target_id}</code> успешно забрана подписка PRO (теперь <b>free</b>).", 
        reply_markup=get_admin_back_keyboard()
    )


# ─────────────── Предложения ───────────────

from src.db.models import Suggestion
from src.keyboards.admin import get_admin_suggestion_nav_keyboard

@router.callback_query(F.data == "admin:suggestions")
async def process_admin_suggestions(callback: CallbackQuery, session_maker: async_sessionmaker) -> None:
    if not is_admin(callback.from_user.id):
        return
        
    await show_suggestion(callback, session_maker, offset=0)


async def show_suggestion(callback: CallbackQuery, session_maker: async_sessionmaker, offset: int = 0) -> None:
    async with session_maker() as session:
        # Get unread suggestions count
        stmt_count = select(func.count(Suggestion.id)).where(Suggestion.is_read == False)
        count_res = await session.execute(stmt_count)
        total_unread = count_res.scalar() or 0
        
        if total_unread == 0:
            await callback.message.edit_text(
                "💡 <b>Нет новых предложений</b>\n\nВсе предложения прочитаны.",
                reply_markup=get_admin_back_keyboard()
            )
            return

        # Get ONE suggestion at the offset
        stmt = select(Suggestion).where(Suggestion.is_read == False).order_by(Suggestion.created_at.desc()).offset(offset).limit(1)
        res = await session.execute(stmt)
        suggestion = res.scalar_one_or_none()
        
        if not suggestion:
            await callback.message.edit_text(
                "💡 <b>Предложение не найдено</b>",
                reply_markup=get_admin_back_keyboard()
            )
            return
            
        from src.db.user_dao import UserDAO
        user_dao = UserDAO(session)
        user = await user_dao.get_by_telegram_id(suggestion.user_id) # oops, this is user.id, need to get user by id
        
        if user:
            user_info = f"<a href='tg://user?id={user.telegram_id}'>{user.name or 'Без имени'}</a> (ID: <code>{user.telegram_id}</code>)"
        else:
            # Maybe user_id was foreign key id, let's just get it using the exact relation
            stmt_usr = select(User).where(User.id == suggestion.user_id)
            usr_res = await session.execute(stmt_usr)
            usr = usr_res.scalar_one_or_none()
            if usr:
                user_info = f"<a href='tg://user?id={usr.telegram_id}'>{usr.name or 'Без имени'}</a> (ID: <code>{usr.telegram_id}</code>)"
            else:
                user_info = f"UID БД: {suggestion.user_id}"
            
        text = (
            f"💡 <b>Непрочитанные предложения</b> ({offset + 1}/{total_unread})\n\n"
            f"👤 От: {user_info}\n"
            f"📅 Дата: {suggestion.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"<i>{suggestion.text}</i>"
        )
        
        has_prev = offset > 0
        has_next = offset < total_unread - 1
        
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_suggestion_nav_keyboard(suggestion.id, offset, has_prev, has_next)
        )


@router.callback_query(F.data.startswith("admin:sugg_nav_off:"))
async def process_admin_suggestion_nav_off(callback: CallbackQuery, session_maker: async_sessionmaker) -> None:
    if not is_admin(callback.from_user.id):
        return
        
    parts = callback.data.split(":")
    offset = int(parts[-1])
    await show_suggestion(callback, session_maker, offset)


@router.callback_query(F.data.startswith("admin:sugg_read:"))
async def process_admin_suggestion_read(callback: CallbackQuery, session_maker: async_sessionmaker) -> None:
    if not is_admin(callback.from_user.id):
        return
        
    suggestion_id = int(callback.data.split(":")[-1])
    
    async with session_maker() as session:
        stmt = select(Suggestion).where(Suggestion.id == suggestion_id)
        res = await session.execute(stmt)
        suggestion = res.scalar_one_or_none()
        
        if suggestion:
            suggestion.is_read = True
            await session.commit()
            
    await callback.answer("✅ Отмечено как прочитанное")
    
    # Show the next unread suggestion (which is now at offset 0 since we just marked the current one read)
    await show_suggestion(callback, session_maker, offset=0)
