"""Обработчики для системы поддержки (диалоги пользователь-админ)."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
import logging
from typing import Dict

from bot.config import settings
from bot.states.client_states import SupportStates
from bot.keyboards.client_keyboards import get_support_menu, get_main_menu, get_main_menu_with_cancel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.database.models import Order, OrderStatus

logger = logging.getLogger(__name__)
router = Router(name='support')

# Хранилище активных диалогов (в продакшене лучше использовать Redis)
# Формат: {user_id: admin_id}
active_dialogs: Dict[int, int] = {}


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


# ========== ОБРАБОТЧИКИ CALLBACK ДЛЯ АДМИНОВ ==========

@router.callback_query(F.data.startswith("support_respond:"))
async def admin_respond(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Админ откликнулся на запрос поддержки."""
    user_id = int(callback.data.split(":")[1])
    admin_id = callback.from_user.id
    
    # Проверяем, не занят ли уже этот пользователь
    if user_id in active_dialogs:
        existing_admin = active_dialogs[user_id]
        if existing_admin != admin_id:
            await callback.answer(
                f"❌ На этого пользователя уже откликнулся другой админ!",
                show_alert=True
            )
            return
    
    # Создаем диалог
    active_dialogs[user_id] = admin_id
    
    # Устанавливаем состояние для админа
    await state.update_data(support_user_id=user_id)
    await state.set_state(SupportStates.ADMIN_IN_DIALOG)
    
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
        
        # Устанавливаем состояние для пользователя (через его FSM storage)
        user_state = FSMContext(
            bot=callback.bot,
            storage=state.storage,
            key=state.key.__class__(
                bot_id=state.key.bot_id,
                chat_id=user_id,
                user_id=user_id
            )
        )
        await user_state.set_state(SupportStates.USER_IN_DIALOG)
        await user_state.update_data(support_admin_id=admin_id)
        
    except Exception as e:
        logger.error(f"Ошибка уведомления пользователя: {e}")
        await callback.answer("❌ Ошибка связи с пользователем", show_alert=True)
        del active_dialogs[user_id]
        return
    
    await callback.answer("✅ Диалог начат")
    logger.info(f"Админ {admin_id} откликнулся на пользователя {user_id}")


@router.callback_query(F.data.startswith("support_ignore:"))
async def admin_ignore(callback: CallbackQuery):
    """Админ игнорирует запрос."""
    await callback.message.delete()
    await callback.answer("❌ Игнорировано")


# ========== ПЕРЕСЫЛКА СООБЩЕНИЙ ==========

@router.message(SupportStates.USER_IN_DIALOG)
async def user_message_in_dialog(message: Message, state: FSMContext):
    """Пересылка сообщений от пользователя к админу."""
    data = await state.get_data()
    admin_id = data.get('support_admin_id')
    
    if not admin_id:
        await message.answer("❌ Диалог не найден. Используйте кнопку Поддержка.")
        return
    
    try:
        # Пересылка любых типов сообщений
        prefix = f"👤 От пользователя (ID: {message.from_user.id}):\n\n"
        
        if message.text:
            await message.bot.send_message(admin_id, prefix + message.text)
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
        logger.error(f"Ошибка пересылки админу: {e}")
        await message.answer("❌ Ошибка отправки сообщения.")


@router.message(SupportStates.ADMIN_IN_DIALOG)
async def admin_message_in_dialog(message: Message, state: FSMContext):
    """Пересылка сообщений от админа к пользователю."""
    # Проверяем команду завершения
    if message.text and message.text.startswith('/end_support'):
        await end_support_command(message, state)
        return
    
    data = await state.get_data()
    user_id = data.get('support_user_id')
    
    if not user_id:
        await message.answer("❌ Диалог не найден.")
        return
    
    try:
        # Пересылка любых типов сообщений
        prefix = "👨‍💻 Ответ оператора:\n\n"
        
        if message.text:
            await message.bot.send_message(user_id, prefix + message.text)
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
            await message.answer("❌ Неподдерживаемый тип сообщения.")
            
    except Exception as e:
        logger.error(f"Ошибка пересылки пользователю: {e}")
        await message.answer("❌ Ошибка отправки сообщения.")


# ========== ЗАВЕРШЕНИЕ ДИАЛОГА ==========

@router.message(F.text.contains("Завершить диалог"))
async def user_end_dialog(message: Message, state: FSMContext, session: AsyncSession):
    """Пользователь завершает диалог."""
    data = await state.get_data()
    admin_id = data.get('support_admin_id')
    user_id = message.from_user.id
    
    if admin_id and user_id in active_dialogs:
        # Удаляем диалог
        del active_dialogs[user_id]
        
        # Очищаем состояния
        await state.clear()
        
        # Уведомляем админа
        try:
            admin_state = FSMContext(
                bot=message.bot,
                storage=state.storage,
                key=state.key.__class__(
                    bot_id=state.key.bot_id,
                    chat_id=admin_id,
                    user_id=admin_id
                )
            )
            await admin_state.clear()
            
            await message.bot.send_message(
                admin_id,
                f"🔚 Пользователь (ID: {user_id}) завершил диалог."
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления админа: {e}")
        
        # Проверяем, есть ли активный заказ
        user_has_order = await has_active_order(session, user_id)
        
        await message.answer(
            "✅ Диалог завершен. Спасибо за обращение!",
            reply_markup=get_main_menu_with_cancel() if user_has_order else get_main_menu()
        )
        logger.info(f"Пользователь {user_id} завершил диалог с админом {admin_id}")
    else:
        await message.answer("❌ У вас нет активного диалога.")


async def end_support_command(message: Message, state: FSMContext):
    """Админ завершает диалог через команду."""
    data = await state.get_data()
    user_id = data.get('support_user_id')
    admin_id = message.from_user.id
    
    if user_id and user_id in active_dialogs:
        # Удаляем диалог
        del active_dialogs[user_id]
        
        # Очищаем состояния
        await state.clear()
        
        # Уведомляем пользователя
        try:
            user_state = FSMContext(
                bot=message.bot,
                storage=state.storage,
                key=state.key.__class__(
                    bot_id=state.key.bot_id,
                    chat_id=user_id,
                    user_id=user_id
                )
            )
            await user_state.clear()
            
            await message.bot.send_message(
                user_id,
                "🔚 Оператор завершил диалог. Спасибо за обращение!",
                reply_markup=get_main_menu()
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления пользователя: {e}")
        
        await message.answer("✅ Диалог завершен.")
        logger.info(f"Админ {admin_id} завершил диалог с пользователем {user_id}")
    else:
        await message.answer("❌ У вас нет активного диалога.")
