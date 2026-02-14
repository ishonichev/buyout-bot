# GitFlow для проекта telegram-buyout-bot

## Структура веток

```
main (production)
  └─ develop (staging/development)
      ├─ feature/* (новый функционал)
      ├─ fix/* (исправления)
      └─ hotfix/* (критические исправления)
```

## Ветки

### `main`
- **Назначение:** Production-готовый код
- **Защищена:** Да, только PR
- **Deploy:** Автоматически на production

### `develop`
- **Назначение:** Разработка и тестирование
- **Защищена:** Да, только PR
- **Deploy:** Staging/test сервер

### `feature/*`
- **Назначение:** Новый функционал
- **Создается от:** `develop`
- **Мерджится в:** `develop`
- **Пример:** `feature/cashback-support`, `feature/dynamic-products`

### `fix/*`
- **Назначение:** Исправления багов
- **Создается от:** `develop`
- **Мерджится в:** `develop`
- **Пример:** `fix/imports-and-docker`, `fix/product-id-sequence`

### `hotfix/*`
- **Назначение:** Критические исправления в production
- **Создается от:** `main`
- **Мерджится в:** `main` И `develop`
- **Пример:** `hotfix/critical-crash`

## Workflow

### 1. Разработка новой фичи

```bash
# Перейти на develop
git checkout develop
git pull origin develop

# Создать feature ветку
git checkout -b feature/new-feature

# Разработка...
git add .
git commit -m "feat: описание изменений"
git push origin feature/new-feature

# Создать Pull Request в develop
```

### 2. Исправление бага

```bash
# Перейти на develop
git checkout develop
git pull origin develop

# Создать fix ветку
git checkout -b fix/bug-description

# Исправление...
git add .
git commit -m "fix: описание исправления"
git push origin fix/bug-description

# Создать Pull Request в develop
```

### 3. Критическое исправление (hotfix)

```bash
# Перейти на main
git checkout main
git pull origin main

# Создать hotfix ветку
git checkout -b hotfix/critical-issue

# Исправление...
git add .
git commit -m "hotfix: описание"
git push origin hotfix/critical-issue

# Создать 2 Pull Request:
# 1. hotfix/critical-issue -> main
# 2. hotfix/critical-issue -> develop
```

### 4. Релиз

```bash
# Когда develop готов к production
# Создать Pull Request: develop -> main
# После мерджа создать tag:

git checkout main
git pull origin main
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

## Commit Message Стандарт

Используем Conventional Commits:

```
<type>: <description>

[optional body]

[optional footer]
```

### Types:
- `feat:` - новая функция
- `fix:` - исправление бага
- `docs:` - изменения в документации
- `style:` - форматирование кода
- `refactor:` - рефакторинг
- `test:` - добавление тестов
- `chore:` - рутинные задачи

### Примеры:

```bash
feat: добавить поддержку кешбека для товаров

fix: исправить ошибку импорта handlers

docs: обновить инструкцию по миграциям
```

## Pull Request Чеклист

Перед созданием PR проверьте:

- [ ] Код протестирован локально
- [ ] Все тесты проходят
- [ ] Нет конфликтов с целевой веткой
- [ ] Документация обновлена
- [ ] Commit messages соответствуют стандарту
- [ ] Описание PR заполнено

## Текущие ветки проекта

### Активные:
- `feature/improvements` - добавление кешбека, динамических товаров
- `fix/imports-and-docker` - исправление импортов и Docker
- `fix/product-id-sequence` - исправление sequence для products.id

### План:
1. Мердж `fix/product-id-sequence` в `fix/imports-and-docker`
2. Мердж `fix/imports-and-docker` в `feature/improvements`
3. Тестирование `feature/improvements`
4. Мердж `feature/improvements` в `develop` (создать если нужно)
5. Мердж `develop` в `main` после полного тестирования
