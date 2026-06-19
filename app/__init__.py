"""Фабрика приложения EbloidStore backend."""
import os

from flask import Flask, jsonify
from flask_cors import CORS

from .config import Config
from .models import db


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    # CORS открыт для API, чтобы мобильный клиент мог стучаться откуда угодно.
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)

    from .api import api_bp
    from .web import web_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(web_bp)

    with app.app_context():
        db.create_all()

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "ebloidstore"})

    @app.errorhandler(404)
    def not_found(e):
        from flask import request
        if request.path.startswith("/api/"):
            return jsonify({"error": "Не найдено"}), 404
        return e, 404

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"error": "Файл слишком большой"}), 413

    return app
