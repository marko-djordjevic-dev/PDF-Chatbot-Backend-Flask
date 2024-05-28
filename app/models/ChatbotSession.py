from app import db
from sqlalchemy.dialects.postgresql import ARRAY

class ChatbotSession(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    chatbot_id = db.Column(db.String(64), db.ForeignKey('chatbot.id'))
    chat_history = db.Column(ARRAY(db.TEXT))