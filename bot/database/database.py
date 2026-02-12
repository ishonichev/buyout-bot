"""Настройка подключения к базе данных."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from bot.config import settings
import logging

logger = logging.getLogger(__name__)

# Создаем асинхронный движок с принудительной кодировкой UTF-8
engine = create_async_engine(
    settings.database_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={
        "server_settings": {
            "client_encoding": "UTF8"
        }
    }
)

# Создаем фабрику сессий
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass


async def get_session() -> AsyncSession:
    """Получить сессию базы данных."""
    async with async_session_maker() as session:
        yield session


async def init_db():
    """Инициализация базы данных (создание таблиц)."""
    from bot.database.models import User, Product, Order, AnalyticsEvent
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Таблицы базы данных созданы")
    
    # Инициализируем 4 товара
    async with async_session_maker() as session:
        from sqlalchemy import select
        result = await session.execute(select(Product))
        products = result.scalars().all()
        
        if len(products) == 0:
            for i in range(1, 5):
                product = Product(
                    id=i,
                    name=f"Товар {i}",
                    is_active=False,
                    instruction_text="Инструкция не установлена"
                )
                session.add(product)
            
            await session.commit()
            logger.info("Создано 4 пустых товара")
