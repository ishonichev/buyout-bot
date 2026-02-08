"""Обработчики для админ-панели."""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from bot.database.models import Product, Order, OrderStatus, User
from bot.keyboards.admin_keyboards import (
    get_admin_main_keyboard,
    get_products_list_keyboard,
    get_product_edit_keyboard
)
from bot.states.admin_states import AdminStates
from bot.config import settings

logger = logging.getLogger(__name__)
router = Router(name='admin')


# Фильтр для проверки админа
def is_admin(user_id: int) -> bool:
    return user_id == settings.ADMIN_ID


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Открыть админ-панель."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    await message.answer(
        "🔑 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_admin_main_keyboard()
    )


@router.callback_query(F.data == "admin:products")
async def admin_products(callback: CallbackQuery, session: AsyncSession):
    """Список товаров."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    result = await session.execute(select(Product).order_by(Product.id))
    products = result.scalars().all()
    
    await callback.message.edit_text(
        "📝 <b>Управление товарами</b>\n\nВыберите товар для редактирования:",
        reply_markup=get_products_list_keyboard(products)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:edit_product:"))
async def edit_product(callback: CallbackQuery, session: AsyncSession):
    """Открыть редактирование товара."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    product_id = int(callback.data.split(":")[2])
    
    result = await session.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    
    status = "✅ Активен" if product.is_active else "❌ Неактивен"
    
    text = (
        f"✏️ <b>Редактирование товара</b>\n\n"
        f"🏷 <b>Название:</b> {product.name}\n"
        f"🔗 <b>Ссылка:</b> {product.url[:50] if product.url else 'не установлена'}...\n"
        f"💰 <b>Кэшбэк:</b> {product.cashback_amount} ₽\n"
        f"🟢 <b>Статус:</b> {status}"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_product_edit_keyboard(product_id, product.is_active)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:edit:"))
async def start_edit_field(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование поля."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    parts = callback.data.split(":")
    field = parts[2]
    product_id = int(parts[3])
    
    await state.update_data(product_id=product_id)
    
    messages = {
        "name": "✏️ Отправьте новое название товара:",
        "url": "🔗 Отправьте новую ссылку на товар:",
        "cashback": "💰 Отправьте сумму кэшбэка (только цифры):",
        "instruction": "📝 Отправьте новую инструкцию:"
    }
    
    states_map = {
        "name": AdminStates.EDIT_PRODUCT_NAME,
        "url": AdminStates.EDIT_PRODUCT_URL,
        "cashback": AdminStates.EDIT_PRODUCT_CASHBACK,
        "instruction": AdminStates.EDIT_PRODUCT_INSTRUCTION
    }
    
    await state.set_state(states_map[field])
    await callback.message.answer(messages[field])
    await callback.answer()


@router.message(AdminStates.EDIT_PRODUCT_NAME)
async def save_product_name(message: Message, state: FSMContext, session: AsyncSession):
    """Сохранить новое название."""
    data = await state.get_data()
    product_id = data.get('product_id')
    
    result = await session.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    
    if product:
        product.name = message.text
        await session.commit()
        await message.answer(f"✅ Название изменено на: {message.text}")
    
    await state.clear()


@router.message(AdminStates.EDIT_PRODUCT_URL)
async def save_product_url(message: Message, state: FSMContext, session: AsyncSession):
    """Сохранить новую ссылку."""
    data = await state.get_data()
    product_id = data.get('product_id')
    
    result = await session.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    
    if product:
        product.url = message.text
        await session.commit()
        await message.answer(f"✅ Ссылка изменена")
    
    await state.clear()


@router.message(AdminStates.EDIT_PRODUCT_CASHBACK)
async def save_product_cashback(message: Message, state: FSMContext, session: AsyncSession):
    """Сохранить сумму кэшбэка."""
    try:
        cashback = int(message.text)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число.")
        return
    
    data = await state.get_data()
    product_id = data.get('product_id')
    
    result = await session.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    
    if product:
        product.cashback_amount = cashback
        await session.commit()
        await message.answer(f"✅ Сумма кэшбэка изменена на: {cashback} ₽")
    
    await state.clear()


@router.message(AdminStates.EDIT_PRODUCT_INSTRUCTION)
async def save_product_instruction(message: Message, state: FSMContext, session: AsyncSession):
    """Сохранить инструкцию."""
    data = await state.get_data()
    product_id = data.get('product_id')
    
    result = await session.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    
    if product:
        product.instruction_text = message.text
        await session.commit()
        await message.answer("✅ Инструкция обновлена")
    
    await state.clear()


@router.callback_query(F.data.startswith("admin:toggle:"))
async def toggle_product(callback: CallbackQuery, session: AsyncSession):
    """Переключить статус товара."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    product_id = int(callback.data.split(":")[2])
    
    result = await session.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    
    if product:
        product.is_active = not product.is_active
        await session.commit()
        
        status = "✅ Активирован" if product.is_active else "❌ Деактивирован"
        await callback.answer(f"Товар {status}", show_alert=True)
        
        # Обновляем клавиатуру
        text = (
            f"✏️ <b>Редактирование товара</b>\n\n"
            f"🏷 <b>Название:</b> {product.name}\n"
            f"🔗 <b>Ссылка:</b> {product.url[:50] if product.url else 'не установлена'}...\n"
            f"💰 <b>Кэшбэк:</b> {product.cashback_amount} ₽\n"
            f"🟢 <b>Статус:</b> {✅ if product.is_active else ❌}"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_product_edit_keyboard(product_id, product.is_active)
        )


@router.callback_query(F.data == "admin:back")
async def admin_back(callback: CallbackQuery):
    """Возврат в главное меню админки."""
    await callback.message.edit_text(
        "🔑 <b>Админ-панель</b>\n\nВыберите действие:",
        reply_markup=get_admin_main_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:approve:"))
async def approve_review(callback: CallbackQuery, session: AsyncSession):
    """Одобрить отзыв."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    order_id = int(callback.data.split(":")[2])
    
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if order:
        order.status = OrderStatus.COMPLETED
        order.review_date = datetime.now()
        await session.commit()
        
        # Уведомляем пользователя
        try:
            await callback.bot.send_message(
                order.user_id,
                "✅ <b>Отличные новости!</b>\n\n"
                "Ваш отзыв одобрен! Кэшбэк будет перечислен в ближайшее время. 🙏"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {e}")
        
        await callback.message.edit_text(
            f"{callback.message.text}\n\n✅ <b>Отзыв одобрен</b>"
        )
        await callback.answer("✅ Отзыв одобрен")


@router.callback_query(F.data.startswith("admin:reject:"))
async def reject_review(callback: CallbackQuery, session: AsyncSession):
    """Отклонить отзыв."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    order_id = int(callback.data.split(":")[2])
    
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    
    if order:
        order.status = OrderStatus.CANCELLED
        await session.commit()
        
        try:
            await callback.bot.send_message(
                order.user_id,
                "❌ К сожалению, ваш отзыв не прошел модерацию. "
                "Пожалуйста, свяжитесь с нами для уточнения деталей."
            )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {e}")
        
        await callback.message.edit_text(
            f"{callback.message.text}\n\n❌ <b>Отзыв отклонен</b>"
        )
        await callback.answer("❌ Отзыв отклонен")
