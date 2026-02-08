"""Обработка скриншотов от клиентов."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import logging

from bot.database.models import User, Order, OrderStatus, AnalyticsEvent, Product
from bot.keyboards.client_keyboards import get_confirm_screenshot_keyboard
from bot.states.client_states import ClientStates
from bot.config import settings

logger = logging.getLogger(__name__)
router = Router(name='client_screenshots')


@router.callback_query(F.data == "agree_instruction")
async def agree_instruction(callback: CallbackQuery, session: AsyncSession, user: User, state: FSMContext):
    """Пользователь согласился с инструкцией."""
    # Аналитика: Кнопка 3
    event = AnalyticsEvent(user_id=user.tg_id, event_type="button_3")
    session.add(event)
    await session.commit()
    
    await callback.message.answer(
        "✅ Отлично! Теперь давайте пройдем по этапам.",
        reply_markup=get_confirm_screenshot_keyboard("basket")
    )
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data.startswith("send_screenshot:"))
async def request_screenshot(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User):
    """Запрос на отправку скриншота."""
    step = callback.data.split(":")[1]
    
    # Аналитика
    button_map = {
        "basket": "button_4",
        "buy": "button_5",
        "received": "button_6",
        "review": "button_7"
    }
    event = AnalyticsEvent(user_id=user.tg_id, event_type=button_map.get(step, "unknown"))
    session.add(event)
    await session.commit()
    
    messages = {
        "basket": "📸 Отправьте скриншот товара в корзине:",
        "buy": "📸 Отправьте скриншот покупки:",
        "received": "📸 Отправьте скриншот товара на руках:",
        "review": "📸 Отправьте скриншот опубликованного отзыва:"
    }
    
    states_map = {
        "basket": ClientStates.WAITING_BASKET_SCREENSHOT,
        "buy": ClientStates.WAITING_BUY_SCREENSHOT,
        "received": ClientStates.WAITING_RECEIVED_SCREENSHOT,
        "review": ClientStates.WAITING_REVIEW_SCREENSHOT
    }
    
    await state.set_state(states_map[step])
    await callback.message.answer(messages[step])
    await callback.message.delete()
    await callback.answer()


@router.message(ClientStates.WAITING_BASKET_SCREENSHOT, F.photo)
async def basket_screenshot_received(message: Message, state: FSMContext, session: AsyncSession, user: User):
    """Получен скриншот корзины."""
    data = await state.get_data()
    order_id = data.get('order_id')
    
    # Обновляем заказ
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if order:
        order.basket_date = datetime.now()
        order.status = OrderStatus.BASKET_SENT
        await session.commit()
    
    await message.answer(
        "✅ Скриншот корзины принят! Следующий этап:",
        reply_markup=get_confirm_screenshot_keyboard("buy")
    )
    await state.set_state(None)


@router.message(ClientStates.WAITING_BUY_SCREENSHOT, F.photo)
async def buy_screenshot_received(message: Message, state: FSMContext, session: AsyncSession, user: User):
    """Получен скриншот покупки."""
    data = await state.get_data()
    order_id = data.get('order_id')
    product_id = data.get('product_id')
    cashback_amount = data.get('cashback_amount', 0)
    
    # Обновляем заказ
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if order:
        order.buy_date = datetime.now()
        order.status = OrderStatus.BUY_SENT
        await session.commit()
    
    # Записываем в Google Sheets (Лист 1)
    sheets_service = message.bot.get('sheets_service')
    if sheets_service:
        await sheets_service.add_order_to_sheet1({
            'order_id': order_id,
            'username': message.from_user.username or message.from_user.full_name,
            'basket_date': order.basket_date,
            'buy_date': order.buy_date,
            'cashback_amount': cashback_amount
        })
    
    await message.answer(
        "✅ Скриншот покупки принят! Следующий этап:",
        reply_markup=get_confirm_screenshot_keyboard("received")
    )
    await state.set_state(None)


@router.message(ClientStates.WAITING_RECEIVED_SCREENSHOT, F.photo)
async def received_screenshot(message: Message, state: FSMContext, session: AsyncSession, user: User):
    """Получен скриншот товара на руках."""
    data = await state.get_data()
    order_id = data.get('order_id')
    
    # Обновляем заказ
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if order:
        order.received_date = datetime.now()
        order.status = OrderStatus.RECEIVED
        await session.commit()
    
    review_text = (
        "👍 Отлично!\n\n"
        "📝 <b>Добрый день!</b>\n\n"
        "Отзыв <b>ЗАВТРА</b> на карточку:\n"
        "⭐️ 5 звезд <b>БЕЗ ТЕКСТА И ФОТО</b>\n\n"
        "После подтверждения модерации пришлите, пожалуйста:\n"
        "• Скриншот опубликованного отзыва\n"
        "• Ваше имя на WB\n"
        "• Куда отправить кэшбэк"
    )
    
    await message.answer(
        review_text,
        reply_markup=get_confirm_screenshot_keyboard("review")
    )
    await state.set_state(None)


@router.message(ClientStates.WAITING_REVIEW_SCREENSHOT, F.photo)
async def review_screenshot_received(message: Message, state: FSMContext, session: AsyncSession, user: User):
    """Получен скриншот отзыва - отправляем на модерацию."""
    data = await state.get_data()
    order_id = data.get('order_id')
    
    # Обновляем заказ
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if order:
        order.status = OrderStatus.REVIEW_MODERATION
        await session.commit()
    
    # Просим указать реквизиты
    await message.answer(
        "✅ Скриншот отзыва получен!\n\n"
        "📝 Теперь укажите:\n"
        "• Ваше имя на WildBerries\n"
        "• Реквизиты для перевода кэшбэка\n\n"
        "Например: <i>Иван Иванов, +79001234567</i>"
    )
    await state.set_state(ClientStates.WAITING_PAYMENT_DETAILS)


@router.message(ClientStates.WAITING_PAYMENT_DETAILS, F.text)
async def payment_details_received(message: Message, state: FSMContext, session: AsyncSession, user: User):
    """Получены реквизиты - отправляем админу."""
    data = await state.get_data()
    order_id = data.get('order_id')
    
    # Обновляем заказ
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if order:
        order.payment_details = message.text
        await session.commit()
    
    # Отправляем уведомление админу
    from bot.keyboards.admin_keyboards import get_review_moderation_keyboard
    
    # Получаем инфо о товаре
    result = await session.execute(select(Product).where(Product.id == order.product_id))
    product = result.scalar_one_or_none()
    
    admin_text = (
        f"🔔 <b>Новый отзыв на модерации!</b>\n\n"
        f"👤 Пользователь: {message.from_user.full_name}\n"
        f"🆔 Username: @{message.from_user.username or 'нет'}\n"
        f"🆔 ID: {user.tg_id}\n\n"
        f"📦 Товар: {product.name if product else 'Неизвестно'}\n"
        f"💰 Сумма кэшбэка: {data.get('cashback_amount', 0)} ₽\n\n"
        f"📝 Реквизиты:\n{message.text}"
    )
    
    for moderator_id in settings.moderator_ids:
        try:
            await message.bot.send_message(
                moderator_id,
                admin_text,
                reply_markup=get_review_moderation_keyboard(order_id, user.tg_id)
            )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления модератору {moderator_id}: {e}")
    
    await message.answer(
        "✅ <b>Спасибо!</b>\n\n"
        "Ваш отзыв отправлен на модерацию. "
        "Мы свяжемся с вами в ближайшее время! 🙏"
    )
    await state.clear()


# Проверка на неправильные сообщения
@router.message(ClientStates.WAITING_BASKET_SCREENSHOT)
@router.message(ClientStates.WAITING_BUY_SCREENSHOT)
@router.message(ClientStates.WAITING_RECEIVED_SCREENSHOT)
@router.message(ClientStates.WAITING_REVIEW_SCREENSHOT)
async def wrong_content_type(message: Message):
    """Обработка неправильного типа сообщения."""
    await message.delete()
    await message.answer(
        "❌ Пожалуйста, отправьте <b>скриншот</b> (фотографию)."
    )
