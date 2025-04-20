# woker.py
from celery import Celery
import os
from dotenv import load_dotenv
load_dotenv()

def make_celery(app_name=__name__):
  print("BROKER:", os.getenv("CELERY_BROKER_URL"))
  print("BACKEND:", os.getenv("CELERY_RESULT_BACKEND"))
  return Celery(
    app_name,
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
  )

import tasks
app = make_celery()  # 'celery'から'app'に変更