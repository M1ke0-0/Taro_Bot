import logging
from aiogram import F, Router
from aiogram.types import PreCheckoutQuery, Message, BufferedInputFile
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.db.payment_dao import PaymentDAO
from src.db.user_dao import UserDAO
from src.keyboards.main_menu import get_main_menu
from src.services.receipt import generate_receipt
from src.config import settings

logger = logging.getLogger(__name__)

router = Router(name="payments")


async def _send_receipt(message: Message, payment: object, user_name: str, amount: float, currency: str):
    try:
        pdf_bytes = generate_receipt(
            payment_id=payment.id,
            user_name=user_name,
            amount=amount,
            currency=currency,
            payment_type=payment.payment_type,
            created_at=payment.created_at,
        )
        await message.answer_document(
            BufferedInputFile(pdf_bytes, filename=f"receipt_{payment.id:06d}.pdf"),
            caption="📄 Ваша квитанция об оплате",
        )
    except Exception as e:
        logger.error(f"Failed to generate receipt: {e}")


@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message, session_maker: async_sessionmaker):
    payment_info = message.successful_payment
    payload = payment_info.invoice_payload
    telegram_id = message.from_user.id
    currency = payment_info.currency

    amount = payment_info.total_amount
    if currency != "XTR":
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
            await user_dao.set_pro_status(telegram_id)
            payment = await payment_dao.add_payment(user.id, amount, "pro_sub", "success")

            await message.answer(
                "🎉 <b>Оплата прошла успешно!</b>\n\n"
                "Подписка <b>PRO</b> активирована! Теперь вам доступны все премиум-функции бота.",
                reply_markup=get_main_menu(is_pro=True)
            )
            await _send_receipt(message, payment, user.name or str(telegram_id), amount, currency)
            logger.info(f"User {telegram_id} bought PRO subscription.")

        elif payload == "single_spread":
            payment = await payment_dao.add_payment(user.id, amount, "single_spread", "success")

            await message.answer(
                "✅ <b>Оплата прошла успешно!</b>\n\n"
                "Ваш глубокий разбор сейчас будет сгенерирован (в разработке).",
            )
            await _send_receipt(message, payment, user.name or str(telegram_id), amount, currency)
            logger.info(f"User {telegram_id} bought single spread deep dive.")

        else:
            await message.answer("✅ Оплата получена, но назначение платежа неизвестно.")
            logger.warning(f"Unknown payment payload '{payload}' from user {telegram_id}")
