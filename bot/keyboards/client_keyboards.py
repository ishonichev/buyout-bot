"""Клавиатуры для клиентов."""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from typing import List
from bot.database.models import Product


def get_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню клиента."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛋️ Выбрать товар")],
            [KeyboardButton(text="❓ Есть вопросы")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_products_keyboard(products: List[Product]) -> InlineKeyboardMarkup:
    """Клавиатура выбора товара (до 4 слотов)."""
    buttons = []
    
    # Создаем 4 слота (ID 1-4)
    for slot_id in range(1, 5):
        product = next((p for p in products if p.id == slot_id), None)
        
        if product and product.is_active:
            # Активный товар
            buttons.append([
                InlineKeyboardButton(
                    text=f"🛍 {product.name}",
                    callback_data=f"product:{product.id}"
                )
            ])
        else:
            # Пустой слот
            buttons.append([
                InlineKeyboardButton(
                    text="⬜️ Нет товара",
                    callback_data="empty"
                )
            ])
    
    # Кнопка назад
    buttons.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back_to_main"
        )
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_agreement_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура согласия с условиями."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Я прочитал и согласен с условиями",
                callback_data="agree"
            )
        ],
        [
            InlineKeyboardButton(
                text="❓ Есть вопросы",
                callback_data="ask_question"
            )
        ]
    ])
    return keyboard


def get_send_photo_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для отправки фото."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📤 Отправить фото",
                callback_data="send_photo_reminder"
            )
        ]
    ])
    return keyboard
