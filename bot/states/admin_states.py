"""Состояния для админ-панели."""
from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    """Состояния админа при редактировании товаров."""
    # Редактирование товара
    EDIT_PRODUCT_NAME = State()
    EDIT_PRODUCT_URL = State()
    EDIT_PRODUCT_CASHBACK = State()
    EDIT_PRODUCT_INSTRUCTION = State()
