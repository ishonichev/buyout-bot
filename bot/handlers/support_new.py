"""Новая система поддержки с откликами админов."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import logging

from bot.states.client_states import SupportStates
from bot.states.admin_states import AdminStates
from bot.keyboards.client_keyboards import get_support_menu, get_main_menu, get_support_admin_keyboard
from bot.config import settings

logger = logging.getLogger(__name__)
router = Router(name='support_new')

# Словарь для хранения активных диалогов {user_id: admin_id}
active_dialogs = {}


@router.message(F.text.contains("Поддержка"))
async def start_support(message: Message, state: FSMContext):
    """Начало диалога с поддержкой."""
    user_id = message.from_user.id
    
    # Проверяем, есть ли уже активный диалог
    if user_id in active_dialogs:
        await message.answer(
            "💬 Вы уже в диалоге с поддержкой!\n"
            "Используйте кнопку 'Завершить диалог' для завершения."
        )
        return
    
    # Устанавливаем состояние ожидания отклика
    await state.set_state(SupportStates.CHATTING_WITH_USER)
    
    await message.answer(
        "💬 Вы обратились в поддержку.\n\n"
        "Опишите ваш вопрос или проблему, и оператор скоро с вами свяжется. 👨‍💻",
        reply_markup=get_support_menu()
    )
    
    # Отправляем уведомление всем админам
    username = f"@{message.from_user.username}" if message.from_user.username else "не указан"
    full_name = message.from_user.full_name or "Неизвестный"
    
    admin_text = (
        f"🔔 Новый запрос в поддержку!\n\n"
        f"🆔 ID: {user_id}\n"
        f"👤 Имя: {full_name}\n"
        f"🆔 Username: {username}\n\n"
        f"💬 Пользователь ожидает ответа..."
    )
    
    for admin_id in settings.admin_ids:
        try:
            await message.bot.send_message(
                admin_id,
                admin_text,
                reply_markup=get_support_admin_keyboard(user_id)
            )
        except Exception as e:
            logger.error(f"Ошибка отправки админу {admin_id}: {e}")


@router.callback_query(F.data.startswith("support_respond:"))
async def admin_respond(callback: CallbackQuery, state: FSMContext):
    """Админ откликнулся на запрос."""
    admin_id = callback.from_user.id
    user_id = int(callback.data.split(":")[1])
    
    # Проверяем, не занят ли уже этот диалог
    if user_id in active_dialogs:
        await callback.answer(
            "❌ Этот пользователь уже в диалоге с другим админом!",
            show_alert=True
        )
        return
    
    # Создаем диалог
    active_dialogs[user_id] = admin_id
    
    # Устанавливаем состояние для админа
    await state.set_state(AdminStates.CHATTING_WITH_USER)
    await state.update_data(support_user_id=user_id)
    
    # Удаляем кнопки у всех админов
    await callback.message.edit_reply_markup(reply_markup=None)
    
    # Уведомляем админа
    admin_menu = get_support_menu()
    await callback.message.answer(
        f"✅ Вы начали диалог с пользователем {user_id}.\n\n"
        f"💬 Все ваши сообщения будут пересланы пользователю.",
        reply_markup=admin_menu
    )
    
    # Уведомляем пользователя
    try:
        await callback.bot.send_message(
            user_id,
            "✅ Оператор подключился к диалогу!\n\n"
            "💬 Опишите вашу проблему или вопрос."
        )
    except Exception as e:
        logger.error(f"Ошибка уведомления пользователя {user_id}: {e}")
    
    await callback.answer()


@router.callback_query(F.data.startswith("support_ignore:"))
async def admin_ignore(callback: CallbackQuery):
    """Админ игнорирует запрос."""
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("❌ Запрос игнорирован")


@router.message(F.text.contains("Завершить диалог"))
async def end_support_dialog(message: Message, state: FSMContext):
    """Завершение диалога (для обеих сторон)."""
    user_id = message.from_user.id
    
    # Проверяем, кто завершает диалог
    is_user = user_id in active_dialogs
    is_admin = user_id in active_dialogs.values()
    
    if not is_user and not is_admin:
        await message.answer("❌ У вас нет активного диалога.")
        return
    
    # Находим пару
    if is_user:
        admin_id = active_dialogs[user_id]
        del active_dialogs[user_id]
        other_id = admin_id
    else:
        # Админ завершает
        user_id_in_dialog = next((uid for uid, aid in active_dialogs.items() if aid == user_id), None)
        if user_id_in_dialog:
            del active_dialogs[user_id_in_dialog]
            other_id = user_id_in_dialog
        else:
            await message.answer("❌ Диалог не найден.")
            return
    
    # Очищаем состояния
    await state.clear()
    
    # Уведомляем обе стороны
    await message.answer(
        "✅ Диалог завершен.\n\n"
        "Спасибо за обращение! 🙏",
        reply_markup=get_main_menu()
    )
    
    try:
        await message.bot.send_message(
            other_id,
            "✅ Диалог завершен.",
            reply_markup=get_main_menu()
        )
    except Exception as e:
        logger.error(f"Ошибка уведомления: {e}")


# Пересылка сообщений от пользователя
@router.message(SupportStates.CHATTING_WITH_USER)
async def forward_user_message(message: Message):
    """Пересылка сообщения от пользователя админу."""
    user_id = message.from_user.id
    
    if user_id not in active_dialogs:
        await message.answer(
            "❌ Диалог завершен или не найден.\n"
            "Нажмите 'Поддержка' чтобы начать снова.",
            reply_markup=get_main_menu()
        )
        return
    
    admin_id = active_dialogs[user_id]
    
    try:
        # Пересылаем сообщение админу
        prefix = f"👤 От пользователя {user_id}:\n\n"
        
        if message.text:
            await message.bot.send_message(admin_id, prefix + message.text)
        elif message.photo:
            await message.bot.send_photo(admin_id, message.photo[-1].file_id, caption=prefix + (message.caption or ""))
        elif message.document:
            await message.bot.send_document(admin_id, message.document.file_id, caption=prefix + (message.caption or ""))
        elif message.voice:
            await message.bot.send_voice(admin_id, message.voice.file_id, caption=prefix)
        elif message.video:
            await message.bot.send_video(admin_id, message.video.file_id, caption=prefix + (message.caption or ""))
        else:
            await message.bot.send_message(admin_id, prefix + "[Неподдерживаемый тип сообщения]")
    except Exception as e:
        logger.error(f"Ошибка пересылки админу {admin_id}: {e}")
        await message.answer("❌ Ошибка отправки сообщения.")


# Пересылка сообщений от админа
@router.message(AdminStates.CHATTING_WITH_USER)
async def forward_admin_message(message: Message, state: FSMContext):
    """Пересылка сообщения от админа пользователю."""
    data = await state.get_data()
    user_id = data.get('support_user_id')
    
    if not user_id or user_id not in active_dialogs:
        await message.answer("❌ Диалог завершен.")
        await state.clear()
        return
    
    try:
        # Пересылаем сообщение пользователю
        prefix = "👨‍💻 Ответ поддержки:\n\n"
        
        if message.text:
            await message.bot.send_message(user_id, prefix + message.text)
        elif message.photo:
            await message.bot.send_photo(user_id, message.photo[-1].file_id, caption=prefix + (message.caption or ""))
        elif message.document:
            await message.bot.send_document(user_id, message.document.file_id, caption=prefix + (message.caption or ""))
        elif message.voice:
            await message.bot.send_voice(user_id, message.voice.file_id, caption=prefix)
        elif message.video:
            await message.bot.send_video(user_id, message.video.file_id, caption=prefix + (message.caption or ""))
        else:
            await message.bot.send_message(user_id, prefix + "[Неподдерживаемый тип сообщения]")
    except Exception as e:
        logger.error(f"Ошибка пересылки пользователю {user_id}: {e}")
        await message.answer("❌ Ошибка отправки сообщения.")
