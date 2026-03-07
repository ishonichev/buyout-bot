"""Миддлварь для работы с базой данных."""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
from bot.database.database import async_session_maker
from bot.database.models import User
from sqlalchemy import select
import logging

logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    """Миддлварь для создания сессии БД и регистрации пользователей."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        async with async_session_maker() as session:
            data['session'] = session
            
            # Получаем пользователя Telegram
            tg_user: TgUser = data.get('event_from_user')
            
            if tg_user:
                # Проверяем, есть ли пользователь в БД
                result = await session.execute(
                    select(User).where(User.tg_id == tg_user.id)
                )
                user = result.scalar_one_or_none()
                
                if user is None:
                    user = User(
                        tg_id=tg_user.id,
                        username=tg_user.username,
                        full_name=tg_user.full_name or "Неизвестно"
                    )
                    session.add(user)
                    await session.commit()
                    logger.info(f"Новый пользователь: {user.tg_id} ({user.full_name})")
                
                # Добавляем пользователя в data
                data['user'] = user
            
            return await handler(event, data)
