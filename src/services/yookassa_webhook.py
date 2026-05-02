import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

from aiohttp import web
from aiogram import Bot
from aiogram.types import BufferedInputFile
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.config import settings
from src.db.payment_dao import PaymentDAO
from src.db.user_dao import UserDAO
from src.keyboards.main_menu import get_main_menu
from src.services.receipt import generate_receipt

logger = logging.getLogger(__name__)


async def yookassa_webhook_handler(request: web.Request) -> web.Response:
    bot: Bot = request.app["bot"]
    session_maker: async_sessionmaker = request.app["session_maker"]

    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400)

    event_type = data.get("event")
    payment_obj = data.get("object", {})

    if event_type != "payment.succeeded":
        return web.Response(status=200)

    payment_id_yk = payment_obj.get("id")
    amount_value = float(payment_obj.get("amount", {}).get("value", 0))
    currency = payment_obj.get("amount", {}).get("currency", "RUB")
    payload = payment_obj.get("metadata", {}).get("payload", "")
    telegram_id_str = payment_obj.get("metadata", {}).get("telegram_id", "")

    if not telegram_id_str:
        logger.warning("YooKassa webhook: no telegram_id in metadata, payment %s", payment_id_yk)
        return web.Response(status=200)

    telegram_id = int(telegram_id_str)

    async with session_maker() as session:
        user_dao = UserDAO(session)
        payment_dao = PaymentDAO(session)

        user = await user_dao.get_by_telegram_id(telegram_id)
        if not user:
            logger.warning("YooKassa webhook: user %s not found", telegram_id)
            return web.Response(status=200)

        payment = None  # будет установлен в блоке if/elif ниже

        if payload == "pro_sub":
            await user_dao.set_pro_status(telegram_id)
            payment = await payment_dao.add_payment(user.id, amount_value, "pro_sub", "success")

            await bot.send_message(
                telegram_id,
                "🎉 <b>Оплата прошла успешно!</b>\n\n"
                "Подписка <b>PRO</b> активирована! Теперь вам доступны все премиум-функции бота.",
                reply_markup=get_main_menu(is_pro=True),
                parse_mode="HTML",
            )
            logger.info("User %s bought PRO via YooKassa", telegram_id)

        elif payload == "single_spread":
            payment = await payment_dao.add_payment(user.id, amount_value, "single_spread", "success")

            await bot.send_message(
                telegram_id,
                "✅ <b>Оплата прошла успешно!</b>\n\n"
                "Ваш глубокий разбор сейчас будет сгенерирован (в разработке).",
                parse_mode="HTML",
            )
            logger.info("User %s bought single_spread via YooKassa", telegram_id)

        else:
            logger.warning("YooKassa webhook: unknown payload '%s'", payload)
            return web.Response(status=200)

    # Отправляем PDF-квитанцию (только если платёж был успешно записан)
    if payment is not None:
        try:
            pdf_bytes = generate_receipt(
                payment_id=payment.id,
                user_name=user.name or str(telegram_id),
                amount=amount_value,
                currency=currency,
                payment_type=payment.payment_type,
                created_at=payment.created_at,
            )
            await bot.send_document(
                telegram_id,
                BufferedInputFile(pdf_bytes, filename=f"receipt_{payment.id:06d}.pdf"),
                caption="📄 Ваша квитанция об оплате",
            )
        except Exception as e:
            logger.error("Failed to send receipt to %s: %s", telegram_id, e)

    return web.Response(status=200)


def setup_yookassa_webhook(app: web.Application, bot: Bot, session_maker: async_sessionmaker):
    app["bot"] = bot
    app["session_maker"] = session_maker
    app.router.add_post("/yookassa/webhook", yookassa_webhook_handler)
