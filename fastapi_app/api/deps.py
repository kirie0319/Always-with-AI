# fastapi_app/api/deps.py
from contextlib import contextmanager
from models import db

@contextmanager
def provide_session():
  try:
    yield db.session
  finally:
    db.session.close()
    