# models/prompts.py
from flask_sqlalchemy import SQLAlchemy 
from datetime import datetime

db = SQLAlchemy()

class Prompt(db.Model):
  __tablename__ = 'prompts'

  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String, nullable=False, unique=True)
  content = db.Column(db.Text, nullable=False)
  description = db.Column(db.String, nullable=True)
  updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)