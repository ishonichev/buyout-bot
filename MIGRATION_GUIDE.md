# Инструкция по применению миграций

## Применение миграций в Docker

### Шаг 1: Переключение на ветку fix/imports-and-docker

```bash
git checkout fix/imports-and-docker
git pull origin fix/imports-and-docker
```

### Шаг 2: Остановить текущие контейнеры

```bash
docker-compose down
```

### Шаг 3: Применить миграцию

Есть два способа:

#### Способ 1: Выполнить миграцию внутри Docker-контейнера

```bash
# Запустить контейнеры
docker-compose up -d

# Выполнить миграцию
docker-compose exec buyout_bot alembic upgrade head
```

#### Способ 2: Запустить разовый контейнер для миграции

```bash
# Запустить только базу данных
docker-compose up -d postgres

# Выполнить миграцию
docker-compose run --rm buyout_bot alembic upgrade head

# Запустить все сервисы
docker-compose up -d
```

### Шаг 4: Проверить логи

```bash
docker-compose logs -f buyout_bot
```

Бот должен запуститься без ошибок.

## Что было добавлено

### 1. Поле `cashback` в таблице `products`
- Тип: `FLOAT`
- По умолчанию: `0.0`
- Не NULL

### 2. Поле `cashback_amount` в таблице `orders`
- Тип: `FLOAT`
- Может быть NULL
- Хранит сумму, введенную админом

### 3. Поддержка динамических товаров
- `products.id` теперь с `autoincrement`
- Нет ограничения на 4 товара
- Добавлены API методы для создания/удаления

## Откат миграции (если нужно)

```bash
docker-compose exec buyout_bot alembic downgrade -1
```

## Тестирование

После применения миграции:

1. Откройте веб-панель админа
2. Добавьте новый товар с кешбеком
3. Активируйте товар
4. Проверьте выбор товара в боте (должен отобразиться кешбек)
5. Создайте тестовый заказ и проверьте запрос суммы кешбека при модерации
