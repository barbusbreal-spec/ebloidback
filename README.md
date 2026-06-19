# EbloidStore — бэкенд

Бэкенд магазина приложений (как Google Play): REST API для мобильного клиента
[ebloid](https://github.com/barbusbreal-spec/ebloid), веб-панель разработчика,
панель модерации и уведомления в Telegram.

Написан на **Flask** и рассчитан на запуск на бесплатном хостинге **serv00**
(Phusion Passenger), но работает и локально.

## Возможности
- **Аккаунты**: регистрация/вход, авторизация по bearer-токену
- **Каталог**: список приложений, поиск, категории, сортировка
- **Карточки**: иконки, скриншоты, описание, версии, счётчик загрузок
- **Отзывы**: оценки 1–5 звёзд, средний рейтинг
- **Панель разработчика** (`/developer`): отправка приложений на модерацию с
  загрузкой иконки, скриншотов и APK/AAB
- **Панель модерации** (`/admin`): одобрение/отклонение заявок с причиной
- **Telegram-бот**: уведомления о новых заявках и решениях модерации

## Быстрый старт (локально)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed.py          # демо-данные (необязательно)
python run.py           # http://localhost:5000
```

- Витрина API: `GET http://localhost:5000/api/apps`
- Панель разработчика: `http://localhost:5000/developer` (demo / demo123)
- Панель модерации: `http://localhost:5000/admin` (admin / admin)

## Переменные окружения
| Переменная | Назначение | По умолчанию |
|---|---|---|
| `EBLOID_SECRET_KEY` | секрет для сессий/токенов | `change-me-in-production` |
| `EBLOID_DATABASE_URL` | строка подключения к БД | SQLite в корне |
| `EBLOID_UPLOAD_FOLDER` | папка для загрузок | `app/web/static/uploads` |
| `EBLOID_TG_BOT_TOKEN` | токен Telegram-бота | — |
| `EBLOID_TG_ADMIN_CHAT_ID` | chat_id для уведомлений | — |
| `EBLOID_ADMIN_USER` / `EBLOID_ADMIN_PASSWORD` | вход в модерацию | `admin` / `admin` |

## Подключение Telegram-бота
1. Создайте бота у [@BotFather](https://t.me/BotFather), получите токен.
2. Узнайте свой `chat_id` (напишите боту и откройте
   `https://api.telegram.org/bot<TOKEN>/getUpdates`, либо используйте `@userinfobot`).
3. Пропишите `EBLOID_TG_BOT_TOKEN` и `EBLOID_TG_ADMIN_CHAT_ID`.

Если переменные не заданы — уведомления просто не отправляются, остальное работает.

## Деплой на serv00
1. Залейте репозиторий в домашнюю директорию аккаунта serv00.
2. В панели serv00 создайте сайт типа **Python** и укажите точкой входа
   `passenger_wsgi.py` (Passenger ищет объект `application`).
3. Создайте виртуальное окружение и поставьте в него зависимости. Это важно:
   Passenger часто запускает приложение «системным» Python без наших пакетов,
   поэтому `passenger_wsgi.py` сам переключается на интерпретатор из `venv`.
   ```bash
   cd ~/ebloidback
   python3.11 -m venv venv
   ./venv/bin/pip install --upgrade pip
   ./venv/bin/pip install -r requirements.txt
   ```
   > Если venv лежит не в `~/ebloidback/venv` — задайте путь в `EBLOID_VENV`.
4. Пропишите переменные окружения `EBLOID_*` в `~/.bash_profile`.
5. Перезапустите приложение:
   ```bash
   mkdir -p tmp && touch tmp/restart.txt
   ```
6. В Android-клиенте укажите `API_BASE_URL = https://<домен>.serv00.net/api/`.

> SQLite подходит для старта. Для нагрузки можно переключиться на MySQL
> (serv00 его предоставляет), задав `EBLOID_DATABASE_URL`.

### Если видите «Web application could not be started»
Это значит, что Passenger не смог запустить процесс. После обновления
`passenger_wsgi.py` откройте сайт в браузере — вместо общей страницы он покажет
**настоящий traceback** и какой Python используется. Частые причины:
- зависимости не установлены в том окружении, которым стартует Passenger →
  выполните шаг 3 (venv) и `touch tmp/restart.txt`;
- не та версия Python — укажите `EBLOID_VENV` на нужный venv;
- посмотреть логи на serv00: `~/domains/<домен>/logs/` или системный лог Passenger.

## REST API (кратко)
| Метод | Путь | Описание |
|---|---|---|
| POST | `/api/auth/register` | регистрация → токен |
| POST | `/api/auth/login` | вход → токен |
| GET | `/api/auth/me` | текущий профиль (Bearer) |
| GET | `/api/apps?q=&category=&sort=` | каталог |
| GET | `/api/categories` | список категорий |
| GET | `/api/apps/{id}` | карточка приложения |
| GET | `/api/apps/{id}/reviews` | отзывы |
| POST | `/api/apps/{id}/reviews` | оставить отзыв (Bearer) |
| POST | `/api/apps/{id}/download` | засчитать загрузку, вернуть apk_url |
| GET | `/api/developer/apps` | мои заявки (Bearer) |
| POST | `/api/developer/apps` | отправить приложение (multipart, Bearer) |

## Структура
```
passenger_wsgi.py     точка входа для serv00/Passenger
run.py                локальный запуск
seed.py               демо-данные
app/
├── __init__.py       фабрика приложения
├── config.py         конфиг из переменных окружения
├── models.py         User, Token, App, Screenshot, Review
├── auth.py           bearer-авторизация
├── storage.py        сохранение загруженных файлов
├── telegram.py       уведомления в Telegram
├── api/              REST: auth, apps, developer
└── web/              панель разработчика + модерация (HTML)
```
