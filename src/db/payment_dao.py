from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Payment

class PaymentDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_payment(self, user_id: int, amount: float, payment_type: str, status: str = "success") -> Payment:
        payment = Payment(
            user_id=user_id,
            amount=amount,
            payment_type=payment_type,
            status=status
        )
        self.session.add(payment)
        await self.session.commit()
        return payment

    async def get_all_payments(self):
        stmt = select(Payment).order_by(Payment.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()
