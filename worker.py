# woker.py
from celery import Celery
import os
from dotenv import load_dotenv
load_dotenv()

def make_celery(app_name=__name__):
  return Celery(
    app_name,
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
  )

import tasks
app = make_celery()  # 'celery'から'app'に変更