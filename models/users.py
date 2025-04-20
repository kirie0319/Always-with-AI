# from datetime import datetime
# from app import db
# from werkzeug.security import generate_password_hash, check_password_hash
# import uuid 


# class User(db.Model):
#   __tablename__  = 'users'

#   id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid()))
#   username = db.Column(db.String(64), unique=True, nullable=False, index=True)
#   email = db.Column(db.String(120), unique=True, nullable=False, index=True)
#   password_hash = db.Column(db.String(256), nullable=False)
#   is_admin = db.Column(db.Boolean, default=False)
#   created_at = db.Column(db.DateTime, default=datetime.utcnow)

#   def set_password(seflf, password):
#     self.password_hash = generate_password_hash(password)

#   def check_password(self, password):
#     return check_password_hash(self.password_hash, password)
  
#   def __repr__(self):
#     return f'<User {self.username}'
# プロンプトのとのリレーションシップが必須になる