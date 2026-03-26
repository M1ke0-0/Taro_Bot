import logging
from aiogram import F, Router
from aiogram.types import PreCheckoutQuery, Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.db.payment_dao import PaymentDAO
from src.db.user_dao import UserDAO
from src.keyboards.main_menu import get_main_menu

logger = logging.getLogger(__name__)

router = Router(name="payments")

@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    """
    Подтверждаем готовность к оплате. Обязательный шаг для Telegram-платежей.
    """
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment_handler(message: Message, session_maker: async_sessionmaker):
    """
    Обработка успешной оплаты.
    """
    payment_info = message.successful_payment
    payload = payment_info.invoice_payload
    telegram_id = message.from_user.id
    
    # Сумма приходит в минимальных единицах валюты (например, копейки или центы).
    # Для Telegram Stars (XTR) сумма обычно равна кол-ву звезд.
    # Если фиат, то делим на 100 для получения нормальной суммы.
    amount = payment_info.total_amount
    if payment_info.currency != "XTR":
        amount = amount / 100.0

    async with session_maker() as session:
        user_dao = UserDAO(session)
        user = await user_dao.get_by_telegram_id(telegram_id)
        if not user:
            user = await user_dao.create(
                telegram_id=telegram_id,
                name=message.from_user.first_name,
                username=message.from_user.username,
            )
            
        payment_dao = PaymentDAO(session)
        
        if payload == "pro_sub":
            # Выдача PRO
            await user_dao.set_pro_status(telegram_id)
            await payment_dao.add_payment(user.id, amount, "pro_sub", "success")
            
            await message.answer(
                "🎉 <b>Оплата прошла успешно!</b>\n\n"
                "Подписка <b>PRO</b> активирована! Теперь вам доступны все премиум-функции бота.",
                reply_markup=get_main_menu(is_pro=True)
            )
            logger.info(f"User {telegram_id} bought PRO subscription.")
            
        elif payload == "single_spread":
            # Выдача разового глубокого разбора
            await payment_dao.add_payment(user.id, amount, "single_spread", "success")
            
            await message.answer(
                "✅ <b>Оплата прошла успешно!</b>\n\n"
                "Ваш глубокий разбор сейчас будет сгенерирован (в разработке).",
            )
            logger.info(f"User {telegram_id} bought single spread deep dive.")
            
        else:
            await message.answer("✅ Оплата получена, но назначение платежа неизвестно.")
            logger.warning(f"Unknown payment payload '{payload}' from user {telegram_id}")
