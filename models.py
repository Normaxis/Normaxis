from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), default='user')
    confirmed = db.Column(db.Boolean, default=False)

    # Accès aux thèmes
    securite = db.Column(db.Boolean, default=False)
    qualite = db.Column(db.Boolean, default=False)
    environnement = db.Column(db.Boolean, default=False)

    messages = db.relationship('Message', backref='user', lazy=True)


class Section(db.Model):
    __tablename__ = 'section'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    video_url = db.Column(db.String(300), nullable=True)
    file_path = db.Column(db.String(200), nullable=True)
    theme = db.Column(db.String(50), nullable=False)


class Message(db.Model):
    __tablename__ = 'message'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
