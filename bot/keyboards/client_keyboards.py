"""Клавиатуры для клиентской части."""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from typing import List


def get_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню - только две кнопки."""
    keyboard = [
        [KeyboardButton(text="🛋️ Выбрать товар")],
        [KeyboardButton(text="❓ Есть вопросы")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_products_keyboard(products: List) -> InlineKeyboardMarkup:
    """Инлайн клавиатура с товарами (максимум 4)."""
    buttons = []
    
    for i in range(4):
        if i < len(products) and products[i].is_active:
            product = products[i]
            buttons.append([
                InlineKeyboardButton(
                    text=product.name,
                    callback_data=f"product:{product.id}"
                )
            ])
        else:
            buttons.append([
                InlineKeyboardButton(
                    text="— Товара нет —",
                    callback_data="empty"
                )
            ])
    
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_agreement_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура согласия с инструкцией."""
    buttons = [
        [InlineKeyboardButton(text="✅ Я прочитал и согласен", callback_data="agree")],
        [InlineKeyboardButton(text="❓ Есть вопросы", callback_data="ask_question")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
