# Быстрое исправление ошибки "duplicate key products_pkey"

## Проблема

При добавлении нового товара через веб-панель возникает ошибка:
```
asyncpg.exceptions.UniqueViolationError: duplicate key value violates unique constraint "products_pkey"
DETAIL: Key (id)=(1) already exists.
```

## Быстрое решение (1 минута)

### Шаг 1: Обновить код

```bash
git checkout fix/product-id-sequence
git pull origin fix/product-id-sequence
```

### Шаг 2: Перезапустить Docker

```bash
docker-compose down
docker-compose up -d
```

### Шаг 3: Исправить sequence в базе данных

**Вариант A: Через SQL скрипт (рекомендуется)**

```bash
# Скопировать скрипт в контейнер с PostgreSQL
docker-compose exec -T postgres psql -U buyout_user -d buyout_bot_db < scripts/reset_products_sequence.sql
```

**Вариант B: Вручную через psql**

```bash
# Подключиться к базе данных
docker-compose exec postgres psql -U buyout_user -d buyout_bot_db

# Выполнить команду сброса sequence
SELECT setval(
    pg_get_serial_sequence('products', 'id'),
    COALESCE((SELECT MAX(id) FROM products), 0) + 1,
    false
);

# Выйти
\q
```

### Шаг 4: Проверить

1. Откройте веб-панель в боте: `/admin`
2. Нажмите "⊕ Добавить товар"
3. Товар должен создаться без ошибок

## Если используете Alembic миграции

Если вы хотите применить миграцию через Alembic:

```bash
# Применить миграцию (имя контейнера - bot, не buyout_bot!)
docker-compose exec bot alembic upgrade head
```

**Примечание:** Контейнер называется `bot` в вашем docker-compose.yml, а не `buyout_bot`!

## Проверка что всё работает

```bash
# Проверить текущее значение sequence
docker-compose exec postgres psql -U buyout_user -d buyout_bot_db -c "
SELECT 
    'MAX ID' as info, COALESCE(MAX(id), 0) as value FROM products
UNION ALL
SELECT 
    'Sequence' as info, last_value as value FROM products_id_seq;
"
```

**Результат должен быть примерно таким:**
```
   info    | value 
-----------+-------
 MAX ID    |     4
 Sequence  |     5
```

Sequence должен быть больше чем MAX ID!

## Если всё ещё не работает

### Проверить имя контейнера

```bash
# Посмотреть список запущенных контейнеров
docker-compose ps

# Найти контейнер с ботом (может называться bot, buyout_bot, telegram-buyout-bot_bot)
```

### Посмотреть логи

```bash
# Логи бота
docker-compose logs -f bot

# Если контейнер называется по-другому:
docker-compose logs -f buyout_bot
```

### Пересоздать базу данных (ВНИМАНИЕ: удалит все данные!)

```bash
# Остановить контейнеры
docker-compose down -v

# Запустить заново
docker-compose up -d

# Применить миграцию
docker-compose exec bot alembic upgrade head
```

## Что было исправлено

✅ Исправлен импорт в `alembic/env.py` (DATABASE_URL → settings.DATABASE_URL)
✅ Добавлен SQL скрипт для ручного сброса sequence
✅ Миграция автоматически сбрасывает sequence
✅ Добавлена документация для быстрого исправления

## Следующие шаги

После того как всё заработает:
1. Протестировать создание/удаление товаров
2. Проверить процесс модерации
3. Создать Pull Request согласно [GITFLOW.md](GITFLOW.md)

---

**Нужна помощь?** Откройте Issue на GitHub с описанием проблемы и вывод команды:
```bash
docker-compose logs --tail=50 bot
```
