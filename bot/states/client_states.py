"""Состояния для клиентской части бота."""
from aiogram.fsm.state import State, StatesGroup


class ClientStates(StatesGroup):
    """Состояния клиента в процессе выкупа."""
    # Ожидание скриншотов
    WAITING_BASKET_SCREENSHOT = State()
    WAITING_BUY_SCREENSHOT = State()
    WAITING_RECEIVED_SCREENSHOT = State()
    WAITING_REVIEW_SCREENSHOT = State()
    WAITING_PAYMENT_DETAILS = State()


class SupportStates(StatesGroup):
    """Состояния для работы с поддержкой."""
    CHATTING_WITH_USER = State()
