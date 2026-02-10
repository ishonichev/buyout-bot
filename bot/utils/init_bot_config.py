"""Инициализация дефолтных текстов в BotConfig."""
import asyncio
from sqlalchemy import select
from bot.database.database import async_session_maker
from bot.database.models import BotConfig
import logging

logger = logging.getLogger(__name__)


DEFAULT_TEXTS = {
    "welcome_message": {
        "value": (
            "👋 Привет!\n\n"
            "Для вашего и нашего удобства и экономии времени мы создали бота "
            "для выкупов со 100% кэшбэком.\n\n"
            "Вы сможете в любое время зайти и проверить какие товары доступны для выкупа "
            "и сразу их заказать не дожидаясь ответа от нашего менеджера.\n\n"
            "В случае вопросов и нестандартных ситуаций наш оператор выйдет на связь. "
            "Обещаем не спамить! 😉"
        ),
        "description": "Приветственное сообщение при /start"
    },
    "products_select_text": {
        "value": "🛌️ Выберите товар для выкупа:",
        "description": "Текст при выборе товара"
    },
    "step_1_message": {
        "value": "📦 Пришлите скриншот товара в корзине",
        "description": "Этап 1: товар в корзине"
    },
    "step_2_message": {
        "value": "💳 Пришлите скриншот покупки",
        "description": "Этап 2: факт покупки"
    },
    "step_3_message": {
        "value": "📦 Пришлите скриншот товара на руках (ПВЗ)",
        "description": "Этап 3: получение товара"
    },
    "step_4_message": {
        "value": (
            "⭐ Отлично!\n\n"
            "Отзыв ЗАВТРА на карточку 5 звезд БЕЗ ТЕКСТА И ФОТО\n\n"
            "Пришлите скриншот опубликованного отзыва"
        ),
        "description": "Этап 4: отзыв на WB"
    },
    "step_5_message": {
        "value": (
            "💰 Последний шаг!\n\n"
            "Напишите ваши реквизиты для перевода кэшбэка\n"
            "(номер карты или телефона)"
        ),
        "description": "Этап 5: реквизиты для выплаты"
    },
    "order_pending_message": {
        "value": "✅ Ваша заявка на проверке. Ожидайте уведомления от администратора!",
        "description": "Сообщение после отправки всех данных"
    },
    "payment_sent_message": {
        "value": "🎉 Кэшбэк выплачен! Спасибо за сотрудничество!",
        "description": "Сообщение пользователю после одобрения"
    }
}


async def init_default_config():
    """Инициализация дефолтных настроек."""
    async with async_session_maker() as session:
        for key, data in DEFAULT_TEXTS.items():
            # Проверяем существует ли уже
            result = await session.execute(
                select(BotConfig).where(BotConfig.config_key == key)
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                config = BotConfig(
                    config_key=key,
                    config_value=data["value"],
                    description=data["description"]
                )
                session.add(config)
                logger.info(f"✅ Добавлена настройка: {key}")
        
        await session.commit()
        logger.info("✅ Инициализация BotConfig завершена")


if __name__ == "__main__":
    asyncio.run(init_default_config())
