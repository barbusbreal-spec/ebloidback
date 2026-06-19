"""Хелперы для сохранения загруженных файлов (иконки, скриншоты, apk)."""
import os
import secrets

from flask import current_app
from werkzeug.utils import secure_filename


def _ext(filename):
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _save(file_storage, subdir, allowed):
    if not file_storage or not file_storage.filename:
        return None
    ext = _ext(file_storage.filename)
    if ext not in allowed:
        raise ValueError(f"Недопустимый тип файла: .{ext}")
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subdir)
    os.makedirs(folder, exist_ok=True)
    name = f"{secrets.token_hex(12)}.{ext}"
    file_storage.save(os.path.join(folder, name))
    # Возвращаем путь относительно папки uploads (для URL).
    return f"{subdir}/{name}"


def save_icon(file_storage):
    return _save(file_storage, "icons", current_app.config["ALLOWED_IMAGE_EXT"])


def save_screenshot(file_storage):
    return _save(file_storage, "screenshots", current_app.config["ALLOWED_IMAGE_EXT"])


def save_apk(file_storage):
    return _save(file_storage, "apk", current_app.config["ALLOWED_APK_EXT"])


def cleanup_app_files(app):
    """Удаляет уже сохранённые файлы приложения, если заявка не дошла до commit.

    Защищает диск хостинга от накопления «осиротевших» загрузок при ошибке.
    """
    base = current_app.config["UPLOAD_FOLDER"]
    rels = [app.icon, app.apk_file] + [s.path for s in getattr(app, "screenshots", [])]
    for rel in rels:
        if not rel:
            continue
        try:
            os.remove(os.path.join(base, rel))
        except OSError:
            pass
