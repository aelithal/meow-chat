# Установка и настройка

**Разделы документации:**
[Главная](index.md) |
[Быстрый старт](quick-start.md) |
[Установка и настройка](installation.md) |
[Руководство пользователя](user-guide.md) |
[Справочная информация](reference.md)

---

Раздел описывает развёртывание Meow Chat на сервере под управлением Ubuntu Server: требования, установку, настройку, запуск в виде службы и проверку работоспособности. Для запуска на локальном компьютере достаточно [Быстрого старта](quick-start.md).

## Системные требования

### Сервер

| Параметр | Значение |
|---|---|
| Операционная система | Ubuntu Server (Linux) |
| Процессор | Intel Core i3 или аналогичный |
| Оперативная память | не менее 2 ГБ |
| Свободное место на диске | не менее 5 ГБ (с учётом журналов и резервных копий) |
| Python | 3.11 или новее |
| СУБД | PostgreSQL 14 и новее |
| Веб-сервер | Nginx |
| Сеть | статический IP-адрес, доменное имя, указывающее на сервер |

### Клиент

Браузер Chrome, Edge или Firefox актуальной версии, включённый JavaScript и разрешённый `localStorage`. Дополнительное ПО на устройстве пользователя не требуется.

### Сетевые порты

| Порт | Назначение | Доступ |
|---|---|---|
| 80/tcp | HTTP, Nginx (при HTTPS дополнительно 443/tcp) | извне |
| 22/tcp | SSH | только администраторы |
| 8000/tcp | бэкенд (Uvicorn) | только `127.0.0.1` |
| 5432/tcp | PostgreSQL | только `127.0.0.1` |

## Порядок установки

1. Создайте служебного пользователя и клонируйте проект:

```bash
   sudo adduser meowchat
   sudo -u meowchat -i
   git clone https://github.com/aelithal/meow-chat.git
   cd meow-chat
```

2. Создайте виртуальное окружение и установите зависимости:

```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
```

3. Создайте базу данных (под пользователем с правами `sudo`):

```bash
   sudo -u postgres psql -c "CREATE DATABASE chatdb;"
```

4. Создайте и заполните `.env` (см. [параметры](#параметры-настройки-env)).
5. [Укажите адреса бэкенда в клиентских скриптах](#адреса-бэкенда-в-клиентских-скриптах).
6. [Настройте запуск бэкенда как службы](#запуск-бэкенда-как-службы-systemd).
7. [Настройте Nginx](#настройка-nginx).
8. [Проверьте работу](#проверка-установки).

## Параметры настройки (.env)

Настройки хранятся в файле `backend/.env`. Шаблон — `backend/.env.example`.

| Параметр | Назначение | По умолчанию |
|---|---|---|
| `DATABASE_URL` | Строка подключения к PostgreSQL | `postgresql+asyncpg://postgres:postgres@localhost:5432/chatdb` |
| `SECRET_KEY` | Секретный ключ подписи JWT (обязательный, без значения по умолчанию) | — |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Время жизни токена доступа в минутах | `60` |

Пример файла:

```ini
DATABASE_URL=postgresql+asyncpg://postgres:ваш_пароль@localhost:5432/chatdb
SECRET_KEY=сгенерированная_случайная_строка
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Команда создаёт случайный ключ, который нужно вставить в `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

После изменения `.env` перезапустите службу: `sudo systemctl restart meow-chat`.

> **Безопасность:** не публикуйте `.env` и `SECRET_KEY` (файл указан в `.gitignore`) и ограничьте права доступа: `chmod 600 .env`. При смене `SECRET_KEY` все выданные токены станут недействительными, и пользователям придётся войти заново.

## Адреса бэкенда в клиентских скриптах

В репозитории адреса бэкенда заданы для локального запуска:

| Файл | Константа | Значение в репозитории |
|---|---|---|
| `frontend/app.js` | `API_BASE` | `http://localhost:8000` |
| `frontend/ws-client.js` | `WS_BASE` | `ws://localhost:8000` |

На сервере браузер пользователя не сможет обратиться к `localhost`, поэтому замените значения на адрес вашего домена:

```javascript
const API_BASE = 'http://meow-chat.net';   // frontend/app.js
const WS_BASE  = 'ws://meow-chat.net';     // frontend/ws-client.js
```

Запросы пойдут через Nginx на порту 80. Если вы включите HTTPS, используйте `https://` и `wss://`.

## Запуск бэкенда как службы (systemd)

Файл `/etc/systemd/system/meow-chat.service`:

```ini
[Unit]
Description=Meow Chat FastAPI backend
After=network.target postgresql.service

[Service]
Type=simple
User=meowchat
Group=meowchat
WorkingDirectory=/home/meowchat/meow-chat/backend
EnvironmentFile=/home/meowchat/meow-chat/backend/.env
ExecStart=/home/meowchat/meow-chat/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Бэкенд слушает только `127.0.0.1`, поэтому снаружи доступен лишь через Nginx. При аварийном завершении процесса systemd перезапускает его через 5 секунд.

Включите и запустите службу:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now meow-chat
sudo systemctl status meow-chat
```

Ожидаемый результат: статус `active (running)`.

## Настройка Nginx

Nginx раздаёт статические файлы фронтенда и проксирует остальные запросы на бэкенд. Блок `location /ws/` необходим для WebSocket: без заголовков `Upgrade` и `Connection` чат не будет получать сообщения в реальном времени.

Файл `/etc/nginx/sites-available/meow-chat.net`:

```nginx
server {
    listen 80;
    server_name meow-chat.net;

    root /home/meowchat/meow-chat/frontend;
    index login.html;

    location / {
        try_files $uri $uri/ @backend;
    }

    location @backend {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Подключите конфигурацию и примените её:

```bash
sudo ln -s /etc/nginx/sites-available/meow-chat.net /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Ожидаемый результат: `nginx -t` выводит `syntax is ok`, страница `http://meow-chat.net/login.html` открывается.

## Проверка установки

| Что проверяем | Команда | Ожидаемый результат |
|---|---|---|
| Служба бэкенда | `sudo systemctl status meow-chat` | `active (running)` |
| Ответ бэкенда | `curl http://127.0.0.1:8000/health` | `{"status":"ok"}` |
| Доступность через Nginx | открыть `http://meow-chat.net/login.html` | отображается страница входа |
| База данных | `psql -h 127.0.0.1 -U postgres -d chatdb -c "\dt"` | таблицы `users`, `rooms`, `messages` |
| Проксирование REST | `curl -s -o /dev/null -w "%{http_code}" http://meow-chat.net/rooms` | `401` (запрос дошёл до бэкенда) |

Для проверки полного цикла выполните контрольный сценарий:

1. Зарегистрируйте двух пользователей.
2. Под первым создайте комнату, под вторым убедитесь, что она появилась без перезагрузки страницы.
3. Отправьте сообщение от первого и проверьте, что второй получил его сразу.
4. Обновите страницу у второго и убедитесь, что сообщение осталось в истории.
5. Удалите комнату у первого и проверьте, что второго вернуло на экран «Выберите комнату».

Эндпоинты для ручной проверки описаны в [Справочной информации](reference.md#rest-api).

## Ограничения и рекомендации

- **Журналирование SQL.** В `backend/database.py` включён `echo=True`: все SQL-запросы попадают в журнал, и он быстро растёт. В продуктивной среде установите `echo=False` и следите за размером журнала командой `journalctl --disk-usage`.
- **Синхронизация времени.** При расхождении часов на сервере токены могут считаться просроченными. Проверьте `timedatectl`: должно быть `System clock synchronized: yes`.
- **CORS.** В `main.py` разрешены запросы с любых источников (`allow_origins=["*"]`). Для закрытой установки ограничьте список своим доменом.
- **Нет ролей.** Все пользователи равны, и любой авторизованный пользователь может удалить любую комнату.
- **Миграции.** Таблицы создаются при старте через `create_all`. Изменение моделей в существующей базе требует ручной миграции (в зависимостях есть Alembic, но в проекте он не настроен).
- **Один процесс.** Активные WebSocket-соединения хранятся в памяти процесса, поэтому запуск нескольких воркеров Uvicorn приведёт к тому, что пользователи из разных процессов не будут видеть сообщения друг друга.

[← Вернуться на главную страницу](index.md) | Далее: [Руководство пользователя](user-guide.md)
