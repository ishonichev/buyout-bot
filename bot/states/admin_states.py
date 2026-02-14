"""Состояния администратора."""
from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    """Состояния администратора."""
    
    # Модерация заказов
    WAITING_CASHBACK_AMOUNT = State()  # Ожидание суммы кешбека
    WAITING_PAYMENT_SCREENSHOT = State()  # Ожидание скрина перевода
    WAITING_REJECTION_REASON = State()  # Ожидание причины отказа
    
    # Поддержка
    CHATTING_WITH_USER = State()  # Диалог с пользователем
