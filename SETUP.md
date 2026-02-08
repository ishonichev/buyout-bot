# 🛠️ Пошаговая настройка

Этот гайд поможет развернуть бота с нуля за 15 минут.

## Шаг 1: Создание бота в Telegram

1. Откройте [@BotFather](https://t.me/BotFather)
2. Отправьте `/newbot`
3. Введите имя бота (например: `WB Buyout Bot`)
4. Введите username (например: `wb_buyout_bot`)
5. **Скопируйте токен** в безопасное место

## Шаг 2: Получение Telegram ID

1. Откройте [@userinfobot](https://t.me/userinfobot)
2. Отправьте `/start`
3. Скопируйте ваш **ID** (это будет админ ID)

## Шаг 3: Google Sheets API

### 3.1 Создание проекта в Google Cloud

1. Перейдите на [console.cloud.google.com](https://console.cloud.google.com/)
2. Создайте новый проект (name: `buyout-bot-project`)
3. Выберите проект → **API и сервисы** → **Библиотека**
4. Найдите **Google Sheets API** → Нажмите **Включить**

### 3.2 Создание сервисного аккаунта

1. Перейдите в **IAM и администрирование** → **Сервисные аккаунты**
2. Нажмите **Создать сервисный аккаунт**
   - Name: `buyout-bot-service`
   - Role: **Viewer** (достаточно)
3. Нажмите на созданный аккаунт → **Ключи** → **Добавить ключ** → **Создать новый ключ**
4. Тип: **JSON** → Скачается файл `buyout-bot-project-xxxxx.json`
5. **Переименуйте** его в `google_credentials.json`

### 3.3 Создание Google Sheets таблицы

1. Откройте [Google Sheets](https://sheets.google.com/)
2. Создайте новую таблицу: **WB Buyout Analytics**
3. Создайте два листа:

#### Лист 1: "Заявки"
Вставьте заголовки в первую строку:
```
№ | Ник тг | Корзина | Покупка | Выкуп | Отзыв | Оплата (сумма)
```

#### Лист 2: "Аналитика"
Вставьте заголовки в первую строку:
```
 | Зашли в бот | Запустили бот | Нажали кнопку 1 | Нажали кнопку 2 | ... | Нажали кнопку 7
Кол-во |  0  |  0  |  0  |  0  | ... |  0
%   | 100% | 100% | 100% | 100% | ... | 100%
```

4. **Скопируйте ID таблицы** из URL:
   ```
   https://docs.google.com/spreadsheets/d/[THIS_IS_YOUR_SHEET_ID]/edit
   ```

5. **Расшарьте таблицу:**
   - Нажмите **Предоставить доступ**
   - Вставьте email из `google_credentials.json` (поле `client_email`)
   - Выберите роль: **Редактор**

## Шаг 4: Настройка проекта

### 4.1 Клонируйте репозиторий
```bash
git clone https://github.com/shogeo/telegram-buyout-bot.git
cd telegram-buyout-bot
```

### 4.2 Поместите `google_credentials.json`
Скопируйте скачанный JSON-ключ в корень проекта:
```bash
cp ~/Downloads/buyout-bot-project-xxxxx.json ./google_credentials.json
```

### 4.3 Создайте `.env` файл
```bash
cp .env.example .env
nano .env  # или используйте ваш любимый редактор
```

**Заполните все переменные:**
```env
# Telegram Bot
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz  # из Шага 1
ADMIN_IDS=123456789,987654321                    # из Шага 2 (через запятую)

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/buyout_bot

# Redis
REDIS_URL=redis://redis:6379/0

# Google Sheets
GOOGLE_SHEET_ID=1AbC2DeF3GhI4JkL5MnO6PqR7StU8VwX9YzA  # из Шага 3.3
GOOGLE_SERVICE_ACCOUNT_FILE=google_credentials.json
```

## Шаг 5: Запуск

### 5.1 Сборка и запуск
```bash
docker-compose up -d --build
```

### 5.2 Проверка статуса
```bash
# Проверить что все контейнеры запущены
docker-compose ps

# Просмотр логов
docker-compose logs -f bot
```

Вы должны увидеть:
```
INFO     - Bot started successfully
INFO     - Polling started
```

### 5.3 Первый запуск

1. Откройте Telegram
2. Найдите вашего бота (по username)
3. Отправьте `/start`
4. Как админ, отправьте `/admin`

## Шаг 6: Настройка товаров

1. Отправьте `/admin` в бота
2. Нажмите **Редактировать товар**
3. Выберите слот (1-4)
4. Заполните:
   - **Название:** `iPhone 15 Pro Max`
   - **Ссылка:** `https://www.wildberries.ru/catalog/123456/detail.aspx`
   - **Инструкция:** Текст инструкции с ссылкой
   - **Сумма кэшбэка:** `550`
5. Нажмите **Активировать**

## ✅ Готово!

Бот запущен и готов к работе. Теперь вы можете:
- Поделиться ссылкой на бота с клиентами
- Отслеживать заявки в Google Sheets
- Анализировать конверсию воронки

---

## Частые вопросы

**Q: Бот не отвечает на сообщения**
- Проверьте логи: `docker-compose logs bot`
- Убедитесь что `BOT_TOKEN` правильный

**Q: Google Sheets не заполняются**
- Проверьте что таблица расшарена на email сервисного аккаунта
- Проверьте `GOOGLE_SHEET_ID` в `.env`

**Q: Как остановить бота?**
```bash
docker-compose down
```

**Q: Как перезапустить бота?**
```bash
docker-compose restart bot
```
