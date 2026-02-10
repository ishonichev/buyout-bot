"""Конфигурация бота."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Настройки приложения."""
    
    # Telegram Bot
    BOT_TOKEN: str
    ADMIN_BOT_TOKEN: str = ""  # Токен для отдельного админ-бота (опционально)
    ADMIN_IDS: str  # Список ID через запятую, например: "123456789,987654321"
    
    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "buyout_bot"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Google Sheets
    GOOGLE_SHEETS_CREDENTIALS_FILE: str = "credentials.json"
    GOOGLE_SPREADSHEET_ID: str
    SHEET1_NAME: str = "Лист1"
    SHEET2_NAME: str = "Лист2"
    
    # Analytics
    ANALYTICS_UPDATE_INTERVAL: int = 300  # Обновление аналитики каждые 5 минут (300 секунд)
    
    # Bot Configuration
    BOT_LANGUAGE: str = "ru"
    DEBUG: bool = False
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )
    
    @property
    def database_url(self) -> str:
        """Получить URL подключения к базе данных."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    @property
    def admin_ids(self) -> List[int]:
        """Получить список ID администраторов."""
        return [int(id.strip()) for id in self.ADMIN_IDS.split(",") if id.strip()]
    
    @property
    def admin_ids_list(self) -> List[int]:
        """Алиас для совместимости."""
        return self.admin_ids
    
    @property
    def moderator_ids(self) -> List[int]:
        """Список ID модераторов (включает всех админов)."""
        return self.admin_ids


settings = Settings()
