# Исправление ошибки "duplicate key value violates unique constraint products_pkey"

## Проблема

При попытке создать новый товар через веб-панель возникала ошибка:

```
asyncpg.exceptions.UniqueViolationError: duplicate key value violates unique constraint "products_pkey"
DETAIL: Key (id)=(1) already exists.
```

### Причина

PostgreSQL sequence для `products.id` не был синхронизирован с существующими данными:
- В таблице уже есть записи с ID 1-4
- Sequence начинается с 1, что вызывает конфликт при INSERT

## Решение

Миграция теперь автоматически сбрасывает sequence:

```sql
SELECT setval(
    pg_get_serial_sequence('products', 'id'),
    COALESCE((SELECT MAX(id) FROM products), 0) + 1,
    false
);
```

Эта команда:
1. Находит максимальный ID в таблице
2. Устанавливает sequence на MAX(id) + 1
3. Следующий INSERT получит корректный ID

## Как применить

### Вариант 1: Применить миграцию

```bash
# 1. Переключиться на fix ветку
git checkout fix/product-id-sequence
git pull origin fix/product-id-sequence

# 2. Перезапустить Docker
docker-compose down
docker-compose up -d

# 3. Применить миграцию
docker-compose exec buyout_bot alembic upgrade head

# 4. Проверить логи
docker-compose logs -f buyout_bot
```

### Вариант 2: Ручной сброс sequence (если миграция уже применена)

Если вы уже применили миграцию без сброса sequence:

```bash
# Подключиться к PostgreSQL
docker-compose exec postgres psql -U buyout_user -d buyout_bot_db

# Выполнить SQL
SELECT setval(
    pg_get_serial_sequence('products', 'id'),
    COALESCE((SELECT MAX(id) FROM products), 0) + 1,
    false
);

# Выйти
\q
```

### Вариант 3: Переприменить миграцию

Если нужно переприменить миграцию:

```bash
# Откатить миграцию
docker-compose exec buyout_bot alembic downgrade -1

# Применить заново
docker-compose exec buyout_bot alembic upgrade head
```

## Проверка

После применения исправления:

1. Откройте веб-панель: `/admin` в боте
2. Нажмите "➕ Добавить товар"
3. Товар должен создаться без ошибок

Проверить sequence в базе:

```sql
-- Показать текущее значение sequence
SELECT last_value FROM products_id_seq;

-- Показать MAX ID в таблице
SELECT MAX(id) FROM products;
```

`last_value` должен быть больше `MAX(id)`.

## Что было исправлено

✅ Добавлен сброс sequence в миграцию  
✅ Sequence теперь синхронизирован с существующими данными  
✅ Создание новых товаров работает корректно  

## Дальнейшие шаги (по GitFlow)

См. [GITFLOW.md](GITFLOW.md) для полной инструкции.

```bash
# 1. Создать Pull Request:
#    fix/product-id-sequence -> fix/imports-and-docker

# 2. После мерджа создать PR:
#    fix/imports-and-docker -> feature/improvements

# 3. Тестирование feature/improvements

# 4. Создать develop ветку (если нет) и мердж в нее

# 5. После полного тестирования: develop -> main
```

## Ссылки

- Ветка: [fix/product-id-sequence](https://github.com/shogeo/telegram-buyout-bot/tree/fix/product-id-sequence)
- Коммит с исправлением: [0200948](https://github.com/shogeo/telegram-buyout-bot/commit/0200948380768bdb1558f387071f4da529974b6a)
- GitFlow: [GITFLOW.md](GITFLOW.md)
