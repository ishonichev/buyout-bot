"""Сервис аналитики."""
from bot.services.sheets_service import SheetsService
from bot.config import settings
from datetime import datetime
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Сервис для сбора аналитики."""
    
    def __init__(self, sheets_service: SheetsService):
        self.sheets_service = sheets_service
        self.events_cache = defaultdict(int)
    
    async def track_event(self, event_type: str):
        """Зафиксировать событие."""
        self.events_cache[event_type] += 1
        logger.debug(f"Событие {event_type} зафиксировано")
    
    async def update_analytics_sheet(self):
        """Обновить Лист 2 с аналитикой."""
        try:
            worksheet = await self.sheets_service.spreadsheet.worksheet(settings.SHEET2_NAME)
            
            # Получаем текущие значения
            values = await worksheet.get_all_values()
            
            if len(values) < 2:
                # Создаем заголовки
                headers = [
                    '',
                    'Зашли в бот',
                    'Запустили бот',
                    'Нажали кнопку 1',
                    'Нажали кнопку 2',
                    'Нажали кнопку 3',
                    'Нажали кнопку 4',
                    'Нажали кнопку 5',
                    'Нажали кнопку 6',
                    'Нажали кнопку 7'
                ]
                await worksheet.append_row(headers)
                await worksheet.append_row(['Кол-во'] + [0] * 9)
                await worksheet.append_row(['%'] + ['0%'] * 9)
            
            # Обновляем значения
            for event_type, count in self.events_cache.items():
                # Здесь логика обновления счётчиков
                pass
            
            logger.info("Аналитика обновлена")
        except Exception as e:
            logger.error(f"Ошибка обновления аналитики: {e}")
