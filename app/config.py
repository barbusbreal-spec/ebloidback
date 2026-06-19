"""Конфигурация приложения.

Все значения берутся из переменных окружения, что удобно для serv00:
достаточно прописать их в ~/.bash_profile или в panel переменных окружения.
"""
import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    # Секретный ключ для подписи токенов/сессий. ОБЯЗАТЕЛЬНО поменять на проде.
    SECRET_KEY = os.environ.get("EBLOID_SECRET_KEY", "change-me-in-production")

    # База данных. По умолчанию SQLite в корне проекта — работает на serv00 без настройки.
    # Можно указать MySQL: mysql+pymysql://user:pass@host/dbname
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "EBLOID_DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "ebloid.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Куда складываем загруженные файлы (иконки, скриншоты, apk).
    UPLOAD_FOLDER = os.environ.get(
        "EBLOID_UPLOAD_FOLDER", os.path.join(BASE_DIR, "app", "web", "static", "uploads")
    )
    MAX_CONTENT_LENGTH = int(os.environ.get("EBLOID_MAX_UPLOAD_MB", "100")) * 1024 * 1024

    # Время жизни токена авторизации (в днях).
    TOKEN_TTL_DAYS = int(os.environ.get("EBLOID_TOKEN_TTL_DAYS", "30"))

    # Telegram-бот для уведомлений.
    TELEGRAM_BOT_TOKEN = os.environ.get("EBLOID_TG_BOT_TOKEN", "")
    # Чат/канал, куда падают уведомления о новых заявках на модерацию.
    TELEGRAM_ADMIN_CHAT_ID = os.environ.get("EBLOID_TG_ADMIN_CHAT_ID", "")

    # Логин/пароль для входа в админ-панель модерации.
    ADMIN_USERNAME = os.environ.get("EBLOID_ADMIN_USER", "admin")
    ADMIN_PASSWORD = os.environ.get("EBLOID_ADMIN_PASSWORD", "admin")

    ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "webp"}
    ALLOWED_APK_EXT = {"apk", "aab", "zip"}
