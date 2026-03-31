import uuid
import aiohttp
import logging
from src.config import settings

logger = logging.getLogger(__name__)

YOOKASSA_API_URL = "https://api.yookassa.ru/v3/payments"


async def create_payment(
    amount: float,
    currency: str,
    description: str,
    payload: str,
    return_url: str,
    telegram_id: int = 0,
) -> dict:
    """
    Создаёт платёж через API ЮKassa.
    Возвращает dict с полями: id, confirmation_url, status
    """
    idempotence_key = str(uuid.uuid4())

    body = {
        "amount": {
            "value": f"{amount:.2f}",
            "currency": currency,
        },
        "confirmation": {
            "type": "redirect",
            "return_url": return_url,
        },
        "capture": True,
        "description": description,
        "metadata": {
            "payload": payload,
            "telegram_id": str(telegram_id),
        },
    }

    auth = aiohttp.BasicAuth(
        login=str(settings.YOOKASSA_SHOP_ID),
        password=settings.YOOKASSA_SECRET_KEY,
    )

    async with aiohttp.ClientSession() as session:
        async with session.post(
            YOOKASSA_API_URL,
            json=body,
            auth=auth,
            headers={"Idempotence-Key": idempotence_key},
        ) as resp:
            data = await resp.json()
            if resp.status != 200:
                logger.error("YooKassa create_payment error %s: %s", resp.status, data)
                raise RuntimeError(data.get("description", "YooKassa API error"))
            return {
                "id": data["id"],
                "confirmation_url": data["confirmation"]["confirmation_url"],
                "status": data["status"],
            }
