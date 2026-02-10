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
            await self.sheet2.update('A3', [["% "]])
            # Инициализируем нулями
            await self.sheet2.update('B2:J2', [[0] * 9])
            await self.sheet2.update('B3:J3', [["100%"] + ["0%"] * 8])
            logger.info("Заголовки Листа 2 созданы")
    
    async def add_order_to_sheet1(self, order_data: Dict[str, Any]):
        """Добавление ПОЛНОЙ заявки в Лист 1 (только в конце!)."""
        try:
            order_id = order_data.get('order_id')
            username = order_data.get('username', 'Неизвестно')
            basket_date = self._format_date(order_data.get('basket_date'))
            buy_date = self._format_date(order_data.get('buy_date'))
            received_date = self._format_date(order_data.get('received_date'))  # ТЕПЕРЬ ИСПОЛЬЗУЕМ!
            review_date = self._format_date(order_data.get('review_date'))      # ТЕПЕРЬ ИСПОЛЬЗУЕМ!
            cashback = order_data.get('cashback_amount', 0)
            
            logger.info(f"[📊 Sheets] Записываю ПОЛНЫЙ заказ #{order_id}")
            
            # ПОЛНАЯ строка со всеми данными
            row_data = [
                order_id,
                username,
                basket_date,
                buy_date,
                received_date,  # Выкуп
                review_date,    # Отзыв
                cashback
            ]
            
            await self.sheet1.append_row(row_data)
            logger.info(f"[✅ Sheets] Заказ #{order_id} успешно записан: {username}")
            
        except Exception as e:
            logger.error(f"[❌ Sheets] Ошибка записи заказа: {e}", exc_info=True)
    
    async def increment_analytics_event(self, event_type: str):
        """ИНКРЕМЕНТАЛЬНОЕ обновление аналитики (+1 к событию)."""
        try:
            event_mapping = {
                'bot_visited': 'B',
                'bot_started': 'C',
                'button_1': 'D',
                'button_2': 'E',
                'button_3': 'F',
                'button_4': 'G',
                'button_5': 'H',
                'button_6': 'I',
                'button_7': 'J',
            }
            
            if event_type not in event_mapping:
                return
            
            col = event_mapping[event_type]
            
            # Читаем текущее значение
            current_value = await self.sheet2.acell(f'{col}2')
            count = int(current_value.value) if current_value.value else 0
            
            # Увеличиваем на 1
            await self.sheet2.update(f'{col}2', [[count + 1]])
            
            # Пересчитываем проценты
            await self._recalculate_percentages()
            
            logger.info(f"[📊 Sheets] {event_type}: {count} -> {count + 1}")
            
        except Exception as e:
            logger.error(f"[❌ Sheets] Ошибка инкремента аналитики: {e}")
    
    async def _recalculate_percentages(self):
        """Пересчитать проценты для Листт2."""
        try:
            # Читаем все значения
            row2 = await self.sheet2.row_values(2)
            counts = [int(v) if v else 0 for v in row2[1:10]]  # B2:J2
            
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
            
            await self.sheet2.update('B3:J3', [percentages])
            
        except Exception as e:
            logger.error(f"[❌ Sheets] Ошибка пересчета процентов: {e}")
    
    def _format_date(self, date_value) -> str:
        """Форматирование даты в строку."""
        if isinstance(date_value, datetime):
            return date_value.strftime("%d.%m.%Y")
        elif isinstance(date_value, str):
            return date_value
        return ""
