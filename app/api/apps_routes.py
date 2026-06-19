"""Каталог приложений и отзывы (публичная витрина магазина)."""
from flask import g, jsonify, request

from . import api_bp
from ..auth import current_user, login_required
from ..models import App, Review, STATUS_APPROVED, db


def base_url():
    # Абсолютный префикс для ссылок на статику (иконки/скриншоты).
    return request.url_root.rstrip("/")


@api_bp.get("/apps")
def list_apps():
    """Список опубликованных приложений с фильтрами поиска/категории."""
    q = (request.args.get("q") or "").strip()
    category = (request.args.get("category") or "").strip()
    sort = request.args.get("sort", "new")

    query = App.query.filter_by(status=STATUS_APPROVED)
    if q:
        like = f"%{q}%"
        query = query.filter(App.title.ilike(like) | App.short_description.ilike(like))
    if category:
        query = query.filter_by(category=category)

    apps = query.all()
    if sort == "downloads":
        apps.sort(key=lambda a: a.downloads, reverse=True)
    elif sort == "rating":
        apps.sort(key=lambda a: a.rating, reverse=True)
    else:
        apps.sort(key=lambda a: a.created_at or 0, reverse=True)

    return jsonify({"apps": [a.to_dict(base_url()) for a in apps]})


@api_bp.get("/categories")
def categories():
    rows = (
        db.session.query(App.category)
        .filter(App.status == STATUS_APPROVED, App.category.isnot(None))
        .distinct()
        .all()
    )
    return jsonify({"categories": sorted({r[0] for r in rows if r[0]})})


@api_bp.get("/apps/<int:app_id>")
def app_detail(app_id):
    app = App.query.filter_by(id=app_id, status=STATUS_APPROVED).first_or_404()
    return jsonify({"app": app.to_dict(base_url(), full=True)})


@api_bp.post("/apps/<int:app_id>/download")
def register_download(app_id):
    app = App.query.filter_by(id=app_id, status=STATUS_APPROVED).first_or_404()
    app.downloads = (app.downloads or 0) + 1
    db.session.commit()
    return jsonify({"downloads": app.downloads, "apk_url": app.to_dict(base_url(), full=True)["apk_url"]})


@api_bp.get("/apps/<int:app_id>/reviews")
def list_reviews(app_id):
    App.query.filter_by(id=app_id, status=STATUS_APPROVED).first_or_404()
    reviews = (
        Review.query.filter_by(app_id=app_id)
        .order_by(Review.created_at.desc())
        .all()
    )
    return jsonify({"reviews": [r.to_dict() for r in reviews]})


@api_bp.post("/apps/<int:app_id>/reviews")
@login_required
def add_review(app_id):
    App.query.filter_by(id=app_id, status=STATUS_APPROVED).first_or_404()
    data = request.get_json(silent=True) or {}
    try:
        rating = int(data.get("rating", 0))
    except (TypeError, ValueError):
        rating = 0
    if rating < 1 or rating > 5:
        return jsonify({"error": "Оценка должна быть от 1 до 5"}), 400
    text = (data.get("text") or "").strip()

    review = Review.query.filter_by(app_id=app_id, user_id=g.user.id).first()
    if review:
        review.rating = rating
        review.text = text
    else:
        review = Review(app_id=app_id, user_id=g.user.id, rating=rating, text=text)
        db.session.add(review)
    db.session.commit()
    return jsonify({"review": review.to_dict()}), 201
