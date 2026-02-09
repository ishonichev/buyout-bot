"""Сервис для работы с Google Sheets."""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import gspread_asyncio
from google.oauth2.service_account import Credentials
from bot.config import settings

logger = logging.getLogger(__name__)


class SheetsService:
    """Сервис для работы с Google Sheets."""
    
    def __init__(self):
        self.agcm = None
        self.client = None
        self.spreadsheet = None
        self.sheet1 = None  # Лист "Заявки"
        self.sheet2 = None  # Лист "Аналитика"
        
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
                cols=10
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
        
        # Заголовки для Листа 2 (Аналитика)
        sheet2_headers = [
            "",
            "Зашли в бот",
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
        
        if not first_row or len(first_row) < 2 or first_row[1] != "Зашли в бот":
            await self.sheet2.update('A1:J1', [sheet2_headers])
            await self.sheet2.update('A2', [["Кол-во"]])
            await self.sheet2.update('A3', [["%"]])
            # Инициализируем нулями
            await self.sheet2.update('B2:J2', [[0] * 9])
            await self.sheet2.update('B3:J3', [["100%"] + ["0%"] * 8])
            logger.info("Заголовки Листа 2 созданы")
    
    async def add_order_to_sheet1(self, order_data: Dict[str, Any]):
        """Добавление заявки в Лист 1."""
        try:
            # Получаем все записи
            all_values = await self.sheet1.get_all_values()
            next_row = len(all_values) + 1
            order_num = next_row - 1  # Номер заказа (минус заголовок)
            
            # Форматируем данные
            username = order_data.get('username', 'Неизвестно')
            if not username.startswith('@'):
                username = f"@{username}" if username != 'Неизвестно' else username
            
            basket_date = self._format_date(order_data.get('basket_date'))
            buy_date = self._format_date(order_data.get('buy_date'))
            received_date = self._format_date(order_data.get('received_date', ''))
            review_date = self._format_date(order_data.get('review_date', ''))
            cashback = order_data.get('cashback_amount', 0)
            
            row_data = [
                order_num,
                username,
                basket_date,
                buy_date,
                received_date,
                review_date,
                cashback
            ]
            
            await self.sheet1.append_row(row_data)
            logger.info(f"Заявка #{order_num} добавлена в Лист 1")
            
        except Exception as e:
            logger.error(f"Ошибка добавления заявки в Лист 1: {e}")
    
    async def update_order_in_sheet1(self, username: str, field: str, value: Any):
        """Обновление существующей заявки в Листе 1."""
        try:
            all_values = await self.sheet1.get_all_values()
            
            # Ищем строку с username
            row_index = None
            for i, row in enumerate(all_values[1:], start=2):  # Пропускаем заголовок
                if len(row) > 1 and row[1] == username:
                    row_index = i
                    break
            
            if not row_index:
                return
            
            # Определяем колонку
            field_map = {
                'received_date': 'E',  # Выкуп
                'review_date': 'F',    # Отзыв
            }
            
            if field in field_map:
                col = field_map[field]
                formatted_value = self._format_date(value) if isinstance(value, datetime) else value
                await self.sheet1.update(f'{col}{row_index}', [[formatted_value]])
                logger.info(f"Обновлена ячейка {col}{row_index} для {username}")
                
        except Exception as e:
            logger.error(f"Ошибка обновления заявки: {e}")
    
    async def update_analytics_sheet2(self, analytics_data: Dict[str, int]):
        """Обновление аналитики в Листе 2."""
        try:
            # analytics_data содержит количество для каждого события
            # Формат: {'bot_visited': 100, 'bot_started': 80, ...}
            
            event_mapping = {
                'bot_visited': 'B',      # Зашли в бот
                'bot_started': 'C',      # Запустили бот
                'button_1': 'D',         # Нажали кнопку 1
                'button_2': 'E',         # Нажали кнопку 2
                'button_3': 'F',         # Нажали кнопку 3
                'button_4': 'G',         # Нажали кнопку 4
                'button_5': 'H',         # Нажали кнопку 5
                'button_6': 'I',         # Нажали кнопку 6
                'button_7': 'J',         # Нажали кнопку 7
            }
            
            # Обновляем количество (строка 2)
            for event, col in event_mapping.items():
                count = analytics_data.get(event, 0)
                await self.sheet2.update(f'{col}2', [[count]])
            
            # Вычисляем и обновляем проценты (строка 3)
            counts = [analytics_data.get(event, 0) for event in event_mapping.keys()]
            total = counts[0] if counts[0] > 0 else 1  # Зашли в бот
            
            percentages = []
            prev_count = total
            
            for count in counts:
                if prev_count > 0:
                    percentage = (count / prev_count) * 100
                    percentages.append(f"{percentage:.1f}%")
                    prev_count = count
                else:
                    percentages.append("0%")
            
            # Первый всегда 100%
            percentages[0] = "100%"
            
            await self.sheet2.update('B3:J3', [percentages])
            logger.info("Аналитика в Листе 2 обновлена")
            
        except Exception as e:
            logger.error(f"Ошибка обновления аналитики: {e}")
    
    def _format_date(self, date_value) -> str:
        """Форматирование даты в строку."""
        if isinstance(date_value, datetime):
            return date_value.strftime("%d.%m.%Y")
        elif isinstance(date_value, str):
            return date_value
        return ""
