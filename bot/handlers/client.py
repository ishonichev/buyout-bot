"""Обработчики для клиентской части бота."""
from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import logging

from bot.database.models import User, Product, Order, OrderStatus, AnalyticsEvent
from bot.keyboards.client_keyboards import (
    get_main_menu_keyboard,
    get_products_keyboard,
    get_instruction_keyboard,
    get_confirm_screenshot_keyboard
)
from bot.states.client_states import ClientStates

logger = logging.getLogger(__name__)
router = Router(name='client')


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, user: User):
    """Обработка команды /start."""
    # Аналитика: Зашли в бот
    event = AnalyticsEvent(user_id=user.tg_id, event_type="bot_visited")
    session.add(event)
    await session.commit()
    
    welcome_text = (
        "👋 <b>Привет!</b>\n\n"
        "Для вашего и нашего удобства и экономии времени мы создали бота "
        "для выкупов со 100% кэшбэком.\n\n"
        "Вы сможете в любое время зайти и проверить какие товары доступны для выкупа "
        "и сразу их заказать не дожидаясь ответа от нашего менеджера.\n\n"
        "В случае вопросов и нестандартных ситуаций наш оператор выйдет на связь. "
        "Обещаем не спамить! 😉"
    )
    
    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard())
    logger.info(f"Пользователь {user.tg_id} запустил бота")


@router.callback_query(F.data == "select_product")
async def select_product(callback: CallbackQuery, session: AsyncSession, user: User):
    """Выбор товара."""
    # Аналитика: Кнопка 1 - Запустили бот
    event = AnalyticsEvent(user_id=user.tg_id, event_type="bot_started")
    session.add(event)
    await session.commit()
    
    # Получаем все товары
    result = await session.execute(select(Product).order_by(Product.id))
    products = result.scalars().all()
    
    await callback.message.edit_text(
        "🛋️ Выберите товар для выкупа:",
        reply_markup=get_products_keyboard(products)
    )
    await callback.answer()


@router.callback_query(F.data == "empty")
async def empty_product(callback: CallbackQuery):
    """Обработка нажатия на пустую кнопку."""
    await callback.answer("❌ Товара пока нет", show_alert=True)


@router.callback_query(F.data.startswith("buy:"))
async def buy_product(callback: CallbackQuery, session: AsyncSession, user: User, state: FSMContext):
    """Начало процесса выкупа."""
    product_id = int(callback.data.split(":")[1])
    
    # Аналитика: Кнопка 2 - Нажали кнопку 1 (выбрали товар)
    event = AnalyticsEvent(user_id=user.tg_id, event_type="button_1")
    session.add(event)
    await session.commit()
    
    # Получаем товар
    result = await session.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product or not product.is_active:
        await callback.answer("❌ Товар недоступен", show_alert=True)
        return
    
    # Создаем заказ
    order = Order(
        user_id=user.tg_id,
        product_id=product.id,
        status=OrderStatus.STARTED
    )
    session.add(order)
    await session.commit()
    
    # Сохраняем order_id и product_id в состояние
    await state.update_data(order_id=order.id, product_id=product.id, cashback_amount=product.cashback_amount)
    
    # Отправляем инструкцию
    await callback.message.answer(
        f"📖 <b>Инструкция по выкупу \"{product.name}\"</b>\n\n"
        f"{product.instruction_text}",
        reply_markup=get_instruction_keyboard()
    )
    await callback.message.delete()
    await callback.answer()
    
    logger.info(f"Пользователь {user.tg_id} начал выкуп товара {product.name}")


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню."""
    welcome_text = (
        "👋 <b>Привет!</b>\n\n"
        "Для вашего и нашего удобства и экономии времени мы создали бота "
        "для выкупов со 100% кэшбэком."
    )
    await callback.message.edit_text(welcome_text, reply_markup=get_main_menu_keyboard())
    await callback.answer()
