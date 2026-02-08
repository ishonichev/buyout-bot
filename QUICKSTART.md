# ⚡ Быстрый запуск

Если у вас уже есть:
- Токен бота Telegram
- Google Sheets credentials.json
- Telegram ID админа

## 1. Клонируйте репозиторий

```bash
git clone https://github.com/shogeo/telegram-buyout-bot.git
cd telegram-buyout-bot
```

## 2. Создайте .env файл

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```env
# Telegram Bot
BOT_TOKEN=ВАШ_ТОКЕН_БОТА
ADMIN_IDS=ВАШ_TELEGRAM_ID

# Database (Docker)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=buyout_bot
POSTGRES_USER=postgres
POSTGRES_PASSWORD=ваш_пароль

# Redis (Docker)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Google Sheets
GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json
GOOGLE_SPREADSHEET_ID=ВАШ_SHEET_ID
```

## 3. Поместите credentials.json

```bash
cp ~/Downloads/ваш-credentials.json ./credentials.json
```

## 4. Запустите

```bash
sudo docker-compose up -d --build
```

## 5. Проверьте логи

```bash
sudo docker-compose logs -f bot
```

Должны увидеть:
```
INFO - База данных инициализирована
INFO - Сервисы инициализированы
INFO - Бот запущен в режиме polling
```

## 6. Протестируйте

1. Откройте бота в Telegram
2. Отправьте `/start`
3. Отправьте `/admin`

---

## Полезные команды

```bash
# Просмотр статуса
sudo docker-compose ps

# Перезапуск
sudo docker-compose restart bot

# Остановка
sudo docker-compose down

# Обновление
git pull origin main
sudo docker-compose down
sudo docker-compose up -d --build
```

Подробная инструкция: [SETUP.md](SETUP.md)
