# models/users.py

from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from database import Base

class User(Base):
  __tablename__  = 'users'

  id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
  username = Column(String(64), unique=True, nullable=False, index=True)
  email = Column(String(120), unique=True, nullable=False, index=True)
  password_hash = Column(String(256), nullable=False)
  is_admin = Column(Boolean, default=False)
  created_at = Column(DateTime, default=datetime.utcnow)

  def set_password(self, password):
    self.password_hash = generate_password_hash(password)

  def check_password(self, password):
    return check_password_hash(self.password_hash, password)
  
  def __repr__(self):
    return f'<User {self.username}'