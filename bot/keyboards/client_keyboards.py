"""Клавиатуры для клиентов."""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from typing import List
from bot.database.models import Product


def get_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню клиента."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛍️ Выбрать товар")],
            [KeyboardButton(text="👥 Поддержка")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_main_menu_with_cancel() -> ReplyKeyboardMarkup:
    """Меню с кнопкой отмены прогресса."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отменить прогресс")],
            [KeyboardButton(text="👥 Поддержка")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_support_menu() -> ReplyKeyboardMarkup:
    """Меню в режиме поддержки."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔚 Завершить диалог")]
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
    
    # Кнопку "Назад" УБРАЛИ (по ТЗ)
    
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


# Кнопки для админов (поддержка)
def get_support_admin_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для админа при запросе поддержки."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Откликнуться",
                callback_data=f"support_respond:{user_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Игнорировать",
                callback_data=f"support_ignore:{user_id}"
            )
        ]
    ])
    return keyboard
