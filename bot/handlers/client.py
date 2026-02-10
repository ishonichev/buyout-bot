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
    get_agreement_keyboard,
    get_process_keyboard
)
from bot.states.client_states import ClientStates
from bot.config import settings

logger = logging.getLogger(__name__)
router = Router(name='client')


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, user: User):
    """Обработка команды /start."""
    # Аналитика: Зашли в бот
    event = AnalyticsEvent(user_id=user.tg_id, event_type="bot_visited")
    session.add(event)
    
    # Аналитика: Запустили бот
    event2 = AnalyticsEvent(user_id=user.tg_id, event_type="bot_started")
    session.add(event2)
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
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )
    logger.info(f"Пользователь {user.tg_id} запустил бота")


@router.message(F.text == "🛋️ Выбрать товар")
async def select_product(message: Message, session: AsyncSession, user: User):
    """Выбор товара."""
    # Аналитика: Кнопка 1 - "Выбрать товар"
    event = AnalyticsEvent(user_id=user.tg_id, event_type="button_1")
    session.add(event)
    await session.commit()
    
    # Получаем все товары
    result = await session.execute(select(Product).order_by(Product.id))
    products = result.scalars().all()
    
    await message.answer(
        "🛋️ <b>Выберите товар для выкупа:</b>",
        reply_markup=get_products_keyboard(products),
        parse_mode="HTML"
    )


@router.message(F.text == "❓ Есть вопросы")
async def ask_question(message: Message, user: User, session: AsyncSession):
    """Обработка вопросов пользователя."""
    # Уведомляем админов
    admin_text = (
        f"👤 <b>Пользователь просит помощи!</b>\n\n"
        f"🆔 <b>ID:</b> {user.tg_id}\n"
        f"👤 <b>Имя:</b> {message.from_user.full_name}\n"
    )
    
    if message.from_user.username:
        admin_text += f"🆔 <b>Username:</b> @{message.from_user.username}\n"
    
    for admin_id in settings.admin_ids:
        try:
            await message.bot.send_message(
                admin_id,
                admin_text,
                parse_mode="HTML"
            )
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
async def buy_product(callback: CallbackQuery, session: AsyncSession, user: User, state: FSMContext):
    """Начало процесса выкупа."""
    product_id = int(callback.data.split(":")[1])
    
    # Аналитика: Кнопка 2 - Выбор конкретного товара
    event = AnalyticsEvent(user_id=user.tg_id, event_type="button_2")
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
    
    # Сохраняем данные в состояние
    await state.update_data(
        order_id=order.id,
        product_id=product.id,
        product_name=product.name,
        cashback_amount=product.cashback_amount,
        screenshots={}
    )
    
    # Отправляем инструкцию
    instruction_text = (
        f"📜 <b>Инструкция по выкупу \"{product.name}\"</b>\n\n"
        f"{product.instruction_text}\n\n"
        f"💰 <b>Кэшбэк:</b> {product.cashback_amount} ₽"
    )
    
    await callback.message.delete()
    await callback.message.answer(
        instruction_text,
        reply_markup=get_agreement_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()
    
    logger.info(f"Пользователь {user.tg_id} начал выкуп товара {product.name}")


@router.message(F.text == "✅ Я согласен")
async def agree_instruction(message: Message, state: FSMContext, session: AsyncSession, user: User):
    """Пользователь согласился с инструкцией."""
    data = await state.get_data()
    
    if not data.get('order_id'):
        await message.answer("❌ Сначала выберите товар")
        return
    
    # Аналитика: Кнопка 3
    event = AnalyticsEvent(user_id=user.tg_id, event_type="button_3")
    session.add(event)
    await session.commit()
    
    await state.set_state(ClientStates.WAITING_BASKET_SCREENSHOT)
    
    await message.answer(
        "✅ <b>Отлично!</b>\n\n"
        "📸 Отправьте <b>скриншот товара в корзине</b>",
        reply_markup=get_process_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "❌ Отменить прогресс")
async def cancel_progress(message: Message, state: FSMContext, session: AsyncSession, user: User):
    """Отмена текущего заказа."""
    data = await state.get_data()
    order_id = data.get('order_id')
    
    if order_id:
        # Отменяем заказ
        result = await session.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if order:
            order.status = OrderStatus.CANCELLED
            await session.commit()
    
    await state.clear()
    
    await message.answer(
        "❌ Заказ отменен.\n\n"
        "Вы можете выбрать другой товар или обратиться к оператору.",
        reply_markup=get_main_menu()
    )
    
    logger.info(f"Пользователь {user.tg_id} отменил заказ {order_id}")
