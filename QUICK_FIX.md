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
sudo docker-compose down
sudo docker-compose up -d
```

### Шаг 3: Исправить sequence в базе данных

**Вариант A: Через bash скрипт (рекомендуется)** ⭐

```bash
chmod +x scripts/reset_sequence.sh
sudo ./scripts/reset_sequence.sh
```

**Вариант B: Вручную через psql**

```bash
# ОДНА команда
sudo docker-compose exec postgres psql -U buyout_user -d buyout_bot -c "
SELECT setval(
    pg_get_serial_sequence('products', 'id'),
    COALESCE((SELECT MAX(id) FROM products), 0) + 1,
    false
);
"
```

**Вариант C: Через Alembic**

```bash
sudo docker-compose exec bot alembic upgrade head
```

### Шаг 4: Проверить

1. Откройте веб-панель в боте: `/admin`
2. Нажмите "➕ Добавить товар"
3. Товар должен создаться без ошибок

## Проверка что всё работает

```bash
# Проверить текущее значение sequence
sudo docker-compose exec postgres psql -U buyout_user -d buyout_bot -c "
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

## Важная информация

⚠️ **Параметры вашей БД (из .env и docker-compose.yml):**
- **Имя БД:** `buyout_bot`
- **Пользователь:** `buyout_user` 
- **Контейнер бота:** `bot`
- **Контейнер БД:** `postgres`

⚠️ **Все команды docker-compose нужно запускать с `sudo`!**

## Если всё ещё не работает

### Проверить имя контейнера

```bash
sudo docker-compose ps
```

### Посмотреть логи

```bash
# Логи бота
sudo docker-compose logs -f bot

# Логи PostgreSQL
sudo docker-compose logs -f postgres
```

### Пересоздать базу данных (ВНИМАНИЕ: удалит все данные!)

```bash
# Остановить контейнеры и удалить тома
sudo docker-compose down -v

# Запустить заново
sudo docker-compose up -d

# Применить миграцию
sudo docker-compose exec bot alembic upgrade head
```

## Что было исправлено

✅ Исправлен импорт в `alembic/env.py`  
✅ Добавлен SQL скрипт для ручного сброса sequence  
✅ Добавлен bash скрипт с sudo и правильными параметрами  
✅ Миграция автоматически сбрасывает sequence  
✅ Все команды обновлены с правильными параметрами  

## Следующие шаги

После того как всё заработает:
1. Протестировать создание/удаление товаров
2. Проверить процесс модерации
3. Создать Pull Request согласно [GITFLOW.md](GITFLOW.md)

---

**Нужна помощь?** Откройте Issue на GitHub с описанием проблемы и вывод команды:
```bash
sudo docker-compose logs --tail=50 bot
```
