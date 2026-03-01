"""Сервис аналитики."""
from bot.services.sheets_service import SheetsService
from bot.config import settings
from bot.database.database import async_session_maker
from sqlalchemy import select, func
from bot.database.models import AnalyticsEvent
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Сервис для сбора аналитики."""
    
    def __init__(self, sheets_service: SheetsService):
        self.sheets_service = sheets_service
    
    async def track_event(self, user_id: int, event_type: str):
        """Зафиксировать событие в БД."""
        try:
            async with async_session_maker() as session:
                from bot.database.models import AnalyticsEvent
                
                event = AnalyticsEvent(
                    user_tg_id=user_id,
                    event_type=event_type
                )
                session.add(event)
                await session.commit()
                logger.debug(f"Событие {event_type} зафиксировано для user_id={user_id}")
        except Exception as e:
            logger.error(f"Ошибка записи события: {e}")
    
    async def get_analytics_data(self) -> dict:
        """Получить статистику из БД.
        
        Returns:
            dict: {
                'bot_visited': кол-во зашедших,
                'bot_started': кол-во запустивших,
                'button_1': ...
            }
        """
        try:
            async with async_session_maker() as session:
                # Подсчёт уникальных пользователей по каждому событию
                event_types = [
                    'bot_visited',    # Зашли в бот
                    'bot_started',    # Запустили бот
                    'button_1',       # Кнопка "Выбрать товар"
                    'button_2',       # Выбор конкретного товара
                    'button_3',       # "Я прочитал и согласен"
                    'button_4',       # "Отправить скриншот корзины"
                    'button_5',       # "Отправить скриншот покупки"
                    'button_6',       # "Товар на руках"
                    'button_7'        # "Скриншот опубликованного отзыва"
                ]
                
                stats = {}
                
                for event_type in event_types:
                    # Подсчитать уникальных пользователей
                    query = select(func.count(func.distinct(AnalyticsEvent.user_tg_id))).where(
                        AnalyticsEvent.event_type == event_type
                    )
                    result = await session.execute(query)
                    count = result.scalar() or 0
                    stats[event_type] = count
                
                logger.info(f"Статистика получена: {stats}")
                return stats
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {}
    
    async def update_analytics_sheet(self):
        """Обновить Лист2 с аналитикой."""
        try:
            # Получить статистику
            stats = await self.get_analytics_data()
            
            if not stats:
                logger.warning("Статистика пуста, обновление пропущено")
                return
            
            # Обновить таблицу (передаем dict)
            await self.sheets_service.update_analytics_sheet2(stats)
            logger.info("Аналитика обновлена в Google Sheets")
        except Exception as e:
            logger.error(f"Ошибка обновления аналитики: {e}")
