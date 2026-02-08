"""Главный файл запуска бота для выкупов товаров."""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from bot.config import settings
from bot.database.database import init_db
from bot.handlers import client, admin, support, client_screenshots
from bot.middlewares.db_middleware import DatabaseMiddleware
from bot.services.analytics_service import AnalyticsService
from bot.services.sheets_service import SheetsService


logger = logging.getLogger(__name__)


async def update_analytics_task(analytics_service: AnalyticsService):
    """Фоновая задача для обновления аналитики каждые 5 минут."""
    while True:
        try:
            await asyncio.sleep(settings.ANALYTICS_UPDATE_INTERVAL)
            logger.info("Запуск обновления аналитики...")
            await analytics_service.update_analytics_sheet()
        except asyncio.CancelledError:
            logger.info("Фоновая задача аналитики остановлена")
            break
        except Exception as e:
            logger.error(f"Ошибка в фоновой задаче аналитики: {e}")
            await asyncio.sleep(60)  # Подождать минуту перед повтором


async def main():
    """Основная функция запуска бота."""
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO if not settings.DEBUG else logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/bot.log'),
            logging.StreamHandler()
        ]
    )
    
    logger.info("Запуск бота...")
    
    # Инициализация базы данных
    await init_db()
    logger.info("База данных инициализирована")
    
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
    
    # Подключение middleware
    dp.update.middleware(DatabaseMiddleware())
    
    # Регистрация роутеров
    dp.include_router(admin.router)
    dp.include_router(support.router)
    dp.include_router(client_screenshots.router)
    dp.include_router(client.router)
    
    # Инициализация сервисов
    sheets_service = SheetsService()
    await sheets_service.initialize()
    analytics_service = AnalyticsService(sheets_service)
    
    # Сохраняем сервисы в bot для доступа из хэндлеров
    bot['sheets_service'] = sheets_service
    bot['analytics_service'] = analytics_service
    
    logger.info("Сервисы инициализированы")
    
    # Запуск фоновой задачи для аналитики
    analytics_task = asyncio.create_task(update_analytics_task(analytics_service))
    logger.info("Фоновая задача аналитики запущена")
    
    try:
        # Удаляем вебхук на случай если он был установлен
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Бот запущен в режиме polling")
        
        # Запуск бота
        await dp.start_polling(bot)
    finally:
        # Остановка фоновой задачи
        analytics_task.cancel()
        try:
            await analytics_task
        except asyncio.CancelledError:
            pass
        
        await bot.session.close()
        await redis.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем")
