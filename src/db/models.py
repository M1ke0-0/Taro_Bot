from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Float, Integer, Text, func, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.db.encrypted_type import EncryptedString


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    # Чувствительные поля — хранятся в БД в зашифрованном виде (Fernet AES-128-CBC)
    name: Mapped[Optional[str]] = mapped_column(EncryptedString(512), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(EncryptedString(512), nullable=True)

    dominant_area: Mapped[Optional[str]] = mapped_column(EncryptedString(512), nullable=True)
    subscription_status: Mapped[str] = mapped_column(Text, nullable=False, default="free")
    subscription_end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_report_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cached_weekly_report: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_spreads: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_stress_index: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TarotCard(Base):
    """
    Таблица карт Таро.
    Поле photo хранит Telegram file_id (заполняется позже).
    """
    __tablename__ = "tarot_cards"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    resource: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # Ресурсный аспект
    shadow: Mapped[Optional[str]] = mapped_column(Text, nullable=True)     # Теневой аспект
    stress_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    activity_type: Mapped[str] = mapped_column(Text, nullable=False, default="active")  # active | passive
    love_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.25)
    career_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.25)
    money_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.25)
    psy_weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.25)
    photo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)      # Telegram file_id


class SpreadHistory(Base):
    """
    Таблица истории раскладов пользователей для недельного отчета.
    """
    __tablename__ = "spread_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    cards: Mapped[str] = mapped_column(Text, nullable=False) # Названия карт через запятую
    stress_index: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Setting(Base):
    """
    Лимиты и настройки (цены, количество фри раскладов).
    """
    __tablename__ = "settings"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Payment(Base):
    """
    История платежей пользователей (разовые покупки, подписки).
    """
    __tablename__ = "payments"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_type: Mapped[str] = mapped_column(Text, nullable=False) # 'pro_sub', 'single_spread'
    status: Mapped[str] = mapped_column(Text, nullable=False, default="success") # 'pending', 'success', 'failed'
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

