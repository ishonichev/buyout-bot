"""Конфигурация бота."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Настройки приложения."""
    
    # Telegram Bot
    BOT_TOKEN: str
    ADMIN_ID: int
    
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
    SHEET1_NAME: str = "Лист 1"
    SHEET2_NAME: str = "Лист 2"
    
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
    def moderator_ids(self) -> List[int]:
        """Список ID модераторов (пока только админ)."""
        return [self.ADMIN_ID]


settings = Settings()
