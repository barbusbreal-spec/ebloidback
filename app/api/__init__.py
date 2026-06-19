from flask import Blueprint

api_bp = Blueprint("api", __name__)

from . import auth_routes, apps_routes, developer_routes  # noqa: E402,F401
