"""Модели базы данных EbloidStore."""
import secrets
from datetime import datetime, timedelta

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    # Имя для отображения в отзывах/в профиле разработчика.
    display_name = db.Column(db.String(120))
    is_developer = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reviews = db.relationship("Review", backref="user", cascade="all, delete-orphan")
    apps = db.relationship("App", backref="developer", cascade="all, delete-orphan")
    tokens = db.relationship("Token", backref="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "display_name": self.display_name or self.username,
            "is_developer": self.is_developer,
            "is_admin": self.is_admin,
        }


class Token(db.Model):
    """Простые bearer-токены для авторизации мобильного клиента."""
    __tablename__ = "tokens"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)

    @classmethod
    def issue(cls, user, ttl_days=30):
        token = cls(
            key=secrets.token_hex(32),
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(days=ttl_days),
        )
        db.session.add(token)
        return token

    @property
    def is_valid(self):
        return self.expires_at is None or self.expires_at > datetime.utcnow()


# Статусы модерации приложения.
STATUS_PENDING = "pending"     # на проверке
STATUS_APPROVED = "approved"   # опубликовано
STATUS_REJECTED = "rejected"   # отклонено


class App(db.Model):
    __tablename__ = "apps"

    id = db.Column(db.Integer, primary_key=True)
    # Уникальный package-идентификатор, например com.example.game
    package_name = db.Column(db.String(160), unique=True, nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    short_description = db.Column(db.String(280))
    description = db.Column(db.Text)
    category = db.Column(db.String(80), index=True)
    version = db.Column(db.String(40))
    icon = db.Column(db.String(255))          # относительный путь к иконке
    apk_file = db.Column(db.String(255))      # относительный путь к apk/aab
    developer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    status = db.Column(db.String(20), default=STATUS_PENDING, index=True)
    reject_reason = db.Column(db.Text)
    downloads = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    screenshots = db.relationship(
        "Screenshot", backref="app", cascade="all, delete-orphan", order_by="Screenshot.position"
    )
    reviews = db.relationship("Review", backref="app", cascade="all, delete-orphan")

    @property
    def rating(self):
        if not self.reviews:
            return 0.0
        return round(sum(r.rating for r in self.reviews) / len(self.reviews), 1)

    def to_dict(self, base_url="", full=False):
        data = {
            "id": self.id,
            "package_name": self.package_name,
            "title": self.title,
            "short_description": self.short_description,
            "category": self.category,
            "version": self.version,
            "icon_url": (base_url + "/static/uploads/" + self.icon) if self.icon else None,
            "rating": self.rating,
            "reviews_count": len(self.reviews),
            "downloads": self.downloads,
            "developer": (self.developer.display_name or self.developer.username)
            if self.developer else None,
            "status": self.status,
        }
        if full:
            data.update(
                {
                    "description": self.description,
                    "screenshots": [
                        base_url + "/static/uploads/" + s.path for s in self.screenshots
                    ],
                    "apk_url": (base_url + "/static/uploads/" + self.apk_file)
                    if self.apk_file else None,
                    "reject_reason": self.reject_reason,
                    "created_at": self.created_at.isoformat() if self.created_at else None,
                }
            )
        return data


class Screenshot(db.Model):
    __tablename__ = "screenshots"

    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey("apps.id"), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    position = db.Column(db.Integer, default=0)


class Review(db.Model):
    __tablename__ = "reviews"
    __table_args__ = (db.UniqueConstraint("app_id", "user_id", name="uq_review_user_app"),)

    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey("apps.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1..5
    text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "rating": self.rating,
            "text": self.text,
            "author": (self.user.display_name or self.user.username) if self.user else "—",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
