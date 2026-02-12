"""Обработчики для системы поддержки (диалоги пользователь-админ)."""
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
import logging

from bot.config import settings
from bot.states.client_states import SupportStates
from bot.keyboards.client_keyboards import get_support_menu, get_main_menu, get_main_menu_with_cancel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.database.models import Order, OrderStatus

logger = logging.getLogger(__name__)
router = Router(name='support')


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


async def get_user_state(bot: Bot, storage, user_id: int) -> FSMContext:
    """Получить FSMContext для другого пользователя."""
    return FSMContext(
        storage=storage,
        key=StorageKey(
            bot_id=bot.id,
            chat_id=user_id,
            user_id=user_id
        )
    )


# ========== ОБРАБОТЧИКИ CALLBACK ДЛЯ АДМИНОВ ==========

@router.callback_query(F.data.startswith("support_respond:"))
async def admin_respond(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Админ откликнулся на запрос поддержки."""
    user_id = int(callback.data.split(":")[1])
    admin_id = callback.from_user.id
    
    logger.info(f"[SUPPORT] Админ {admin_id} откликается на пользователя {user_id}")
    
    # Проверяем через Redis, не занят ли уже этот пользователь
    user_state = await get_user_state(callback.bot, state.storage, user_id)
    user_data = await user_state.get_data()
    
    if user_data.get('support_admin_id'):
        existing_admin = user_data['support_admin_id']
        if existing_admin != admin_id:
            logger.warning(f"[SUPPORT] Пользователь {user_id} уже занят админом {existing_admin}")
            await callback.answer(
                f"❌ На этого пользователя уже откликнулся другой админ!",
                show_alert=True
            )
            return
    
    # Устанавливаем состояние для админа
    await state.update_data(support_user_id=user_id)
    await state.set_state(SupportStates.ADMIN_IN_DIALOG)
    
    logger.info(f"[SUPPORT] Состояние админа {admin_id} установлено: support_user_id={user_id}")
    
    # Уведомляем админа
    await callback.message.edit_text(
        f"✅ Вы откликнулись на запрос!\n\n"
        f"Теперь все ваши сообщения будут пересылаться пользователю.\n"
        f"🔚 Используйте /end_support для завершения диалога."
    )
    
    # Уведомляем пользователя
    try:
        # Проверяем, есть ли активный заказ
        user_has_order = await has_active_order(session, user_id)
        
        await callback.bot.send_message(
            user_id,
            "✅ Оператор на связи!\n\n"
            "💬 Отправляйте свои сообщения здесь.\n"
            "🔚 Чтобы завершить диалог, нажмите кнопку ниже.",
            reply_markup=get_support_menu()
        )
        
        # Устанавливаем состояние для пользователя
        await user_state.set_state(SupportStates.USER_IN_DIALOG)
        await user_state.update_data(support_admin_id=admin_id)
        
        logger.info(f"[SUPPORT] Состояние пользователя {user_id} установлено: support_admin_id={admin_id}")
        
    except Exception as e:
        logger.error(f"[SUPPORT] Ошибка уведомления пользователя {user_id}: {e}")
        await callback.answer("❌ Ошибка связи с пользователем", show_alert=True)
        await state.clear()
        return
    
    await callback.answer("✅ Диалог начат")
    logger.info(f"[SUPPORT] Диалог начат: админ {admin_id} <-> пользователь {user_id}")


@router.callback_query(F.data.startswith("support_ignore:"))
async def admin_ignore(callback: CallbackQuery):
    """Админ игнорирует запрос."""
    user_id = callback.data.split(":")[1]
    logger.info(f"[SUPPORT] Админ {callback.from_user.id} игнорирует пользователя {user_id}")
    await callback.message.delete()
    await callback.answer("❌ Игнорировано")


# ========== ЗАВЕРШЕНИЕ ДИАЛОГА (ДОЛЖНО БЫТЬ ДО ПЕРЕСЫЛКИ СООБЩЕНИЙ!) ==========

@router.message(F.text.contains("Завершить диалог"), SupportStates.USER_IN_DIALOG)
async def user_end_dialog(message: Message, state: FSMContext, session: AsyncSession):
    """Пользователь завершает диалог."""
    data = await state.get_data()
    admin_id = data.get('support_admin_id')
    user_id = message.from_user.id
    
    logger.info(f"[SUPPORT] Пользователь {user_id} завершает диалог с админом {admin_id}")
    
    if not admin_id:
        await message.answer("❌ У вас нет активного диалога.")
        return
    
    # Очищаем состояния
    await state.clear()
    
    # Уведомляем админа
    try:
        admin_state = await get_user_state(message.bot, state.storage, admin_id)
        await admin_state.clear()
        
        await message.bot.send_message(
            admin_id,
            f"🔚 Пользователь (ID: {user_id}) завершил диалог."
        )
    except Exception as e:
        logger.error(f"[SUPPORT] Ошибка уведомления админа {admin_id}: {e}")
    
    # Проверяем, есть ли активный заказ
    user_has_order = await has_active_order(session, user_id)
    
    await message.answer(
        "✅ Диалог завершен. Спасибо за обращение!",
        reply_markup=get_main_menu_with_cancel() if user_has_order else get_main_menu()
    )
    logger.info(f"[SUPPORT] Диалог завершен пользователем {user_id}")


@router.message(F.text.startswith('/end_support'), SupportStates.ADMIN_IN_DIALOG)
async def end_support_command(message: Message, state: FSMContext):
    """Админ завершает диалог через команду."""
    data = await state.get_data()
    user_id = data.get('support_user_id')
    admin_id = message.from_user.id
    
    logger.info(f"[SUPPORT] Админ {admin_id} завершает диалог с пользователем {user_id}")
    
    if not user_id:
        await message.answer("❌ У вас нет активного диалога.")
        return
    
    # Очищаем состояния
    await state.clear()
    
    # Уведомляем пользователя
    try:
        user_state = await get_user_state(message.bot, state.storage, user_id)
        await user_state.clear()
        
        await message.bot.send_message(
            user_id,
            "🔚 Оператор завершил диалог. Спасибо за обращение!",
            reply_markup=get_main_menu()
        )
    except Exception as e:
        logger.error(f"[SUPPORT] Ошибка уведомления пользователя {user_id}: {e}")
    
    await message.answer("✅ Диалог завершен.")
    logger.info(f"[SUPPORT] Диалог завершен админом {admin_id}")


# ========== ПЕРЕСЫЛКА СООБЩЕНИЙ (ПОСЛЕ ОБРАБОТЧИКА ЗАВЕРШЕНИЯ!) ==========

@router.message(SupportStates.USER_IN_DIALOG)
async def user_message_in_dialog(message: Message, state: FSMContext):
    """Пересылка сообщений от пользователя к админу."""
    data = await state.get_data()
    admin_id = data.get('support_admin_id')
    
    logger.info(f"[SUPPORT] Сообщение от пользователя {message.from_user.id} -> админ {admin_id}")
    
    if not admin_id:
        logger.warning(f"[SUPPORT] Пользователь {message.from_user.id}: admin_id не найден в state")
        await message.answer("❌ Диалог не найден. Используйте кнопку Поддержка.")
        return
    
    try:
        # Пересылка любых типов сообщений
        prefix = f"👤 От пользователя (ID: {message.from_user.id}):\n\n"
        
        if message.text:
            await message.bot.send_message(admin_id, prefix + message.text)
            logger.info(f"[SUPPORT] Текст отправлен админу {admin_id}")
        elif message.photo:
            await message.bot.send_photo(
                admin_id,
                message.photo[-1].file_id,
                caption=prefix + (message.caption or "")
            )
        elif message.document:
            await message.bot.send_document(
                admin_id,
                message.document.file_id,
                caption=prefix + (message.caption or "")
            )
        elif message.voice:
            await message.bot.send_voice(
                admin_id,
                message.voice.file_id,
                caption=prefix
            )
        elif message.video:
            await message.bot.send_video(
                admin_id,
                message.video.file_id,
                caption=prefix + (message.caption or "")
            )
        elif message.sticker:
            await message.bot.send_sticker(admin_id, message.sticker.file_id)
            await message.bot.send_message(admin_id, prefix + "[Стикер]")
        else:
            await message.bot.send_message(admin_id, prefix + "[Неподдерживаемый тип сообщения]")
            
    except Exception as e:
        logger.error(f"[SUPPORT] Ошибка пересылки админу {admin_id}: {e}")
        await message.answer("❌ Ошибка отправки сообщения.")


@router.message(SupportStates.ADMIN_IN_DIALOG)
async def admin_message_in_dialog(message: Message, state: FSMContext):
    """Пересылка сообщений от админа к пользователю."""
    data = await state.get_data()
    user_id = data.get('support_user_id')
    admin_id = message.from_user.id
    
    logger.info(f"[SUPPORT] Сообщение от админа {admin_id} -> пользователь {user_id}")
    logger.info(f"[SUPPORT] Data админа: {data}")
    
    if not user_id:
        logger.warning(f"[SUPPORT] Админ {admin_id}: user_id не найден в state!")
        await message.answer("❌ Диалог не найден. Используйте /end_support и начните заново.")
        return
    
    try:
        # Пересылка любых типов сообщений
        prefix = "👨‍💻 Ответ оператора:\n\n"
        
        if message.text:
            await message.bot.send_message(user_id, prefix + message.text)
            logger.info(f"[SUPPORT] Текст отправлен пользователю {user_id}")
        elif message.photo:
            await message.bot.send_photo(
                user_id,
                message.photo[-1].file_id,
                caption=prefix + (message.caption or "")
            )
        elif message.document:
            await message.bot.send_document(
                user_id,
                message.document.file_id,
                caption=prefix + (message.caption or "")
            )
        elif message.voice:
            await message.bot.send_voice(
                user_id,
                message.voice.file_id,
                caption=prefix
            )
        elif message.video:
            await message.bot.send_video(
                user_id,
                message.video.file_id,
                caption=prefix + (message.caption or "")
            )
        elif message.sticker:
            await message.bot.send_sticker(user_id, message.sticker.file_id)
        else:
            logger.warning(f"[SUPPORT] Неподдерживаемый тип сообщения от админа {admin_id}")
            await message.answer("❌ Неподдерживаемый тип сообщения.")
            
    except Exception as e:
        logger.error(f"[SUPPORT] Ошибка пересылки пользователю {user_id}: {e}", exc_info=True)
        await message.answer("❌ Ошибка отправки сообщения.")
