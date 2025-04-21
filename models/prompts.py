# models/prompts.py
from sqlalchemy import Column, Integer, String, Text, DateTime 
from datetime import datetime
from database import Base 

class Prompt(Base):
  __tablename__ = 'prompts'

  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False, unique=True)
  content = Column(Text, nullable=False)
  description = Column(String, nullable=True)
  updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)