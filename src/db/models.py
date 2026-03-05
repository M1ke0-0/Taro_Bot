from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Date, DateTime, Float, Integer, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # "male" | "female"
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subscription_status: Mapped[str] = mapped_column(Text, nullable=False, default="free")
    subscription_end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_spreads: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_stress_index: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dominant_area: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
