"""Новые админ-хэндлеры (только модерация заказов)."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
from datetime import datetime

from bot.database.models import Order, OrderStatus, User, BotConfig
from bot.keyboards.admin_keyboards import get_admin_menu, get_webapp_keyboard
from bot.states.admin_states import AdminStates
from bot.config import settings
from bot.services.sheets_service import SheetsService

logger = logging.getLogger(__name__)
router = Router(name='admin_new')


async def get_config_text(session: AsyncSession, key: str) -> str:
    """Получить текст из конфига."""
    result = await session.execute(
        select(BotConfig).where(BotConfig.config_key == key)
    )
    config = result.scalar_one_or_none()
    return config.config_value if config else "Не настроено"


@router.message(Command("admin"))
async def admin_menu(message: Message):
    """Админ-панель."""
    if message.from_user.id not in settings.admin_ids_list:
        return
    
    await message.answer(
        "🛠 Админ-панель\n\n"
        "📝 Для управления товарами и текстами - откройте веб-панель\n"
        "✅ Здесь вы можете модерировать заказы",
        reply_markup=get_webapp_keyboard()
    )


@router.callback_query(F.data.startswith("admin:approve:"))
async def approve_order(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Подтвердить заказ - просим скрин перевода."""
    order_id = int(callback.data.split(":")[2])
    
    # Сохраняем order_id
    await state.update_data(approving_order_id=order_id)
    await state.set_state(AdminStates.WAITING_PAYMENT_SCREENSHOT)
    
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "💸 Отлично! Теперь пришлите скриншот перевода кэшбэка:"
    )
    await callback.answer()


@router.message(AdminStates.WAITING_PAYMENT_SCREENSHOT, F.photo)
async def payment_screenshot(message: Message, state: FSMContext, session: AsyncSession, sheets_service: SheetsService):
    """Скриншот перевода получен."""
    data = await state.get_data()
    order_id = data.get('approving_order_id')
    
    # Обновляем заказ
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if not order:
        await message.answer("❌ Заказ не найден")
        await state.clear()
        return
    
    # Обновляем статус
    order.status = OrderStatus.COMPLETED
    await session.commit()
    
    # Получаем данные пользователя
    user_result = await session.execute(
        select(User).where(User.tg_id == order.user_id)
    )
    user = user_result.scalar_one_or_none()
    username = f"@{user.username}" if user and user.username else "Неизвестно"
    
    # ЗАПИСЫВАЕМ В GOOGLE SHEETS (ЛИСТ1)
    if sheets_service:
        order_data = {
            "order_id": order.id,
            "username": username,
            "basket_date": order.basket_date,
            "buy_date": order.buy_date,
            "received_date": order.received_date,
            "review_date": order.review_date,
            "cashback_amount": 0  # Теперь сумма в инструкции
        }
        await sheets_service.add_order_to_sheet1(order_data)
    
    # Отправляем пользователю
    payment_text = await get_config_text(session, "payment_sent_message")
    
    try:
        await message.bot.send_photo(
            order.user_id,
            message.photo[-1].file_id,
            caption=payment_text
        )
    except Exception as e:
        logger.error(f"Ошибка отправки пользователю: {e}")
    
    await message.answer(
        f"✅ Заказ #{order_id} одобрен и записан в Google Sheets!\n"
        f"Пользователь {username} получил уведомление."
    )
    
    await state.clear()
    logger.info(f"Заказ #{order_id} завершен")


@router.callback_query(F.data.startswith("admin:reject:"))
async def reject_order(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Отклонить заказ - просим причину."""
    order_id = int(callback.data.split(":")[2])
    
    await state.update_data(rejecting_order_id=order_id)
    await state.set_state(AdminStates.WAITING_REJECTION_REASON)
    
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "❌ Напишите причину отклонения:"
    )
    await callback.answer()


@router.message(AdminStates.WAITING_REJECTION_REASON, F.text)
async def rejection_reason(message: Message, state: FSMContext, session: AsyncSession):
    """Причина отклонения получена."""
    data = await state.get_data()
    order_id = data.get('rejecting_order_id')
    
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if not order:
        await message.answer("❌ Заказ не найден")
        await state.clear()
        return
    
    # Обновляем статус
    order.status = OrderStatus.REJECTED
    order.rejection_reason = message.text
    await session.commit()
    
    # Отправляем пользователю
    try:
        await message.bot.send_message(
            order.user_id,
            f"❌ Ваш заказ отклонен\n\n"
            f"📝 Причина: {message.text}"
        )
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")
    
    await message.answer(
        f"✅ Заказ #{order_id} отклонен.\n"
        f"Пользователь получил уведомление."
    )
    
    await state.clear()
    logger.info(f"Заказ #{order_id} отклонен: {message.text}")
