# api/__init__.py
from flask import Blueprint

from api.user_tasks import user_bp

api_bp = Blueprint("api", __name__)

api_bp.register_blueprint(user_bp, url_prefix="/users")
api_bp.register_blueprint(prompt_bp, user_prefix="/prompts")