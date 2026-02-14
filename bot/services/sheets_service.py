"""Сервис для работы с Google Sheets."""
import logging
from datetime import datetime
from typing import Dict, Any, Set
import gspread_asyncio
from google.oauth2.service_account import Credentials
from bot.config import settings
import asyncio

logger = logging.getLogger(__name__)


class SheetsService:
    """Сервис для работы с Google Sheets."""
    
    def __init__(self):
        self.agcm = None
        self.client = None
        self.spreadsheet = None
        self.sheet1 = None  # Лист "Заявки"
        self.sheet2 = None  # Лист "Аналитика"
        
        # Кэш УНИКАЛЬНЫХ пользователей для каждого события
        self.unique_users: Dict[str, Set[int]] = {
            'bot_started': set(),
            'button_1': set(),
            'button_2': set(),
            'button_3': set(),
            'button_4': set(),
            'button_5': set(),
            'button_6': set(),
            'button_7': set(),
        }
        self._update_task = None
        
    def get_creds(self):
        """Получение credentials для Google API."""
        creds = Credentials.from_service_account_file(settings.GOOGLE_SHEETS_CREDENTIALS_FILE)
        scoped = creds.with_scopes([
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ])
        return scoped
    
    async def initialize(self):
        """Инициализация подключения к Google Sheets."""
        try:
            self.agcm = gspread_asyncio.AsyncioGspreadClientManager(self.get_creds)
            self.client = await self.agcm.authorize()
            self.spreadsheet = await self.client.open_by_key(settings.GOOGLE_SPREADSHEET_ID)
            
            # Получаем или создаем листы
            await self._ensure_sheets_exist()
            await self._ensure_headers_exist()
            
            # Загружаем уникальных пользователей из БД
            await self._load_unique_users_from_db()
            
            # Запускаем периодическое обновление (каждые 5 мин)
            self._update_task = asyncio.create_task(self._periodic_sync())
            
            logger.info("Подключение к Google Sheets установлено")
        except Exception as e:
            logger.error(f"Ошибка подключения к Google Sheets: {e}")
            raise
    
    async def _ensure_sheets_exist(self):
        """Проверка существования листов, создание если нет."""
        worksheets = await self.spreadsheet.worksheets()
        worksheet_titles = [ws.title for ws in worksheets]
        
        # Лист 1 - Заявки
        if settings.SHEET1_NAME not in worksheet_titles:
            self.sheet1 = await self.spreadsheet.add_worksheet(
                title=settings.SHEET1_NAME,
                rows=1000,
                cols=7
            )
            logger.info(f"Создан лист '{settings.SHEET1_NAME}'")
        else:
            self.sheet1 = await self.spreadsheet.worksheet(settings.SHEET1_NAME)
        
        # Лист 2 - Аналитика
        if settings.SHEET2_NAME not in worksheet_titles:
            self.sheet2 = await self.spreadsheet.add_worksheet(
                title=settings.SHEET2_NAME,
                rows=100,
                cols=9
            )
            logger.info(f"Создан лист '{settings.SHEET2_NAME}'")
        else:
            self.sheet2 = await self.spreadsheet.worksheet(settings.SHEET2_NAME)
    
    async def _ensure_headers_exist(self):
        """Создание заголовков таблиц если их нет."""
        # Заголовки для Листа 1 (Заявки)
        sheet1_headers = ["№", "Ник тг", "Корзина", "Покупка", "Выкуп", "Отзыв", "Оплата (сумма)"]
        first_row = await self.sheet1.row_values(1)
        
        if not first_row or first_row[0] != "№":
            await self.sheet1.update('A1:G1', [sheet1_headers])
            logger.info("Заголовки Листа 1 созданы")
        
        # Заголовки для Листа 2 (Аналитика) - ОБНОВЛЕННЫЕ НАЗВАНИЯ
        sheet2_headers = [
            "",
            "Запустили бот", 
            "Выбрали товар",
            "Приняли инструкцию",
            "Отправили скриншот товара в корзине",
            "Отправили скриншот покупки",
            "Отправили фотографию товара",
            "Отправили скриншот опубликованного отзыва",
            "Отправили реквизиты"
        ]
        first_row = await self.sheet2.row_values(1)
        
        if not first_row or len(first_row) < 2 or first_row[1] != "Запустили бот":
            await self.sheet2.update('A1:I1', [sheet2_headers])
            await self.sheet2.update('A2', [["Кол-во"]])
            await self.sheet2.update('A3', [["% "]])
            # Инициализируем нулями
            await self.sheet2.update('B2:I2', [[0] * 8])
            await self.sheet2.update('B3:I3', [["100%"] + ["0%"] * 7])
            logger.info("Заголовки Листа 2 созданы")
    
    async def _load_unique_users_from_db(self):
        """Загрузить уникальных пользователей из базы данных."""
        try:
            from bot.database.database import async_session_maker
            from bot.database.models import AnalyticsEvent
            from sqlalchemy import select
            
            async with async_session_maker() as session:
                # Получаем уникальные пары (user_id, event_type)
                result = await session.execute(
                    select(AnalyticsEvent.user_id, AnalyticsEvent.event_type).distinct()
                )
                
                rows = result.all()
                for user_id, event_type in rows:
                    if event_type in self.unique_users:
                        self.unique_users[event_type].add(user_id)
                
            counts = {k: len(v) for k, v in self.unique_users.items()}
            logger.info(f"Уникальные пользователи загружены: {counts}")
        except Exception as e:
            logger.error(f"Ошибка загрузки уникальных пользователей: {e}")
    
    async def _periodic_sync(self):
        """Периодическая синхронизация с Google Sheets (каждые 5 мин)."""
        while True:
            try:
                await asyncio.sleep(300)  # 5 минут
                await self._sync_analytics_to_sheet()
            except Exception as e:
                logger.error(f"Ошибка периодической синхронизации: {e}")
    
    async def _sync_analytics_to_sheet(self):
        """Синхронизация кэша с Google Sheets."""
        try:
            logger.info("Синхронизация аналитики с Google Sheets...")
            
            # Обновляем количество (строка 2) - ТЕПЕРЬ УНИКАЛЬНЫЕ ПОЛЬЗОВАТЕЛИ
            counts = [
                len(self.unique_users['bot_started']),
                len(self.unique_users['button_1']),
                len(self.unique_users['button_2']),
                len(self.unique_users['button_3']),
                len(self.unique_users['button_4']),
                len(self.unique_users['button_5']),
                len(self.unique_users['button_6']),
                len(self.unique_users['button_7']),
            ]
            
            await self.sheet2.update('B2:I2', [counts])
            
            # Пересчитываем проценты
            percentages = []
            
            for i, count in enumerate(counts):
                if i == 0:
                    percentages.append("100%")
                else:
                    prev_count = counts[i - 1] if i > 0 else 1
                    if prev_count > 0:
                        percentage = (count / prev_count) * 100
                        percentages.append(f"{percentage:.1f}%")
                    else:
                        percentages.append("0%")
            
            await self.sheet2.update('B3:I3', [percentages])
            logger.info(f"Аналитика синхронизирована: {counts}")
            
        except Exception as e:
            logger.error(f"Ошибка синхронизации: {e}")
    
    def increment_analytics_event(self, event_type: str, user_id: int):
        """ДОБАВИТЬ УНИКАЛЬНОГО пользователя в множество (быстро, не блокирует)."""
        if event_type in self.unique_users:
            was_new = user_id not in self.unique_users[event_type]
            self.unique_users[event_type].add(user_id)
            if was_new:
                logger.info(f"📊 {event_type}: +1 уникальный пользователь (user_id={user_id}), всего: {len(self.unique_users[event_type])}")
    
    async def add_order_to_sheet1(self, order_data: Dict[str, Any]):
        """Добавление ПОЛНОЙ заявки в Лист 1 (только в конце!)."""
        try:
            order_id = order_data.get('order_id')
            username = order_data.get('username', 'Неизвестно')
            basket_date = self._format_date(order_data.get('basket_date'))
            buy_date = self._format_date(order_data.get('buy_date'))
            received_date = self._format_date(order_data.get('received_date'))
            review_date = self._format_date(order_data.get('review_date'))
            cashback = order_data.get('cashback_amount', 0)
            
            logger.info(f"📊 Записываю ПОЛНЫЙ заказ #{order_id}")
            
            row_data = [
                order_id,
                username,
                basket_date,
                buy_date,
                received_date,
                review_date,
                cashback
            ]
            
            await self.sheet1.append_row(row_data)
            logger.info(f"✅ Заказ #{order_id} успешно записан: {username}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка записи заказа: {e}", exc_info=True)
    
    def _format_date(self, date_value) -> str:
        """Форматирование даты в строку."""
        if isinstance(date_value, datetime):
            return date_value.strftime("%d.%m.%Y")
        elif isinstance(date_value, str):
            return date_value
        return ""
