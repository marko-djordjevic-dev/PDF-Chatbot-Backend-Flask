from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index = True, unique = True)
    first_name = db.Column(db.String(20), nullable = False)
    last_name = db.Column(db.String(20), nullable = False)
    email = db.Column(db.String(64), unique = True, nullable = False)
    password = db.Column(db.String(64))
    superuser = db.Column(db.Integer)
    chatbot_sessions = db.relationship('ChatbotSession', backref = 'user')