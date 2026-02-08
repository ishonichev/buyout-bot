"""Обработчики для поддержки."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
import logging

from bot.config import settings
from bot.states.client_states import SupportStates

logger = logging.getLogger(__name__)
router = Router(name='support')


@router.callback_query(F.data == "has_questions")
async def has_questions(callback: CallbackQuery):
    """Пользователь нажал 'Есть вопросы'."""
    user_id = callback.from_user.id
    username = callback.from_user.username
    full_name = callback.from_user.full_name
    
    # Уведомляем модераторов
    for moderator_id in settings.moderator_ids:
        try:
            await callback.bot.send_message(
                moderator_id,
                f"📩 <b>Новый вопрос!</b>\n\n"
                f"👤 Пользователь: {full_name}\n"
                f"🆔 Username: @{username or 'нет'}\n"
                f"🆔 ID: {user_id}\n\n"
                f"💬 Пользователь просит помощи. Напишите ему в личку или используйте username."
            )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {e}")
    
    await callback.message.answer(
        "👍 Спасибо! Наш менеджер свяжется с вами в ближайшее время."
    )
    await callback.message.delete()
    await callback.answer()
