"""Веб-панели: панель разработчика (отправка приложений на проверку)
и админ-панель модерации. Простые серверные шаблоны на сессиях.
"""
import functools

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from . import web_bp
from ..models import (
    App,
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    Screenshot,
    User,
    db,
)
from ..storage import save_apk, save_icon, save_screenshot
from ..telegram import notify_decision, notify_new_submission

CATEGORIES = ["Игры", "Социальные", "Инструменты", "Образование",
              "Развлечения", "Финансы", "Здоровье", "Прочее"]


# ---------------------------------------------------------------------------
# Панель разработчика (вход по логину/паролю обычного пользователя)
# ---------------------------------------------------------------------------
def dev_required(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("dev_user_id"):
            return redirect(url_for("web.dev_login"))
        return fn(*args, **kwargs)

    return wrapper


def current_dev():
    uid = session.get("dev_user_id")
    return User.query.get(uid) if uid else None


@web_bp.route("/")
def index():
    return redirect(url_for("web.dev_dashboard"))


@web_bp.route("/developer/login", methods=["GET", "POST"])
def dev_login():
    if request.method == "POST":
        login_field = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = (
            User.query.filter_by(username=login_field).first()
            or User.query.filter_by(email=login_field.lower()).first()
        )
        if user and user.check_password(password):
            session["dev_user_id"] = user.id
            return redirect(url_for("web.dev_dashboard"))
        flash("Неверный логин или пароль", "error")
    return render_template("dev_login.html")


@web_bp.route("/developer/register", methods=["GET", "POST"])
def dev_register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        if len(username) < 3 or len(password) < 6 or "@" not in email:
            flash("Проверьте поля: логин 3+, пароль 6+, корректный email", "error")
        elif User.query.filter_by(username=username).first():
            flash("Логин занят", "error")
        elif User.query.filter_by(email=email).first():
            flash("Email уже зарегистрирован", "error")
        else:
            user = User(username=username, email=email, display_name=username,
                        is_developer=True)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            session["dev_user_id"] = user.id
            return redirect(url_for("web.dev_dashboard"))
    return render_template("dev_register.html")


@web_bp.route("/developer/logout")
def dev_logout():
    session.pop("dev_user_id", None)
    return redirect(url_for("web.dev_login"))


@web_bp.route("/developer")
@dev_required
def dev_dashboard():
    apps = (
        App.query.filter_by(developer_id=current_dev().id)
        .order_by(App.created_at.desc())
        .all()
    )
    return render_template("dev_dashboard.html", apps=apps, user=current_dev())


@web_bp.route("/developer/apps/new", methods=["GET", "POST"])
@dev_required
def dev_new_app():
    if request.method == "POST":
        package_name = (request.form.get("package_name") or "").strip()
        title = (request.form.get("title") or "").strip()
        if not package_name or not title:
            flash("Нужны package_name и название", "error")
            return render_template("dev_app_form.html", categories=CATEGORIES)
        if App.query.filter_by(package_name=package_name).first():
            flash("package_name уже занят", "error")
            return render_template("dev_app_form.html", categories=CATEGORIES)

        app = App(
            package_name=package_name,
            title=title,
            short_description=(request.form.get("short_description") or "").strip(),
            description=(request.form.get("description") or "").strip(),
            category=(request.form.get("category") or "").strip(),
            version=(request.form.get("version") or "1.0").strip(),
            developer_id=current_dev().id,
            status=STATUS_PENDING,
        )
        try:
            if request.files.get("icon"):
                app.icon = save_icon(request.files["icon"])
            if request.files.get("apk"):
                app.apk_file = save_apk(request.files["apk"])
            db.session.add(app)
            db.session.flush()
            for i, shot in enumerate(request.files.getlist("screenshots")):
                path = save_screenshot(shot)
                if path:
                    db.session.add(Screenshot(app_id=app.id, path=path, position=i))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "error")
            return render_template("dev_app_form.html", categories=CATEGORIES)

        db.session.commit()
        notify_new_submission(app)
        flash("Приложение отправлено на модерацию ✅", "ok")
        return redirect(url_for("web.dev_dashboard"))

    return render_template("dev_app_form.html", categories=CATEGORIES)


# ---------------------------------------------------------------------------
# Админ-панель модерации
# ---------------------------------------------------------------------------
def admin_required(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("web.admin_login"))
        return fn(*args, **kwargs)

    return wrapper


@web_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username") or ""
        password = request.form.get("password") or ""
        if (
            username == current_app.config["ADMIN_USERNAME"]
            and password == current_app.config["ADMIN_PASSWORD"]
        ):
            session["is_admin"] = True
            return redirect(url_for("web.admin_queue"))
        flash("Неверные данные администратора", "error")
    return render_template("admin_login.html")


@web_bp.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("web.admin_login"))


@web_bp.route("/admin")
@admin_required
def admin_queue():
    status = request.args.get("status", STATUS_PENDING)
    apps = App.query.filter_by(status=status).order_by(App.created_at.desc()).all()
    counts = {
        STATUS_PENDING: App.query.filter_by(status=STATUS_PENDING).count(),
        STATUS_APPROVED: App.query.filter_by(status=STATUS_APPROVED).count(),
        STATUS_REJECTED: App.query.filter_by(status=STATUS_REJECTED).count(),
    }
    return render_template("admin_queue.html", apps=apps, status=status, counts=counts)


@web_bp.route("/admin/apps/<int:app_id>")
@admin_required
def admin_app(app_id):
    app = App.query.get_or_404(app_id)
    return render_template("admin_app.html", app=app)


@web_bp.route("/admin/apps/<int:app_id>/approve", methods=["POST"])
@admin_required
def admin_approve(app_id):
    app = App.query.get_or_404(app_id)
    app.status = STATUS_APPROVED
    app.reject_reason = None
    db.session.commit()
    notify_decision(app, approved=True)
    flash(f"«{app.title}» опубликовано", "ok")
    return redirect(url_for("web.admin_queue"))


@web_bp.route("/admin/apps/<int:app_id>/reject", methods=["POST"])
@admin_required
def admin_reject(app_id):
    app = App.query.get_or_404(app_id)
    app.status = STATUS_REJECTED
    app.reject_reason = (request.form.get("reason") or "").strip()
    db.session.commit()
    notify_decision(app, approved=False)
    flash(f"«{app.title}» отклонено", "ok")
    return redirect(url_for("web.admin_queue"))
