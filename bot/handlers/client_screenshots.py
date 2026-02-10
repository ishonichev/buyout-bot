"""Обработка скриншотов от клиентов."""
from aiogram import Router, F
from aiogram.types import Message, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import logging

from bot.database.models import User, Order, OrderStatus, AnalyticsEvent, Product
from bot.keyboards.client_keyboards import get_process_keyboard, get_main_menu
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
    
    # Обновляем заказ
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
        "✅ <b>Скриншот корзины принят!</b>\n\n"
        "📸 Теперь отправьте <b>скриншот покупки</b>",
        reply_markup=get_process_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ClientStates.WAITING_BUY_SCREENSHOT)


@router.message(ClientStates.WAITING_BUY_SCREENSHOT, F.photo)
async def buy_screenshot_received(message: Message, state: FSMContext, session: AsyncSession, user: User, sheets_service: SheetsService):
    """Получен скриншот покупки."""
    data = await state.get_data()
    order_id = data.get('order_id')
    cashback_amount = data.get('cashback_amount', 0)
    screenshots = data.get('screenshots', {})
    
    # Сохраняем file_id фото
    screenshots['buy'] = message.photo[-1].file_id
    await state.update_data(screenshots=screenshots)
    
    # Обновляем заказ
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if order:
        order.buy_date = datetime.now()
        order.status = OrderStatus.BUY_SENT
        await session.commit()
    
    # Записываем в Google Sheets (Лист1)
    if sheets_service:
        username = message.from_user.username
        if username:
            username = f"@{username}"
        else:
            username = message.from_user.full_name
            
        await sheets_service.add_order_to_sheet1({
            'order_id': order_id,
            'username': username,
            'basket_date': order.basket_date,
            'buy_date': order.buy_date,
            'cashback_amount': cashback_amount
        })
    
    # Аналитика: Кнопка 5
    event = AnalyticsEvent(user_id=user.tg_id, event_type="button_5")
    session.add(event)
    await session.commit()
    
    await message.answer(
        "✅ <b>Скриншот покупки принят!</b>\n\n"
        "📸 Теперь отправьте <b>скриншот товара на руках</b>",
        reply_markup=get_process_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ClientStates.WAITING_RECEIVED_SCREENSHOT)


@router.message(ClientStates.WAITING_RECEIVED_SCREENSHOT, F.photo)
async def received_screenshot(message: Message, state: FSMContext, session: AsyncSession, user: User, sheets_service: SheetsService):
    """Получен скриншот товара на руках."""
    data = await state.get_data()
    order_id = data.get('order_id')
    screenshots = data.get('screenshots', {})
    
    # Сохраняем file_id фото
    screenshots['received'] = message.photo[-1].file_id
    await state.update_data(screenshots=screenshots)
    
    # Обновляем заказ
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if order:
        order.received_date = datetime.now()
        order.status = OrderStatus.RECEIVED
        await session.commit()
    
    # Обновляем Google Sheets
    if sheets_service:
        username = message.from_user.username
        if username:
            username = f"@{username}"
        else:
            username = message.from_user.full_name
        await sheets_service.update_order_in_sheet1(username, 'received_date', order.received_date)
    
    # Аналитика: Кнопка 6
    event = AnalyticsEvent(user_id=user.tg_id, event_type="button_6")
    session.add(event)
    await session.commit()
    
    review_text = (
        "👍 <b>Отлично!</b>\n\n"
        "📝 <b>Добрый день!</b>\n\n"
        "Отзыв <b>ЗАВТРА</b> на карточку:\n"
        "⭐️ 5 звезд <b>БЕЗ ТЕКСТА И ФОТО</b>\n\n"
        "После подтверждения модерации пришлите, пожалуйста:\n"
        "📸 Скриншот опубликованного отзыва"
    )
    
    await message.answer(
        review_text,
        reply_markup=get_process_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(ClientStates.WAITING_REVIEW_SCREENSHOT)


@router.message(ClientStates.WAITING_REVIEW_SCREENSHOT, F.photo)
async def review_screenshot_received(message: Message, state: FSMContext, session: AsyncSession, user: User, sheets_service: SheetsService):
    """Получен скриншот отзыва."""
    data = await state.get_data()
    order_id = data.get('order_id')
    screenshots = data.get('screenshots', {})
    
    # Сохраняем file_id фото
    screenshots['review'] = message.photo[-1].file_id
    await state.update_data(screenshots=screenshots)
    
    # Обновляем заказ
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if order:
        order.status = OrderStatus.REVIEW_MODERATION
        await session.commit()
    
    # Обновляем Google Sheets
    if sheets_service:
        username = message.from_user.username
        if username:
            username = f"@{username}"
        else:
            username = message.from_user.full_name
        await sheets_service.update_order_in_sheet1(username, 'review_date', datetime.now())
    
    # Аналитика: Кнопка 7
    event = AnalyticsEvent(user_id=user.tg_id, event_type="button_7")
    session.add(event)
    await session.commit()
    
    # Просим указать реквизиты
    await message.answer(
        "✅ <b>Скриншот отзыва получен!</b>\n\n"
        "📝 Теперь укажите:\n"
        "• Ваше имя на WildBerries\n"
        "• Реквизиты для перевода кэшбэка\n\n"
        "Например: <i>Иван Иванов, +79001234567</i>",
        parse_mode="HTML"
    )
    await state.set_state(ClientStates.WAITING_PAYMENT_DETAILS)


@router.message(ClientStates.WAITING_PAYMENT_DETAILS, F.text)
async def payment_details_received(message: Message, state: FSMContext, session: AsyncSession, user: User):
    """Получены реквизиты - отправляем админу ВСЕ фото в одном сообщении."""
    data = await state.get_data()
    order_id = data.get('order_id')
    product_name = data.get('product_name', 'Неизвестно')
    cashback_amount = data.get('cashback_amount', 0)
    screenshots = data.get('screenshots', {})
    
    # Обновляем заказ
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if order:
        order.payment_details = message.text
        await session.commit()
    
    # Формируем сообщение для админа
    admin_text = (
        f"🔔 <b>Новый заказ на модерации!</b>\n\n"
        f"👤 <b>Пользователь:</b> {message.from_user.full_name}\n"
    )
    
    if message.from_user.username:
        admin_text += f"🆔 <b>Username:</b> @{message.from_user.username}\n"
    
    admin_text += (
        f"🆔 <b>ID:</b> {user.tg_id}\n\n"
        f"📦 <b>Товар:</b> {product_name}\n"
        f"💰 <b>Сумма кэшбэка:</b> {cashback_amount} ₽\n\n"
        f"📝 <b>Реквизиты:</b>\n{message.text}"
    )
    
    # Отправляем админам медиагруппу со всеми фото
    media_group = []
    
    if 'basket' in screenshots:
        media_group.append(InputMediaPhoto(
            media=screenshots['basket'],
            caption=admin_text if len(media_group) == 0 else None,
            parse_mode="HTML"
        ))
    
    if 'buy' in screenshots:
        media_group.append(InputMediaPhoto(
            media=screenshots['buy'],
            caption=admin_text if len(media_group) == 0 else None,
            parse_mode="HTML"
        ))
    
    if 'received' in screenshots:
        media_group.append(InputMediaPhoto(
            media=screenshots['received'],
            caption=admin_text if len(media_group) == 0 else None,
            parse_mode="HTML"
        ))
    
    if 'review' in screenshots:
        media_group.append(InputMediaPhoto(
            media=screenshots['review'],
            caption=admin_text if len(media_group) == 0 else None,
            parse_mode="HTML"
        ))
    
    # Отправляем всем админам
    for admin_id in settings.admin_ids:
        try:
            if media_group:
                await message.bot.send_media_group(
                    admin_id,
                    media=media_group
                )
            else:
                # Если почему-то нет фото, отправляем только текст
                await message.bot.send_message(
                    admin_id,
                    admin_text,
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления админу {admin_id}: {e}")
    
    await message.answer(
        "✅ <b>Спасибо!</b>\n\n"
        "Ваш заказ отправлен на модерацию. "
        "Мы свяжемся с вами в ближайшее время! 🙏",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )
    await state.clear()
    
    logger.info(f"Пользователь {user.tg_id} завершил заказ {order_id}")


# Проверка на неправильные сообщения
@router.message(ClientStates.WAITING_BASKET_SCREENSHOT)
@router.message(ClientStates.WAITING_BUY_SCREENSHOT)
@router.message(ClientStates.WAITING_RECEIVED_SCREENSHOT)
@router.message(ClientStates.WAITING_REVIEW_SCREENSHOT)
async def wrong_content_type(message: Message):
    """Обработка неправильного типа сообщения."""
    await message.delete()
    await message.answer(
        "❌ Пожалуйста, отправьте <b>скриншот</b> (фотографию).",
        parse_mode="HTML"
    )
