"""Клавиатуры для клиентской части."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List
from bot.database.models import Product


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню бота."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Выбрать товар для выкупа 🢒", callback_data="select_product")]
    ])
    return keyboard


def get_products_keyboard(products: List[Product]) -> InlineKeyboardMarkup:
    """Клавиатура выбора товара."""
    buttons = []
    
    for product in products:
        if product.is_active:
            button_text = product.name
            callback_data = f"buy:{product.id}"
        else:
            # Пустая кнопка (невидимый символ)
            button_text = "ㅤ"  # Корейский невидимый символ
            callback_data = "empty"
        
        buttons.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
    
    # Кнопка назад
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_instruction_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после инструкции."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Я прочитал инструкцию и согласен с условиями", callback_data="agree_instruction")],
        [InlineKeyboardButton(text="Есть вопросы", callback_data="has_questions")]
    ])
    return keyboard


def get_confirm_screenshot_keyboard(step: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения отправки скриншота."""
    step_texts = {
        "basket": "Отправить скриншот товара в корзине 📸",
        "buy": "Отправить скриншот покупки 💳",
        "received": "Товар на руках 📦",
        "review": "Скриншот опубликованного отзыва ⭐️"
    }
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=step_texts.get(step, "Отправить"), callback_data=f"send_screenshot:{step}")]
    ])
    return keyboard
