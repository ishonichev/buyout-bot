# Changelog

## [1.0.0] - 2026-02-08

### Fixed
- ✅ **Критическое**: Исправлена ошибка импорта `SessionLocal` → `async_session_maker` в `analytics_service.py`
- ✅ **Критическое**: Исправлены хосты базы данных в `.env.example`: `localhost` → `postgres` для Docker
- ✅ **Критическое**: Исправлен Redis хост в `.env.example`: `localhost` → `redis` для Docker
- ✅ **Критическое**: Удалено монтирование `./:/app` в `docker-compose.yml` (перезаписывало контейнер)
- ✅ Исправлена зависимость `gspread`: `6.1.4` → `6.0.2` (совместимость с `gspread-asyncio==2.0.0`)
- ✅ Исправлена логика аналитики в `client.py`: `bot_started` и `bot_visited` теперь на `/start`
- ✅ Создание папки `logs/` перед записью логов в `main.py`

### Added
- ✨ Healthchecks для PostgreSQL и Redis в `docker-compose.yml`
- ✨ `QUICKSTART.md` - быстрая инструкция по запуску
- ✨ Обновлен `SETUP.md` с правильными переменными окружения
- ✨ `CHANGELOG.md` для отслеживания изменений

### Improved
- 🚀 Оптимизирован `docker-compose.yml`: теперь бот ждет полного запуска баз данных
- 🚀 Улучшенная структура волюмов Docker: только `logs/` и `credentials.json`
- 🚀 Комментарии в `.env.example` для ясности

## Как обновить

```bash
git pull origin main

# Обновите .env файл:
# POSTGRES_HOST=postgres  (вместо localhost)
# REDIS_HOST=redis        (вместо localhost)

sudo docker-compose down
sudo docker-compose up -d --build
```

## Проверка

```bash
sudo docker-compose logs -f bot
```

Должны увидеть:
- `INFO - База данных инициализирована`
- `INFO - Сервисы инициализированы`
- `INFO - Бот запущен в режиме polling`
