"""Модели базы данных."""
from datetime import datetime
from sqlalchemy import BigInteger, String, Integer, Boolean, DateTime, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from bot.database.database import Base
import enum


class OrderStatus(enum.Enum):
    """Статусы заказа."""
    STARTED = "started"  # Начато
    BASKET_SENT = "basket_sent"  # Отправлен скриншот корзины
    BUY_SENT = "buy_sent"  # Отправлен скриншот покупки
    RECEIVED = "received"  # Товар на руках
    REVIEW_MODERATION = "review_moderation"  # Отзыв на модерации
    COMPLETED = "completed"  # Завершено
    CANCELLED = "cancelled"  # Отменен


class User(Base):
    """Модель пользователя."""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    registration_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)


class Product(Base):
    """Модель товара."""
    __tablename__ = "products"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # 1-4
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    cashback_amount: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    instruction_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Order(Base):
    """Модель заказа."""
    __tablename__ = "orders"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(SQLEnum(OrderStatus), default=OrderStatus.STARTED)
    
    # Даты этапов
    basket_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    buy_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    received_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    review_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    # Реквизиты для кэшбэка
    payment_details: Mapped[str] = mapped_column(Text, nullable=True)
    wb_username: Mapped[str] = mapped_column(String(255), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AnalyticsEvent(Base):
    """Модель события аналитики."""
    __tablename__ = "analytics_events"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)  # button_1, button_2, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
