# Справочная информация

**Разделы документации:**
[Главная](index.md) |
[Быстрый старт](quick-start.md) |
[Установка и настройка](installation.md) |
[Руководство пользователя](user-guide.md) |
[Справочная информация](reference.md)

---

Раздел содержит технические сведения об API Meow Chat: REST-эндпоинты, WebSocket-протокол, модель данных, сообщения об ошибках и команды диагностики. Примеры используют адрес `http://meow-chat.net`, при локальном запуске замените его на `http://localhost:8000`.

Интерактивная документация FastAPI (Swagger UI) доступна по адресу `/docs`.

## Общие сведения

- Данные передаются в кодировке UTF-8, даты — в формате ISO 8601.
- Тело POST-запросов — JSON (`Content-Type: application/json`).
- Защищённые эндпоинты требуют заголовок `Authorization: Bearer <token>`.
- Токен — JWT (алгоритм HS256), в поле `sub` хранится идентификатор пользователя.
- Для WebSocket токен передаётся в query-параметре `token`.

## REST API

| Метод | Путь | Авторизация | Описание | Успешный ответ |
|---|---|---|---|---|
| POST | `/auth/register` | нет | Регистрация пользователя | `201` |
| POST | `/auth/login` | нет | Вход, получение токена | `200` |
| GET | `/auth/me` | да | Данные текущего пользователя | `200` |
| GET | `/rooms` | да | Список комнат | `200` |
| POST | `/rooms` | да | Создание комнаты | `201` |
| DELETE | `/rooms/{room_id}` | да | Удаление комнаты и её сообщений | `204` |
| GET | `/rooms/{room_id}/messages` | да | История сообщений | `200` |
| GET | `/health` | нет | Проверка работоспособности | `200` |

### Входные данные

| Эндпоинт | Поле | Тип | Требования |
|---|---|---|---|
| `/auth/register` | `username` | string | 3–50 символов, только буквы и цифры |
| `/auth/register` | `password` | string | не менее 6 символов |
| `/auth/login` | `username`, `password` | string | обязательные |
| `/rooms` (POST) | `name` | string | 2–100 символов, уникальное |
| `/rooms/{room_id}/messages` | `limit` | integer (query) | необязательный, по умолчанию 50 |

### Примеры запросов

Регистрация:

```bash
curl -X POST http://meow-chat.net/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "ivanov", "password": "secret123"}'
```

Ответ `201 Created`:

```json
{ "id": 5, "username": "ivanov", "created_at": "2026-09-24T10:15:00Z" }
```

Вход (эндпоинт принимает JSON, а не форму):

```bash
curl -X POST http://meow-chat.net/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "ivanov", "password": "secret123"}'
```

Ответ `200 OK`:

```json
{ "access_token": "eyJhbGciOiJIUzI1NiIs…", "token_type": "bearer" }
```

Создание комнаты:

```bash
curl -X POST http://meow-chat.net/rooms \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "general"}'
```

Ответ `201 Created`:

```json
{ "id": 3, "name": "general", "created_at": "2026-09-24T10:20:00Z" }
```

Получение истории:

```bash
curl -H "Authorization: Bearer <token>" \
  "http://meow-chat.net/rooms/3/messages?limit=50"
```

Ответ `200 OK` (сообщения от старых к новым):

```json
[
  {
    "id": 12,
    "text": "Привет!",
    "created_at": "2026-09-24T10:22:00Z",
    "author": { "id": 5, "username": "ivanov", "created_at": "2026-09-24T10:15:00Z" }
  }
]
```

Команда нужна для ручной проверки API. Токен берётся из ответа `/auth/login`, подставьте его вместо `<token>`.

## WebSocket

| Адрес | Назначение |
|---|---|
| `ws://meow-chat.net/ws/{room_id}?token=<token>` | Обмен сообщениями в комнате |
| `ws://meow-chat.net/ws/global?token=<token>` | События создания и удаления комнат |

Отправка сообщения в комнату (пустой текст игнорируется):

```json
{ "text": "Привет всем!" }
```

Проверить соединение можно утилитой `wscat`:

```bash
wscat -c "ws://meow-chat.net/ws/3?token=<token>"
```

### События от сервера

| Поле `type` | Когда приходит | Поля |
|---|---|---|
| `message` | Новое сообщение в комнате (получает и отправитель) | `id`, `text`, `username`, `user_id`, `created_at` |
| `system` | Участник вошёл в комнату или вышел из неё | `text` |
| `room_created` | Создана комната (канал `/ws/global`) | `room` (`id`, `name`, `created_at`) |
| `room_deleted` | Комната удалена (комната и `/ws/global`) | `room_id` |

Пример события `message`:

```json
{
  "type": "message",
  "id": 13,
  "text": "Привет всем!",
  "username": "ivanov",
  "user_id": 5,
  "created_at": "2026-09-24T10:25:00Z"
}
```

### Коды закрытия

| Код | Причина | Поведение клиента |
|---|---|---|
| `4001` | Токен недействителен или отсутствует | Клиент не переподключается |
| `4004` | Комната не найдена | Клиент не переподключается |
| другие | Обрыв связи | Автоматическое переподключение с задержкой 1,5 с, до 15 с |

## Модель данных

| Таблица | Поле | Тип | Описание |
|---|---|---|---|
| `users` | `id` | integer, PK | Идентификатор |
| `users` | `username` | varchar(50), unique | Имя пользователя |
| `users` | `hashed_password` | varchar(255) | Хеш пароля (bcrypt) |
| `users` | `created_at` | timestamptz | Дата создания |
| `rooms` | `id` | integer, PK | Идентификатор |
| `rooms` | `name` | varchar(100), unique | Название комнаты |
| `rooms` | `created_at` | timestamptz | Дата создания |
| `messages` | `id` | integer, PK | Идентификатор |
| `messages` | `text` | text | Текст сообщения |
| `messages` | `user_id` | integer, FK → `users.id` | Автор |
| `messages` | `room_id` | integer, FK → `rooms.id` | Комната |
| `messages` | `created_at` | timestamptz | Время отправки |

## Сообщения об ошибках

| Ответ | Причина | Действие |
|---|---|---|
| `409` «Пользователь с таким именем уже существует» | Имя занято | Выбрать другое имя |
| `401` «Неверное имя пользователя или пароль» | Неверные учётные данные | Проверить данные |
| `401` «Неверный или истёкший токен» | Токен недействителен или истёк | Войти заново; на сервере проверить `SECRET_KEY` и время (`timedatectl`) |
| `409` «Комната с таким именем уже существует» | Название занято | Выбрать другое название |
| `404` «Комната не найдена» | Неверный `room_id` | Обновить список комнат |
| `422 Unprocessable Entity` | Нарушены ограничения полей | Исправить данные по таблице входных данных |
| `502 Bad Gateway` (Nginx) | Бэкенд недоступен | Проверить `systemctl status meow-chat` и `journalctl -u meow-chat -n 100` |

## Диагностика и обслуживание

| Задача | Команда |
|---|---|
| Состояние бэкенда | `systemctl is-active meow-chat` |
| Ответ бэкенда | `curl -s http://127.0.0.1:8000/health` |
| Проверка конфигурации Nginx | `sudo nginx -t` |
| Состояние PostgreSQL | `pg_isready -h 127.0.0.1 -p 5432` |
| Журнал бэкенда | `journalctl -u meow-chat -n 100` |
| Размер журнала | `journalctl --disk-usage` |
| Очистка журнала | `sudo journalctl --vacuum-time=30d` |
| Резервная копия БД | `pg_dump -h 127.0.0.1 -U postgres -d chatdb -F c -f /var/backups/meow-chat/chatdb_$(date +%F).dump` |
| Проверка копии | `pg_restore -l /var/backups/meow-chat/chatdb_<дата>.dump` |

Диагностику рекомендуется выполнять ежедневно, а резервную копию создавать по расписанию (в эксплуатации — ежедневно в 03:00 через `cron`, хранение 14 дней).

Установку и настройку описывает раздел [Установка и настройка](installation.md), работу пользователя — [Руководство пользователя](user-guide.md).

[← Вернуться на главную страницу](index.md)
