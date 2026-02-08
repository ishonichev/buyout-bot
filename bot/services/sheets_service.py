"""Сервис работы с Google Sheets."""
import gspread_asyncio
from google.oauth2.service_account import Credentials
from bot.config import settings
import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)


class SheetsService:
    """Сервис для работы с Google Sheets."""
    
    def __init__(self):
        self.agcm = None
        self.spreadsheet = None
    
    def _get_credentials(self):
        """Получить креденшиалы для Google Sheets."""
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_file(
            settings.GOOGLE_SHEETS_CREDENTIALS_FILE,
            scopes=scopes
        )
        return creds
    
    async def initialize(self):
        """Инициализация подключения к Google Sheets."""
        try:
            self.agcm = gspread_asyncio.AsyncioGspreadClientManager(self._get_credentials)
            agc = await self.agcm.authorize()
            self.spreadsheet = await agc.open_by_key(settings.GOOGLE_SPREADSHEET_ID)
            logger.info(f"Подключение к Google Sheets установлено")
        except Exception as e:
            logger.error(f"Ошибка подключения к Google Sheets: {e}")
            raise
    
    async def add_order_to_sheet1(self, data: Dict):
        """Добавить запись в Лист 1 (Заказы)."""
        try:
            worksheet = await self.spreadsheet.worksheet(settings.SHEET1_NAME)
            
            # Формат даты
            date_format = "%d.%m.%Y"
            
            row = [
                data.get('order_id', ''),
                data.get('username', ''),
                data.get('basket_date', datetime.now()).strftime(date_format) if data.get('basket_date') else '',
                data.get('buy_date', datetime.now()).strftime(date_format) if data.get('buy_date') else '',
                data.get('received_date', ''),
                data.get('review_date', ''),
                data.get('cashback_amount', '')
            ]
            
            await worksheet.append_row(row)
            logger.info(f"Заказ {data.get('order_id')} добавлен в Лист 1")
        except Exception as e:
            logger.error(f"Ошибка записи в Лист 1: {e}")
    
    async def update_order_in_sheet1(self, order_id: int, field: str, value: str):
        """Обновить запись в Лист 1."""
        try:
            worksheet = await self.spreadsheet.worksheet(settings.SHEET1_NAME)
            
            # Найти строку с order_id
            cell = await worksheet.find(str(order_id))
            
            if cell:
                # Определить колонку по полю
                col_map = {
                    'basket_date': 3,
                    'buy_date': 4,
                    'received_date': 5,
                    'review_date': 6
                }
                
                if field in col_map:
                    await worksheet.update_cell(cell.row, col_map[field], value)
                    logger.info(f"Обновлено поле {field} для заказа {order_id}")
        except Exception as e:
            logger.error(f"Ошибка обновления Листа 1: {e}")
