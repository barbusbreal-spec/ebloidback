"""Авторизация по bearer-токену для REST API."""
from functools import wraps

from flask import g, jsonify, request

from .models import Token


def current_user():
    """Достаёт пользователя из заголовка Authorization: Bearer <token>."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    key = auth[7:].strip()
    token = Token.query.filter_by(key=key).first()
    if not token or not token.is_valid:
        return None
    return token.user


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            return jsonify({"error": "Требуется авторизация"}), 401
        g.user = user
        return fn(*args, **kwargs)

    return wrapper
