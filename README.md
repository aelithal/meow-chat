# 💬 Meow Chat

Веб-приложение для обмена сообщениями в реальном времени на основе WebSocket поверх TCP. Поддерживает несколько пользователей и комнат одновременно.

## Стек технологий

**Backend**
- Python 3.11+
- FastAPI — REST API и WebSocket
- SQLAlchemy (async) — ORM
- PostgreSQL — база данных
- JWT (python-jose) — аутентификация
- bcrypt — хеширование паролей
- Uvicorn — ASGI сервер

**Frontend**
- HTML + CSS + JavaScript (без фреймворков)
- WebSocket API

## Структура проекта

```
meow-chat/
├── backend/
│   ├── main.py          # точка входа, FastAPI app
│   ├── auth.py          # регистрация, вход, JWT
│   ├── chat.py          # комнаты, сообщения, WebSocket
│   ├── models.py        # SQLAlchemy модели
│   ├── schemas.py       # Pydantic схемы
│   ├── database.py      # подключение к БД
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── login.html
    ├── register.html
    ├── chat.html
    ├── style.css
    ├── app.js           # HTTP клиент
    └── ws-client.js     # WebSocket клиент
```

## Запуск локально

### 1. Клонировать репозиторий

```bash
git clone https://github.com/aelithal/meow-chat.git
cd meow-chat
```

### 2. Создать базу данных PostgreSQL

```bash
psql -U postgres
```

```sql
CREATE DATABASE chatdb;
\q
```

### 3. Настроить переменные окружения

```bash
cd backend
cp .env.example .env
```

Открой `.env` и заполни значения:

```
DATABASE_URL=postgresql+asyncpg://postgres:ваш_пароль@localhost:5432/chatdb
SECRET_KEY=сгенерируйте_случайную_строку_минимум_32_символа
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Сгенерировать `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Установить зависимости

```bash
pip install -r requirements.txt
```

### 5. Запустить бэкенд

```bash
uvicorn main:app --reload
```

Бэкенд будет доступен на `http://localhost:8000`.  
Документация API: `http://localhost:8000/docs`.

### 6. Запустить фронтенд

#### Chrome / Edge

Просто откройте файл `frontend/login.html` в браузере.

#### Firefox и другие Firefox-based браузеры

Firefox ограничивает `localStorage` для `file://` протокола, поэтому нужно запустить локальный HTTP-сервер:

```bash
cd frontend
python -m http.server 5500
```

Затем откройте в браузере: `http://localhost:5500/login.html`