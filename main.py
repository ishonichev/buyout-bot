"""Главный файл запуска бота для выкупов товаров."""
import asyncio
import logging
from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
import uvicorn

from bot.config import settings
from bot.database.database import init_db
from bot.handlers import client_new, admin_new
from bot.middlewares.db_middleware import DatabaseMiddleware
from bot.middlewares.services_middleware import ServicesMiddleware
from bot.services.sheets_service import SheetsService
from bot.api.webapp_api import app as fastapi_app


logger = logging.getLogger(__name__)


async def run_bot(bot: Bot, dp: Dispatcher):
    """Запуск бота."""
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Бот запущен в режиме polling")
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        logger.info("Бот остановлен")
    finally:
        await bot.session.close()


async def run_fastapi():
    """Запуск FastAPI сервера."""
    config = uvicorn.Config(
        fastapi_app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    """Основная функция запуска бота."""
    # Создать директорию для логов если не существует
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO if not settings.DEBUG else logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/bot.log'),
            logging.StreamHandler()
        ]
    )
    
    logger.info("🚀 Запуск бота v2.0...")
    
    # Инициализация базы данных
    await init_db()
    logger.info("✅ База данных инициализирована")
    
    # Инициализируем конфигурацию бота
    try:
        from bot.utils.init_bot_config import init_default_config
        await init_default_config()
        logger.info("✅ Конфигурация бота инициализирована")
    except Exception as e:
        logger.warning(f"⚠️ Конфиг уже существует или ошибка: {e}")
    
    # Инициализация Redis для FSM
    redis = Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB
    )
    storage = RedisStorage(redis=redis)
    
    # Инициализация бота и диспетчера
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=storage)
    
    # Инициализация сервисов
    sheets_service = SheetsService()
    await sheets_service.initialize()
    
    # Сохраняем сервисы в workflow_data для доступа из хэндлеров
    dp.workflow_data.update({
        'sheets_service': sheets_service
    })
    
    logger.info("✅ Сервисы инициализированы")
    
    # Подключение middleware
    dp.update.middleware(ServicesMiddleware())  # Первым добавляем services
    dp.update.middleware(DatabaseMiddleware())  # Потом database
    
    # Регистрация роутеров (НОВЫЕ ХЭНДЛЕРЫ)
    dp.include_router(admin_new.router)
    dp.include_router(client_new.router)
    
    logger.info("✅ Роутеры зарегистрированы")
    
    try:
        # Запускаем бота и FastAPI параллельно
        await asyncio.gather(
            run_bot(bot, dp),
            run_fastapi()
        )
    finally:
        await redis.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем")
