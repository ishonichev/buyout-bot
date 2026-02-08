"""Миддлварь для передачи сервисов в хэндлеры."""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
import logging

logger = logging.getLogger(__name__)


class ServicesMiddleware(BaseMiddleware):
    """Миддлварь для передачи сервисов из workflow_data."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем сервисы из workflow_data
        workflow_data = data.get('workflow_data', {})
        
        # Добавляем сервисы в data
        if 'sheets_service' in workflow_data:
            data['sheets_service'] = workflow_data['sheets_service']
        
        if 'analytics_service' in workflow_data:
            data['analytics_service'] = workflow_data['analytics_service']
        
        return await handler(event, data)
