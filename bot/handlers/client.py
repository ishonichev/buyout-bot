"""Обработчики для клиентской части бота."""
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from bot.database.models import User, Product, Order, OrderStatus, AnalyticsEvent
from bot.keyboards.client_keyboards import (
    get_main_menu,
    get_products_keyboard,
    get_agreement_keyboard
)
from bot.states.client_states import ClientStates
from bot.config import settings
from bot.services.sheets_service import SheetsService

logger = logging.getLogger(__name__)
router = Router(name='client')


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, user: User, sheets_service: SheetsService):
    """Обработка команды /start."""
    # Аналитика: Запустили бот
    event = AnalyticsEvent(user_id=user.tg_id, event_type="bot_started")
    session.add(event)
    await session.commit()
    
    # Обновляем уникальных пользователей
    if sheets_service:
        sheets_service.increment_analytics_event("bot_started", user.tg_id)
    
    welcome_text = (
        "👋 Привет!\n\n"
        "Для вашего и нашего удобства и экономии времени мы создали бота "
        "для выкупов со 100% кэшбэком.\n\n"
        "Вы сможете в любое время зайти и проверить какие товары доступны для выкупа "
        "и сразу их заказать не дожидаясь ответа от нашего менеджера.\n\n"
        "В случае вопросов и нестандартных ситуаций наш оператор выйдет на связь. "
        "Обещаем не спамить! 😉"
    )
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu()
    )
    logger.info(f"Пользователь {user.tg_id} запустил бота")


@router.message(F.text == "🛌️ Выбрать товар")
async def select_product(message: Message, session: AsyncSession, user: User, sheets_service: SheetsService):
    """Выбор товара."""
    # Аналитика: Кнопка 1
    event = AnalyticsEvent(user_id=user.tg_id, event_type="button_1")
    session.add(event)
    await session.commit()
    
    if sheets_service:
        sheets_service.increment_analytics_event("button_1", user.tg_id)
    
    result = await session.execute(select(Product).order_by(Product.id))
    products = result.scalars().all()
    
    await message.answer(
        "🛌️ Выберите товар для выкупа:",
        reply_markup=get_products_keyboard(products)
    )


@router.message(F.text == "❓ Есть вопросы")
async def ask_question(message: Message, user: User, session: AsyncSession):
    """Обработка вопросов пользователя."""
    admin_text = (
        f"👤 Пользователь просит помощи!\n\n"
        f"🆔 ID: {user.tg_id}\n"
        f"👤 Имя: {message.from_user.full_name}\n"
    )
    
    if message.from_user.username:
        admin_text += f"🆔 Username: @{message.from_user.username}\n"
    
    for admin_id in settings.admin_ids:
        try:
            await message.bot.send_message(admin_id, admin_text)
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления админу {admin_id}: {e}")
    
    await message.answer(
        "✅ Ваш запрос отправлен оператору.\n"
        "Мы свяжемся с вами в ближайшее время! 👍"
    )


@router.callback_query(F.data == "empty")
async def empty_product(callback: CallbackQuery):
    """Обработка нажатия на пустую кнопку."""
    await callback.answer("❌ Товара пока нет", show_alert=True)


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню."""
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data.startswith("product:"))
async def buy_product(callback: CallbackQuery, session: AsyncSession, user: User, state: FSMContext, sheets_service: SheetsService):
    """Начало процесса выкупа."""
    product_id = int(callback.data.split(":")[1])
    
    # Аналитика: Кнопка 2
    event = AnalyticsEvent(user_id=user.tg_id, event_type="button_2")
    session.add(event)
    await session.commit()
    
    if sheets_service:
        sheets_service.increment_analytics_event("button_2", user.tg_id)
    
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
    
    # Сохраняем данные в состояние
    username = callback.from_user.username
    if username:
        username = f"@{username}"
    else:
        username = callback.from_user.full_name
    
    await state.update_data(
        order_id=order.id,
        product_id=product.id,
        product_name=product.name,
        cashback_amount=product.cashback_amount,
        username=username,
        screenshots={}
    )
    
    # Отправляем инструкцию
    instruction_text = (
        f"📜 Инструкция по выкупу \"{product.name}\"\n\n"
        f"{product.instruction_text}\n\n"
        f"💰 Кэшбэк: {product.cashback_amount} ₽"
    )
    
    await callback.message.delete()
    await callback.message.answer(
        instruction_text,
        reply_markup=get_agreement_keyboard()
    )
    await callback.answer()
    
    logger.info(f"Пользователь {user.tg_id} начал выкуп товара {product.name}")


@router.callback_query(F.data == "agree")
async def agree_instruction(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User, sheets_service: SheetsService):
    """Пользователь согласился с инструкцией."""
    data = await state.get_data()
    
    if not data.get('order_id'):
        await callback.answer("❌ Сначала выберите товар", show_alert=True)
        return
    
    # Аналитика: Кнопка 3
    event = AnalyticsEvent(user_id=user.tg_id, event_type="button_3")
    session.add(event)
    await session.commit()
    
    if sheets_service:
        sheets_service.increment_analytics_event("button_3", user.tg_id)
    
    await state.set_state(ClientStates.WAITING_BASKET_SCREENSHOT)
    
    await callback.message.delete()
    await callback.message.answer(
        "✅ Отлично!\n\n"
        "📸 Отправьте скриншот товара в корзине"
    )
    await callback.answer()


@router.callback_query(F.data == "ask_question")
async def ask_question_callback(callback: CallbackQuery, user: User):
    """Обработка вопросов через callback."""
    admin_text = (
        f"👤 Пользователь просит помощи!\n\n"
        f"🆔 ID: {user.tg_id}\n"
        f"👤 Имя: {callback.from_user.full_name}\n"
    )
    
    if callback.from_user.username:
        admin_text += f"🆔 Username: @{callback.from_user.username}\n"
    
    for admin_id in settings.admin_ids:
        try:
            await callback.bot.send_message(admin_id, admin_text)
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления админу {admin_id}: {e}")
    
    await callback.answer(
        "✅ Ваш запрос отправлен оператору",
        show_alert=True
    )
