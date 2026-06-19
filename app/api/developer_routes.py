"""API разработчика: загрузка приложения на модерацию и список своих заявок."""
from flask import g, jsonify, request

from . import api_bp
from .apps_routes import base_url
from ..auth import login_required
from ..models import App, STATUS_PENDING, Screenshot, db
from ..storage import save_apk, save_icon, save_screenshot
from ..telegram import notify_new_submission


@api_bp.get("/developer/apps")
@login_required
def my_apps():
    apps = (
        App.query.filter_by(developer_id=g.user.id)
        .order_by(App.created_at.desc())
        .all()
    )
    return jsonify({"apps": [a.to_dict(base_url(), full=True) for a in apps]})


@api_bp.post("/developer/apps")
@login_required
def submit_app():
    """Создание заявки на публикацию. multipart/form-data:

    поля: package_name, title, short_description, description, category, version
    файлы: icon (1), apk (1), screenshots (N)
    """
    f = request.form
    package_name = (f.get("package_name") or "").strip()
    title = (f.get("title") or "").strip()
    if not package_name or not title:
        return jsonify({"error": "Нужны package_name и title"}), 400
    if App.query.filter_by(package_name=package_name).first():
        return jsonify({"error": "Приложение с таким package_name уже существует"}), 409

    app = App(
        package_name=package_name,
        title=title,
        short_description=(f.get("short_description") or "").strip(),
        description=(f.get("description") or "").strip(),
        category=(f.get("category") or "").strip(),
        version=(f.get("version") or "1.0").strip(),
        developer_id=g.user.id,
        status=STATUS_PENDING,
    )
    db.session.add(app)
    try:
        if "icon" in request.files:
            app.icon = save_icon(request.files["icon"])
        if "apk" in request.files:
            app.apk_file = save_apk(request.files["apk"])
        db.session.flush()
        for i, shot in enumerate(request.files.getlist("screenshots")):
            path = save_screenshot(shot)
            if path:
                db.session.add(Screenshot(app_id=app.id, path=path, position=i))
    except ValueError as exc:
        db.session.rollback()
        cleanup_app_files(app)
        return jsonify({"error": str(exc)}), 400
    except OSError as exc:
        db.session.rollback()
        cleanup_app_files(app)
        return jsonify({"error": "Не удалось сохранить файлы (возможно, нет места "
                                 f"на диске): {exc}"}), 507
    except Exception as exc:  # noqa: BLE001 — не роняем процесс целиком
        db.session.rollback()
        cleanup_app_files(app)
        return jsonify({"error": f"Ошибка загрузки: {exc}"}), 500

    g.user.is_developer = True
    db.session.commit()

    try:
        notify_new_submission(app)
    except Exception:  # noqa: BLE001
        pass
    return jsonify({"app": app.to_dict(base_url(), full=True)}), 201
