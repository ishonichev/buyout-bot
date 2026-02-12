"""Новая клиентская логика с пошаговой воронкой."""
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
from datetime import datetime

from bot.database.models import User, Product, Order, OrderStatus, AnalyticsEvent, BotConfig
from bot.keyboards.client_keyboards import (
    get_main_menu,
    get_main_menu_with_cancel,
    get_products_keyboard,
    get_agreement_keyboard
)
from bot.states.client_states import ClientStates
from bot.config import settings
from bot.services.sheets_service import SheetsService

logger = logging.getLogger(__name__)
router = Router(name='client_new')


async def get_config_text(session: AsyncSession, key: str) -> str:
    """Получить текст из конфига."""
    result = await session.execute(
        select(BotConfig).where(BotConfig.config_key == key)
    )
    config = result.scalar_one_or_none()
    return config.config_value if config else "Не настроено"


async def has_active_order(session: AsyncSession, user_id: int) -> bool:
    """Проверка наличия активного заказа."""
    result = await session.execute(
        select(Order).where(
            Order.user_id == user_id,
            Order.status.in_([
                OrderStatus.STARTED,
                OrderStatus.BASKET_SENT,
                OrderStatus.BUY_SENT,
                OrderStatus.RECEIVED,
                OrderStatus.REVIEW_SENT
            ])
        )
    )
    return result.scalar_one_or_none() is not None


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, user: User, state: FSMContext, sheets_service: SheetsService):
    """Обработка команды /start."""
    # Аналитика
    event = AnalyticsEvent(user_id=user.tg_id, event_type="bot_started")
    session.add(event)
    await session.commit()
    
    if sheets_service:
        sheets_service.increment_analytics_event("bot_started", user.tg_id)
    
    # Получаем текст из конфига
    welcome_text = await get_config_text(session, "welcome_message")
    
    # Проверяем, есть ли активный заказ
    active_order = await has_active_order(session, user.tg_id)
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_with_cancel() if active_order else get_main_menu()
    )
    logger.info(f"Пользователь {user.tg_id} запустил бота")


@router.message(F.text.contains("Выбрать товар"))
async def select_product(message: Message, session: AsyncSession, user: User, sheets_service: SheetsService):
    """Выбор товара."""
    # Проверяем, нет ли уже активного заказа
    if await has_active_order(session, user.tg_id):
        await message.answer(
            "❌ У вас уже есть активный заказ!\n"
            "Используйте кнопку \"Отменить прогресс\", чтобы начать заново."
        )
        return
    
    # Аналитика
    event = AnalyticsEvent(user_id=user.tg_id, event_type="button_1")
    session.add(event)
    await session.commit()
    
    if sheets_service:
        sheets_service.increment_analytics_event("button_1", user.tg_id)
    
    # Получаем товары
    result = await session.execute(select(Product).order_by(Product.id).limit(4))
    products = result.scalars().all()
    
    # Получаем текст
    products_text = await get_config_text(session, "products_select_text")
    
    await message.answer(
        products_text,
        reply_markup=get_products_keyboard(products)
    )


@router.message(F.text.contains("Отменить прогресс"))
async def cancel_progress(message: Message, session: AsyncSession, user: User, state: FSMContext):
    """Отмена текущего заказа."""
    # Находим активный заказ
    result = await session.execute(
        select(Order).where(
            Order.user_id == user.tg_id,
            Order.status.in_([
                OrderStatus.STARTED,
                OrderStatus.BASKET_SENT,
                OrderStatus.BUY_SENT,
                OrderStatus.RECEIVED,
                OrderStatus.REVIEW_SENT
            ])
        )
    )
    order = result.scalar_one_or_none()
    
    if order:
        # Отменяем заказ
        await session.delete(order)
        await session.commit()
        
        # Очищаем FSM
        await state.clear()
        
        await message.answer(
            "✅ Прогресс отменен. Можете выбрать новый товар.",
            reply_markup=get_main_menu()
        )
        logger.info(f"Пользователь {user.tg_id} отменил заказ #{order.id}")
    else:
        await message.answer("❌ У вас нет активных заказов.")


@router.message(F.text.contains("Поддержка"))
async def ask_support(message: Message, user: User):
    """Обработка запроса поддержки."""
    from bot.keyboards.client_keyboards import get_support_admin_keyboard
    
    admin_text = (
        f"💬 Пользователь просит поддержки!\n\n"
        f"🆔 ID: {user.tg_id}\n"
        f"👤 Имя: {message.from_user.full_name}\n"
    )
    
    if message.from_user.username:
        admin_text += f"🆔 Username: @{message.from_user.username}\n"
    
    for admin_id in settings.admin_ids:
        try:
            await message.bot.send_message(
                admin_id,
                admin_text,
                reply_markup=get_support_admin_keyboard(user.tg_id)
            )
        except Exception as e:
            logger.error(f"Ошибка отправки админу {admin_id}: {e}")
    
    await message.answer(
        "✅ Ваш запрос отправлен оператору.\n"
        "Мы свяжемся с вами в ближайшее время! 👍"
    )


@router.callback_query(F.data == "empty")
async def empty_product(callback: CallbackQuery):
    """Пустой слот товара."""
    await callback.answer("❌ Товара пока нет", show_alert=True)


@router.callback_query(F.data.startswith("product:"))
async def select_product_callback(callback: CallbackQuery, session: AsyncSession, user: User, state: FSMContext, sheets_service: SheetsService):
    """Выбор товара - показ инструкции."""
    product_id = int(callback.data.split(":")[1])
    
    # Аналитика
    event = AnalyticsEvent(user_id=user.tg_id, event_type="button_2")
    session.add(event)
    await session.commit()
    
    if sheets_service:
        sheets_service.increment_analytics_event("button_2", user.tg_id)
    
    # Получаем товар
    result = await session.execute(
        select(Product).where(Product.id == product_id)
    )
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
    
    # Сохраняем в состояние
    username = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
    
    await state.update_data(
        order_id=order.id,
        product_id=product.id,
        product_name=product.name,
        username=username
    )
    
    # Отправляем инструкцию (только текст из Product)
    await callback.message.delete()
    await callback.message.answer(
        product.instruction_text,
        reply_markup=get_agreement_keyboard()
    )
    await callback.answer()
    
    logger.info(f"Пользователь {user.tg_id} выбрал товар {product.name}")


@router.callback_query(F.data == "agree")
async def agree_instruction(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User, sheets_service: SheetsService):
    """Согласие с инструкцией - ШАГ 1."""
    data = await state.get_data()
    
    if not data.get('order_id'):
        await callback.answer("❌ Сначала выберите товар", show_alert=True)
        return
    
    # Аналитика
    event = AnalyticsEvent(user_id=user.tg_id, event_type="button_3")
    session.add(event)
    await session.commit()
    
    if sheets_service:
        sheets_service.increment_analytics_event("button_3", user.tg_id)
    
    # Устанавливаем состояние
    await state.set_state(ClientStates.WAITING_BASKET_SCREENSHOT)
    
    # Получаем текст Шага 1
    step1_text = await get_config_text(session, "step_1_message")
    
    # Меняем клавиатуру на меню с кнопкой отмены
    await callback.message.delete()
    await callback.message.answer(
        step1_text,
        reply_markup=get_main_menu_with_cancel()
    )
    await callback.answer()


@router.callback_query(F.data == "ask_question")
async def ask_question_callback(callback: CallbackQuery, user: User):
    """Вопрос через callback."""
    from bot.keyboards.client_keyboards import get_support_admin_keyboard
    
    admin_text = (
        f"💬 Пользователь просит поддержки!\n\n"
        f"🆔 ID: {user.tg_id}\n"
        f"👤 Имя: {callback.from_user.full_name}\n"
    )
    
    if callback.from_user.username:
        admin_text += f"🆔 Username: @{callback.from_user.username}\n"
    
    for admin_id in settings.admin_ids:
        try:
            await callback.bot.send_message(
                admin_id,
                admin_text,
                reply_markup=get_support_admin_keyboard(user.tg_id)
            )
        except Exception as e:
            logger.error(f"Ошибка {admin_id}: {e}")
    
    await callback.answer("✅ Запрос отправлен", show_alert=True)


# Обработчики фото (пошагово)
@router.message(ClientStates.WAITING_BASKET_SCREENSHOT, F.photo)
async def basket_screenshot(message: Message, state: FSMContext, session: AsyncSession, user: User, sheets_service: SheetsService):
    """ШАГ 1: Скриншот корзины."""
    data = await state.get_data()
    order_id = data.get('order_id')
    
    # Обновляем заказ
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if order:
        order.status = OrderStatus.BASKET_SENT
        order.basket_date = datetime.now()
        await session.commit()
    
    # Сохраняем file_id
    await state.update_data(basket_photo=message.photo[-1].file_id)
    
    # Аналитика
    event = AnalyticsEvent(user_id=user.tg_id, event_type="button_4")
    session.add(event)
    await session.commit()
    
    if sheets_service:
        sheets_service.increment_analytics_event("button_4", user.tg_id)
    
    # Переходим к Шагу 2
    await state.set_state(ClientStates.WAITING_BUY_SCREENSHOT)
    
    step2_text = await get_config_text(session, "step_2_message")
    await message.answer(step2_text)


@router.message(ClientStates.WAITING_BUY_SCREENSHOT, F.photo)
async def buy_screenshot(message: Message, state: FSMContext, session: AsyncSession, user: User, sheets_service: SheetsService):
    """ШАГ 2: Скриншот покупки."""
    data = await state.get_data()
    order_id = data.get('order_id')
    
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if order:
        order.status = OrderStatus.BUY_SENT
        order.buy_date = datetime.now()
        await session.commit()
    
    await state.update_data(buy_photo=message.photo[-1].file_id)
    
    event = AnalyticsEvent(user_id=user.tg_id, event_type="button_5")
    session.add(event)
    await session.commit()
    
    if sheets_service:
        sheets_service.increment_analytics_event("button_5", user.tg_id)
    
    # Переходим к Шагу 3
    await state.set_state(ClientStates.WAITING_RECEIVED_SCREENSHOT)
    
    step3_text = await get_config_text(session, "step_3_message")
    await message.answer(step3_text)


@router.message(ClientStates.WAITING_RECEIVED_SCREENSHOT, F.photo)
async def received_screenshot(message: Message, state: FSMContext, session: AsyncSession, user: User, sheets_service: SheetsService):
    """ШАГ 3: Скриншот получения."""
    data = await state.get_data()
    order_id = data.get('order_id')
    
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if order:
        order.status = OrderStatus.RECEIVED
        order.received_date = datetime.now()
        await session.commit()
    
    await state.update_data(received_photo=message.photo[-1].file_id)
    
    event = AnalyticsEvent(user_id=user.tg_id, event_type="button_6")
    session.add(event)
    await session.commit()
    
    if sheets_service:
        sheets_service.increment_analytics_event("button_6", user.tg_id)
    
    # Переходим к Шагу 4 (отзыв)
    await state.set_state(ClientStates.WAITING_REVIEW_SCREENSHOT)
    
    step4_text = await get_config_text(session, "step_4_message")
    await message.answer(step4_text)


@router.message(ClientStates.WAITING_REVIEW_SCREENSHOT, F.photo)
async def review_screenshot(message: Message, state: FSMContext, session: AsyncSession, user: User, sheets_service: SheetsService):
    """ШАГ 4: Скриншот отзыва."""
    data = await state.get_data()
    order_id = data.get('order_id')
    
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if order:
        order.status = OrderStatus.REVIEW_SENT
        order.review_date = datetime.now()
        await session.commit()
    
    await state.update_data(review_photo=message.photo[-1].file_id)
    
    event = AnalyticsEvent(user_id=user.tg_id, event_type="button_7")
    session.add(event)
    await session.commit()
    
    if sheets_service:
        sheets_service.increment_analytics_event("button_7", user.tg_id)
    
    # Переходим к Шагу 5 (реквизиты)
    await state.set_state(ClientStates.WAITING_PAYMENT_DETAILS)
    
    step5_text = await get_config_text(session, "step_5_message")
    await message.answer(step5_text)


@router.message(ClientStates.WAITING_PAYMENT_DETAILS, F.text)
async def payment_details(message: Message, state: FSMContext, session: AsyncSession, user: User):
    """ШАГ 5: Реквизиты."""
    data = await state.get_data()
    order_id = data.get('order_id')
    
    # Обновляем заказ
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if order:
        order.payment_details = message.text
        order.status = OrderStatus.PENDING_APPROVAL
        await session.commit()
    
    # Отправляем сообщение пользователю
    pending_text = await get_config_text(session, "order_pending_message")
    await message.answer(
        pending_text,
        reply_markup=get_main_menu()  # Возвращаем обычное меню
    )
    
    # Отправляем всё админам (АЛЬБОМОМ!)
    from bot.keyboards.admin_keyboards import get_order_moderation_keyboard
    
    for admin_id in settings.admin_ids:
        try:
            admin_text = (
                f"🔔 Новый заказ на модерации!\n\n"
                f"🆔 Заказ #{order_id}\n"
                f"👤 Пользователь: {data['username']}\n"
                f"🛍️ Товар: {data['product_name']}\n"
                f"💳 Реквизиты: {message.text}\n"
            )
            
            # Отправляем все фото АЛЬБОМОМ (MediaGroup)
            await message.bot.send_message(admin_id, admin_text)
            
            media_group = [
                InputMediaPhoto(media=data['basket_photo'], caption="📦 Корзина"),
                InputMediaPhoto(media=data['buy_photo'], caption="💳 Покупка"),
                InputMediaPhoto(media=data['received_photo'], caption="📦 Получено"),
                InputMediaPhoto(media=data['review_photo'], caption="⭐ Отзыв")
            ]
            
            await message.bot.send_media_group(admin_id, media=media_group)
            
            # Кнопки модерации отправляем отдельным сообщением
            await message.bot.send_message(
                admin_id,
                "👇 Действия:",
                reply_markup=get_order_moderation_keyboard(order_id)
            )
        except Exception as e:
            logger.error(f"Ошибка отправки админу {admin_id}: {e}")
    
    await state.clear()
    logger.info(f"Заказ #{order_id} отправлен на модерацию")
