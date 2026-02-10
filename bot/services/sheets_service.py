"""Сервис для работы с Google Sheets."""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
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
        
        # Кэш аналитики в памяти (обновляется каждые 5 мин)
        self.analytics_cache = {
            'bot_started': 0,
            'button_1': 0,
            'button_2': 0,
            'button_3': 0,
            'button_4': 0,
            'button_5': 0,
            'button_6': 0,
            'button_7': 0,
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
            await self._load_analytics_from_sheet()
            
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
                cols=9  # УБРАЛИ 1 колонку
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
        
        # Заголовки для Листа 2 (Аналитика) - УБРАЛИ "Зашли в бот"
        sheet2_headers = [
            "",
            "Запустили бот", 
            "Нажали кнопку 1",
            "Нажали кнопку 2",
            "Нажали кнопку 3",
            "Нажали кнопку 4",
            "Нажали кнопку 5",
            "Нажали кнопку 6",
            "Нажали кнопку 7"
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
    
    async def _load_analytics_from_sheet(self):
        """Загрузить текущие значения из таблицы."""
        try:
            row2 = await self.sheet2.row_values(2)
            if len(row2) >= 9:
                self.analytics_cache['bot_started'] = int(row2[1]) if row2[1] else 0
                self.analytics_cache['button_1'] = int(row2[2]) if row2[2] else 0
                self.analytics_cache['button_2'] = int(row2[3]) if row2[3] else 0
                self.analytics_cache['button_3'] = int(row2[4]) if row2[4] else 0
                self.analytics_cache['button_4'] = int(row2[5]) if row2[5] else 0
                self.analytics_cache['button_5'] = int(row2[6]) if row2[6] else 0
                self.analytics_cache['button_6'] = int(row2[7]) if row2[7] else 0
                self.analytics_cache['button_7'] = int(row2[8]) if row2[8] else 0
            logger.info(f"Аналитика загружена: {self.analytics_cache}")
        except Exception as e:
            logger.error(f"Ошибка загрузки аналитики: {e}")
    
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
            
            # Обновляем количество (строка 2)
            counts = [
                self.analytics_cache['bot_started'],
                self.analytics_cache['button_1'],
                self.analytics_cache['button_2'],
                self.analytics_cache['button_3'],
                self.analytics_cache['button_4'],
                self.analytics_cache['button_5'],
                self.analytics_cache['button_6'],
                self.analytics_cache['button_7'],
            ]
            
            await self.sheet2.update('B2:I2', [counts])
            
            # Пересчитываем проценты
            percentages = []
            prev_count = counts[0] if counts[0] > 0 else 1
            
            for i, count in enumerate(counts):
                if i == 0:
                    percentages.append("100%")
                elif prev_count > 0:
                    percentage = (count / prev_count) * 100
                    percentages.append(f"{percentage:.1f}%")
                else:
                    percentages.append("0%")
                prev_count = count
            
            await self.sheet2.update('B3:I3', [percentages])
            logger.info(f"Аналитика синхронизирована: {counts}")
            
        except Exception as e:
            logger.error(f"Ошибка синхронизации: {e}")
    
    def increment_analytics_event(self, event_type: str):
        """ИНКРЕМЕНТ в ПАМЯТИ (быстро, не блокирует)."""
        if event_type in self.analytics_cache:
            self.analytics_cache[event_type] += 1
            logger.info(f"📊 {event_type}: {self.analytics_cache[event_type]}")
    
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
