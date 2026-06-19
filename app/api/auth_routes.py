"""Эндпоинты регистрации/входа/профиля."""
import re

from flask import current_app, g, jsonify, request

from . import api_bp
from ..auth import login_required
from ..models import Token, User, db

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@api_bp.post("/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if len(username) < 3:
        return jsonify({"error": "Логин минимум 3 символа"}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "Некорректный email"}), 400
    if len(password) < 6:
        return jsonify({"error": "Пароль минимум 6 символов"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Логин занят"}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email уже зарегистрирован"}), 409

    user = User(username=username, email=email, display_name=username, is_developer=True)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    token = Token.issue(user, current_app.config["TOKEN_TTL_DAYS"])
    db.session.commit()
    return jsonify({"token": token.key, "user": user.to_dict()}), 201


@api_bp.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    login_field = (data.get("username") or data.get("email") or "").strip()
    password = data.get("password") or ""

    user = (
        User.query.filter_by(username=login_field).first()
        or User.query.filter_by(email=login_field.lower()).first()
    )
    if not user or not user.check_password(password):
        return jsonify({"error": "Неверный логин или пароль"}), 401

    token = Token.issue(user, current_app.config["TOKEN_TTL_DAYS"])
    db.session.commit()
    return jsonify({"token": token.key, "user": user.to_dict()})


@api_bp.get("/auth/me")
@login_required
def me():
    return jsonify({"user": g.user.to_dict()})


@api_bp.post("/auth/logout")
@login_required
def logout():
    auth = request.headers.get("Authorization", "")
    key = auth[7:].strip()
    Token.query.filter_by(key=key).delete()
    db.session.commit()
    return jsonify({"ok": True})
