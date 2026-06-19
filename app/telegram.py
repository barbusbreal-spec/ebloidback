"""Уведомления в Telegram-бот.

Используется для оповещения админов о новых заявках на модерацию и
о действиях по приложениям. Работает через простой Bot API (sendMessage).
Если токен/чат не настроены — функции тихо ничего не делают, чтобы не
ломать основной флоу.
"""
import logging

import requests
from flask import current_app

log = logging.getLogger(__name__)


def _config():
    return (
        current_app.config.get("TELEGRAM_BOT_TOKEN"),
        current_app.config.get("TELEGRAM_ADMIN_CHAT_ID"),
    )


def send_message(text, chat_id=None):
    token, default_chat = _config()
    chat_id = chat_id or default_chat
    if not token or not chat_id:
        log.info("Telegram не настроен, пропускаю уведомление: %s", text)
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML",
                  "disable_web_page_preview": True},
            timeout=10,
        )
        return resp.ok
    except requests.RequestException as exc:
        log.warning("Не удалось отправить сообщение в Telegram: %s", exc)
        return False


def notify_new_submission(app):
    dev = app.developer.display_name or app.developer.username if app.developer else "—"
    send_message(
        "🆕 <b>Новая заявка на модерацию</b>\n"
        f"<b>{app.title}</b> ({app.package_name})\n"
        f"Разработчик: {dev}\n"
        f"Категория: {app.category or '—'} · версия {app.version or '—'}\n"
        f"ID заявки: #{app.id}"
    )


def notify_decision(app, approved):
    if approved:
        send_message(f"✅ Приложение <b>{app.title}</b> (#{app.id}) одобрено и опубликовано.")
    else:
        send_message(
            f"⛔ Приложение <b>{app.title}</b> (#{app.id}) отклонено.\n"
            f"Причина: {app.reject_reason or '—'}"
        )
