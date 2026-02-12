"""Клавиатуры для администратора."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from bot.config import settings


def get_admin_menu() -> InlineKeyboardMarkup:
    """Главное меню админа."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🛠 Открыть веб-панель",
                web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}")
            )
        ]
    ])
    return keyboard


def get_webapp_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для открытия веб-панели."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📝 Открыть настройки",
                web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}")
            )
        ]
    ])
    return keyboard


def get_order_moderation_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для модерации заказа."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=f"admin:approve:{order_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"admin:reject:{order_id}"
            )
        ]
    ])
    return keyboard
