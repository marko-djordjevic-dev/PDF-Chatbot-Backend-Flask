from flask import Blueprint
from .auth import auth_bp
from .chatbot import chatbot_bp

bp = Blueprint('routes', __name__)

bp.register_blueprint(auth_bp)
bp.register_blueprint(chatbot_bp)