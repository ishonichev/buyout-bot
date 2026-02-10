"""Обработка скриншотов от клиентов."""
from aiogram import Router, F
from aiogram.types import Message, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import logging
import asyncio

from bot.database.models import User, Order, OrderStatus, AnalyticsEvent, Product
from bot.keyboards.client_keyboards import get_main_menu
from bot.states.client_states import ClientStates
from bot.config import settings
from bot.services.sheets_service import SheetsService

logger = logging.getLogger(__name__)
router = Router(name='client_screenshots')


@router.message(ClientStates.WAITING_BASKET_SCREENSHOT, F.photo)
async def basket_screenshot_received(message: Message, state: FSMContext, session: AsyncSession, user: User):
    """Получен скриншот корзины."""
    data = await state.get_data()
    order_id = data.get('order_id')
    screenshots = data.get('screenshots', {})
    
    # Сохраняем file_id фото
    screenshots['basket'] = message.photo[-1].file_id
    await state.update_data(screenshots=screenshots)
    
    # Обновляем заказ в БД
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if order:
        order.basket_date = datetime.now()
        order.status = OrderStatus.BASKET_SENT
        await session.commit()
    
    # Аналитика: Кнопка 4
    event = AnalyticsEvent(user_id=user.tg_id, event_type="button_4")
    session.add(event)
    await session.commit()
    
    await message.answer(
        "✅ Скриншот корзины принят!\n\n"
        "📸 Теперь отправьте скриншот покупки"
    )
    await state.set_state(ClientStates.WAITING_BUY_SCREENSHOT)


@router.message(ClientStates.WAITING_BUY_SCREENSHOT, F.photo)
async def buy_screenshot_received(message: Message, state: FSMContext, session: AsyncSession, user: User):
    """Получен скриншот покупки."""
    data = await state.get_data()
    order_id = data.get('order_id')
    screenshots = data.get('screenshots', {})
    
    # Сохраняем file_id фото
    screenshots['buy'] = message.photo[-1].file_id
    await state.update_data(screenshots=screenshots)
    
    # Обновляем заказ в БД
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if order:
        order.buy_date = datetime.now()
        order.status = OrderStatus.BUY_SENT
        await session.commit()
    
    # Аналитика: Кнопка 5
    event = AnalyticsEvent(user_id=user.tg_id, event_type="button_5")
    session.add(event)
    await session.commit()
    
    await message.answer(
        "✅ Скриншот покупки принят!\n\n"
        "📸 Теперь отправьте скриншот товара на руках"
    )
    await state.set_state(ClientStates.WAITING_RECEIVED_SCREENSHOT)


@router.message(ClientStates.WAITING_RECEIVED_SCREENSHOT, F.photo)
async def received_screenshot(message: Message, state: FSMContext, session: AsyncSession, user: User):
    """Получен скриншот товара на руках."""
    data = await state.get_data()
    order_id = data.get('order_id')
    screenshots = data.get('screenshots', {})
    
    # Сохраняем file_id фото
    screenshots['received'] = message.photo[-1].file_id
    await state.update_data(screenshots=screenshots)
    
    # Обновляем заказ в БД
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if order:
        order.received_date = datetime.now()
        order.status = OrderStatus.RECEIVED
        await session.commit()
    
    # Аналитика: Кнопка 6
    event = AnalyticsEvent(user_id=user.tg_id, event_type="button_6")
    session.add(event)
    await session.commit()
    
    review_text = (
        "👍 Отлично!\n\n"
        "📝 Добрый день!\n\n"
        "Отзыв ЗАВТРА на карточку:\n"
        "⭐️ 5 звезд БЕЗ ТЕКСТА И ФОТО\n\n"
        "После подтверждения модерации пришлите, пожалуйста:\n"
        "📸 Скриншот опубликованного отзыва"
    )
    
    await message.answer(review_text)
    await state.set_state(ClientStates.WAITING_REVIEW_SCREENSHOT)


@router.message(ClientStates.WAITING_REVIEW_SCREENSHOT, F.photo)
async def review_screenshot_received(message: Message, state: FSMContext, session: AsyncSession, user: User):
    """Получен скриншот отзыва."""
    data = await state.get_data()
    order_id = data.get('order_id')
    screenshots = data.get('screenshots', {})
    
    # Сохраняем file_id фото
    screenshots['review'] = message.photo[-1].file_id
    await state.update_data(screenshots=screenshots)
    
    # Обновляем заказ в БД
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if order:
        order.status = OrderStatus.REVIEW_MODERATION
        await session.commit()
    
    # Аналитика: Кнопка 7
    event = AnalyticsEvent(user_id=user.tg_id, event_type="button_7")
    session.add(event)
    await session.commit()
    
    await message.answer(
        "✅ Скриншот отзыва получен!\n\n"
        "📝 Теперь укажите:\n"
        "• Ваше имя на WildBerries\n"
        "• Реквизиты для перевода кэшбэка\n\n"
        "Например: Иван Иванов, +79001234567"
    )
    await state.set_state(ClientStates.WAITING_PAYMENT_DETAILS)


@router.message(ClientStates.WAITING_PAYMENT_DETAILS, F.text)
async def payment_details_received(message: Message, state: FSMContext, session: AsyncSession, user: User, sheets_service: SheetsService):
    """Получены реквизиты - ЗАВЕРШАЕМ ЗАКАЗ!"""
    data = await state.get_data()
    order_id = data.get('order_id')
    product_name = data.get('product_name', 'Неизвестно')
    cashback_amount = data.get('cashback_amount', 0)
    username = data.get('username', 'Неизвестно')
    screenshots = data.get('screenshots', {})
    
    # Обновляем заказ в БД
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if order:
        order.payment_details = message.text
        await session.commit()
    
    # ЗАПИСЫВАЕМ В GOOGLE SHEETS ЛИСТ1 ТОЛЬКО СЕЙЧАС (ПОЛНУЮ СТРОКУ!)
    if sheets_service and order:
        try:
            # Фоновая задача - не блокирует бота
            asyncio.create_task(
                sheets_service.add_order_to_sheet1({
                    'order_id': order_id,
                    'username': username,
                    'basket_date': order.basket_date,
                    'buy_date': order.buy_date,
                    'received_date': order.received_date,
                    'review_date': datetime.now(),
                    'cashback_amount': cashback_amount
                })
            )
            logger.info(f"[📊] Запись заказа {order_id} в Google Sheets запущена")
        except Exception as e:
            logger.error(f"[❌] Ошибка записи в Google Sheets: {e}")
    
    # Формируем сообщение для админа со ВСЕМИ фото
    admin_text = (
        f"🔔 Новый заказ на модерации!\n\n"
        f"👤 Пользователь: {message.from_user.full_name}\n"
    )
    
    if message.from_user.username:
        admin_text += f"🆔 Username: @{message.from_user.username}\n"
    
    admin_text += (
        f"🆔 ID: {user.tg_id}\n\n"
        f"📦 Товар: {product_name}\n"
        f"💰 Сумма кэшбэка: {cashback_amount} ₽\n\n"
        f"📝 Реквизиты:\n{message.text}"
    )
    
    # Отправляем админам медиагруппу со всеми фото
    media_group = []
    
    if 'basket' in screenshots:
        media_group.append(InputMediaPhoto(
            media=screenshots['basket'],
            caption=admin_text if len(media_group) == 0 else None
        ))
    
    if 'buy' in screenshots:
        media_group.append(InputMediaPhoto(
            media=screenshots['buy'],
            caption=admin_text if len(media_group) == 0 else None
        ))
    
    if 'received' in screenshots:
        media_group.append(InputMediaPhoto(
            media=screenshots['received'],
            caption=admin_text if len(media_group) == 0 else None
        ))
    
    if 'review' in screenshots:
        media_group.append(InputMediaPhoto(
            media=screenshots['review'],
            caption=admin_text if len(media_group) == 0 else None
        ))
    
    # Отправляем всем админам
    for admin_id in settings.admin_ids:
        try:
            if media_group:
                await message.bot.send_media_group(admin_id, media=media_group)
            else:
                await message.bot.send_message(admin_id, admin_text)
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления админу {admin_id}: {e}")
    
    await message.answer(
        "✅ Спасибо!\n\n"
        "Ваш заказ отправлен на модерацию. "
        "Мы свяжемся с вами в ближайшее время! 🙏",
        reply_markup=get_main_menu()
    )
    await state.clear()
    
    logger.info(f"Пользователь {user.tg_id} завершил заказ {order_id}")
