# 🚀 Telegram Buyout Bot v2.0

Бот для автоматизации выкупов товаров со 100% кэшбэком.

## ✨ Основные возможности v2.0

### 🔄 Пошаговая воронка
- Пользователь проходит 5 четких шагов
- Каждый шаг - отдельное сообщение с кнопкой
- Никакой путаницы - просто и понятно

### 🌐 Telegram Web App
- **Удобная админ-панель** прямо в Telegram
- **Редактирование товаров** без кода
- **Полная настройка текстов** бота
- **Адаптивный дизайн** под темную/светлую тему

### ✅ Модерация с защитой от скама
- Админ видит **все 4 скриншота** перед выплатой
- Подтверждение со скрином перевода
- Отклонение с указанием причины
- **Google Sheets обновляется только после подтверждения**

### 📊 Улучшенная аналитика
- **Реальтайм обновления** воронки (Лис2)
- **Только завершенные** заказы в отчете (Лис1)

---

## 🛠 Установка

### Предварительные требования

- Docker & Docker Compose
- Telegram Bot Token (от [@BotFather](https://t.me/BotFather))
- Google Service Account (для Google Sheets)
- **HTTPS домен** (для Telegram Web App) или ngrok

### Шаг 1: Клонирование репозитория

```bash
git clone https://github.com/shogeo/telegram-buyout-bot.git
cd telegram-buyout-bot
git checkout feature/web-admin-major-refactor
```

### Шаг 2: Настройка переменных окружения

```bash
cp .env.example .env
nano .env
```

**Важные параметры:**

```env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789,987654321
WEBAPP_URL=https://your-domain.com  # ИЛИ https://xxxxx.ngrok.io
GOOGLE_SPREADSHEET_ID=your_spreadsheet_id
```

### Шаг 3: Google Service Account

1. Создайте Service Account в [Google Cloud Console](https://console.cloud.google.com/)
2. Скачайте JSON-ключ
3. Сохраните как `credentials.json` в корне проекта
4. Дайте доступ к таблице (email из JSON)

### Шаг 4: Запуск

```bash
sudo docker-compose up -d --build
sudo docker-compose logs -f bot
```

### Шаг 5: Инициализация конфигурации

Конфигурация инициализируется автоматически при первом запуске.

Если нужно переинициализировать:

```bash
sudo docker exec -it buyout_bot python -m bot.utils.init_bot_config
```

---

## 🔧 Настройка HTTPS для Web App

### Вариант 1: Nginx + SSL сертификат

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Вариант 2: ngrok (для тестирования)

```bash
ngrok http 8000
```

Затем обновите `WEBAPP_URL` в `.env` на URL от ngrok.

---

## 📚 Использование

### Для администратора

1. Отправьте `/admin` в бота
2. Нажмите "📝 Открыть настройки"
3. Настройте товары и тексты

**Вкладки в Web App:**
- 🛍️ **Товары**: Редактирование 4-х слотов
- 📝 **Тексты**: Настройка всех сообщений бота

**Модерация заказов:**
- Получаете уведомление со всеми скриншотами
- Нажмите "✅ Подтвердить" → Отправьте скрин перевода
- Или "❌ Отклонить" → Укажите причину

### Для пользователя

1. Нажать `/start`
2. "🛋️ Выбрать товар"
3. Прочитать инструкцию
4. Пройти 5 шагов (корзина, покупка, получение, отзыв, реквизиты)
5. Дождаться подтверждения от админа

---

## 📊 Структура проекта

```
telegram-buyout-bot/
├── bot/
│   ├── api/
│   │   └── webapp_api.py          # FastAPI эндпоинты
│   ├── database/
│   │   ├── models.py              # BotConfig, Product, Order
│   │   └── database.py
│   ├── handlers/
│   │   ├── client_new.py          # Пошаговая воронка
│   │   └── admin_new.py           # Модерация
│   ├── keyboards/
│   ├── services/
│   │   └── sheets_service.py
│   ├── states/
│   ├── utils/
│   │   └── init_bot_config.py     # Инициализация текстов
│   └── web_app/
│       └── index.html             # Telegram Web App UI
├── main.py                        # Главный файл (бот + FastAPI)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── MIGRATION_GUIDE.md         # Гайд по миграции
```

---

## ⚙️ Настраиваемые тексты

Все тексты редактируются через Web App:

- `welcome_message` - Приветствие
- `products_select_text` - Текст выбора товара
- `step_1_message` - Шаг 1 (корзина)
- `step_2_message` - Шаг 2 (покупка)
- `step_3_message` - Шаг 3 (получение)
- `step_4_message` - Шаг 4 (отзыв)
- `step_5_message` - Шаг 5 (реквизиты)
- `order_pending_message` - Ожидание модерации
- `payment_sent_message` - Выплата произведена

---

## 🐛 Отладка

### Просмотр логов

```bash
sudo docker-compose logs -f bot
```

### Перезапуск

```bash
sudo docker-compose restart bot
```

### Полная пересборка

```bash
sudo docker-compose down
sudo docker-compose up -d --build
```

---

## 🔗 Полезные ссылки

- [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) - Полный гайд по миграции
- [CHANGELOG_V2.md](./CHANGELOG_V2.md) - Все изменения v2.0
- [Telegram Web Apps Documentation](https://core.telegram.org/bots/webapps)

---

## 💬 Поддержка

Если у вас возникли вопросы:

1. Проверьте [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md)
2. Посмотрите логи: `sudo docker-compose logs bot`
3. Откройте Issue на GitHub

---

**Удачи!** 🚀
