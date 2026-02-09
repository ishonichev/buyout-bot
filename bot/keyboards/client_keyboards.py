"""Клавиатуры для клиентской части бота."""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from typing import List


def get_main_menu():
    """Главное меню."""
    builder = ReplyKeyboardBuilder()
    builder.button(text="🛋️ Выбрать товар")
    builder.button(text="❓ Есть вопросы")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_products_keyboard(products: List):
    """Клавиатура с товарами (инлайн для выбора)."""
    builder = InlineKeyboardBuilder()
    
    for product in products:
        if product.is_active:
            builder.button(
                text=f"📦 {product.name}",
                callback_data=f"product:{product.id}"
            )
        else:
            builder.button(
                text="❌ Нет в наличии",
                callback_data="empty"
            )
    
    builder.button(text="⬅️ Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()


def get_agreement_keyboard():
    """Клавиатура согласия с условиями."""
    builder = ReplyKeyboardBuilder()
    builder.button(text="✅ Я согласен")
    builder.button(text="❓ Есть вопросы")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_process_keyboard():
    """Клавиатура в процессе выкупа."""
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Отменить прогресс")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_cancel_keyboard():
    """Клавиатура отмены."""
    builder = ReplyKeyboardBuilder()
    builder.button(text="❌ Отменить")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)
