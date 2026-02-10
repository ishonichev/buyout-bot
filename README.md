# Telegram Buyout Bot

Бот для автоматизации выкупов товаров со 100% кэшбэком.

## Возможности

- ✅ **Автоматическое управление товарами**: 4 слота для товаров
- ✅ **Пошаговый процесс**: корзина → покупка → получение → отзыв
- ✅ **Google Sheets интеграция**: автозаполнение таблиц
- ✅ **Аналитика воронки**: отслеживание конверсии
- ✅ **Сбор скриншотов**: все фото в одном сообщении админу
- ✅ **Отмена прогресса**: пользователь может отменить заказ

## Технологии

- Python 3.11+
- aiogram 3.x
- PostgreSQL
- Redis
- Google Sheets API
- Docker & Docker Compose

## Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/shogeo/telegram-buyout-bot.git
cd telegram-buyout-bot
```

### 2. Настройка переменных окружения

Скопируйте `.env.example` в `.env` и заполните значения:

```bash
cp .env.example .env
nano .env
```

**Обязательные параметры:**

```env
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_IDS=123456789,987654321
POSTGRES_PASSWORD=strong_password_here
GOOGLE_SPREADSHEET_ID=your_google_spreadsheet_id
```

### 3. Настройка Google Sheets

1. Создайте проект в [Google Cloud Console](https://console.cloud.google.com/)
2. Включите Google Sheets API
3. Создайте Service Account
4. Скачайте JSON ключ и сохраните как `credentials.json`
5. Создайте Google таблицу и дайте доступ Service Account email

### 4. Запуск

```bash
docker-compose up -d --build
```

### 5. Проверка логов

```bash
docker-compose logs -f bot
```

## Структура проекта

```
telegram-buyout-bot/
├── bot/
│   ├── handlers/          # Обработчики сообщений
│   ├── keyboards/         # Клавиатуры
│   ├── states/            # FSM состояния
│   ├── database/          # Модели БД
│   ├── services/          # Сервисы (Sheets, Analytics)
│   └── middlewares/       # Middleware
├── main.py               # Точка входа
├── docker-compose.yml    # Docker конфигурация
└── requirements.txt      # Python зависимости
```

## Использование

### Для клиентов

1. Начните чат с ботом: `/start`
2. Нажмите "🛋️ Выбрать товар"
3. Выберите товар и следуйте инструкциям
4. Отправляйте скриншоты на каждом этапе
5. Укажите реквизиты для кэшбэка

### Для администраторов

1. Откройте админ-панель: `/admin`
2. "Редактировать товар" - управление товарами
3. "Статистика" - аналитика пользователей
4. Получайте уведомления о новых заказах со всеми фото

## Google Sheets структура

### Лист1 (Заявки)

| № | Ник тг | Корзина | Покупка | Выкуп | Отзыв | Оплата (сумма) |
|------|-----------|----------|----------|--------|--------|------------------|
| 1    | @user     | 01.01.26 | 01.01.26 | 02.01.26 | 03.01.26 | 550 |

### Лист2 (Аналитика)

|        | Зашли в бот | Запустили бот | Кнопка 1 | ... |
|--------|--------------|-----------------|-----------|-----|
| Кол-во | 100          | 80              | 75        | ... |
| %      | 100%         | 80.0%           | 93.8%     | ... |

## Обновление

```bash
git pull origin main
docker-compose down
docker-compose up -d --build
```

## Поддержка

При возникновении проблем:

1. Проверьте логи: `docker-compose logs bot`
2. Перезапустите: `docker-compose restart bot`
3. Откройте issue в GitHub

## Лицензия

MIT License
