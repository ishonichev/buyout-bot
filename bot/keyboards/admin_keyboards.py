"""Клавиатуры для админ-панели."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List
from bot.database.models import Product


def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню админа."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Управление товарами", callback_data="admin:products")]
    ])
    return keyboard


def get_products_list_keyboard(products: List[Product]) -> InlineKeyboardMarkup:
    """Список товаров для редактирования."""
    buttons = []
    
    for product in products:
        status = "✅" if product.is_active else "❌"
        button_text = f"{status} {product.name}"
        buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"admin:edit_product:{product.id}")])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_product_edit_keyboard(product_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """Меню редактирования товара."""
    toggle_text = "❌ Отключить" if is_active else "✅ Включить"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить название", callback_data=f"admin:edit:name:{product_id}")],
        [InlineKeyboardButton(text="🔗 Изменить ссылку", callback_data=f"admin:edit:url:{product_id}")],
        [InlineKeyboardButton(text="💰 Изменить сумму кэшбэка", callback_data=f"admin:edit:cashback:{product_id}")],
        [InlineKeyboardButton(text="📝 Изменить инструкцию", callback_data=f"admin:edit:instruction:{product_id}")],
        [InlineKeyboardButton(text=toggle_text, callback_data=f"admin:toggle:{product_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:products")]
    ])
    return keyboard


def get_review_moderation_keyboard(order_id: int, user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура модерации отзыва."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"admin:approve:{order_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin:reject:{order_id}")],
        [InlineKeyboardButton(text="💬 Связаться с пользователем", callback_data=f"support:start:{user_id}")]
    ])
    return keyboard
