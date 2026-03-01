"""Модели базы данных."""
from datetime import datetime
from sqlalchemy import (CheckConstraint, BigInteger, String, Integer, Boolean,
                        DateTime, Text, Enum as SQLEnum, Float, ForeignKey)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from bot.database.database import Base
import enum


class OrderStatus(enum.Enum):
    """Статусы заказа."""
    STARTED = "started"  # Начато
    BASKET_SENT = "basket_sent"  # Отправлен скриншот корзины
    BUY_SENT = "buy_sent"  # Отправлен скриншот покупки
    RECEIVED = "received"  # Товар на руках
    REVIEW_SENT = "review_sent"  # Отзыв отправлен
    PENDING_APPROVAL = "pending_approval"  # Ожидает подтверждения
    ADMIN_PAYMENT_SENT = "admin_payment_sent"  # Админ отправил скрин перевода
    COMPLETED = "completed"  # Завершено
    REJECTED = "rejected"  # Отклонен


class User(Base):
    """Модель пользователя."""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    registration_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)

    orders: Mapped[list["Order"]] = relationship(back_populates="user")
    events: Mapped[list["AnalyticsEvent"]] = relationship(back_populates="user")


class Product(Base):
    """Модель товара."""
    __tablename__ = "products"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cashback: Mapped[float] = mapped_column(Float, CheckConstraint('cashback >= 0 AND cashback <= 100'),
                                            default=0.0, nullable=False)
    instruction_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    orders: Mapped[list["Order"]] = relationship(back_populates="product")


class BotConfig(Base):
    """Конфигурация бота"""
    __tablename__ = "bot_config"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    config_value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)  # Подсказка для админа
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class Order(Base):
    """Модель заказа."""
    __tablename__ = "orders"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_tg_id: Mapped[int] = mapped_column(ForeignKey("users.tg_id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(SQLEnum(OrderStatus), default=OrderStatus.STARTED)
    
    # Даты этапов
    basket_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    buy_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    received_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    review_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    # Реквизиты для кэшбэка
    payment_details: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Сумма кешбека (вводится админом)
    cashback_amount: Mapped[float] = mapped_column(Float, nullable=True)
    
    # Причина отклонения (если админ отклонил)
    rejection_reason: Mapped[str] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    user: Mapped["User"] = relationship(back_populates="orders")
    product: Mapped["Product"] = relationship(back_populates="orders")


class AnalyticsEvent(Base):
    """Модель события аналитики."""
    __tablename__ = "analytics_events"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_tg_id: Mapped[int] = mapped_column(ForeignKey("users.tg_id"), nullable=False,
                                            index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)  # button_1, button_2, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)

    user: Mapped["User"] = relationship(back_populates="events")