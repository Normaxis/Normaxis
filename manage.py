from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from app import app, db  # <- Assure-toi que ces deux objets existent dans app.py

migrate = Migrate(app, db)
