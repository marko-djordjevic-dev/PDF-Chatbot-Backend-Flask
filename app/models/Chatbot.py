import uuid
from app import db
from sqlalchemy.dialects.postgresql import ARRAY

class Chatbot(db.Model):
    id = db.Column(db.String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(256), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    file_names = db.Column(ARRAY(db.String(64)))
    index_name = db.Column(db.String(64))
    initial = db.Column(db.Text)
    placeholder = db.Column(db.Text)
    suggested = db.Column(db.Text)
    img_id  = db.Column(db.String(64))
    chatbot_sessions = db.relationship('ChatbotSession',  backref = 'chatbot')