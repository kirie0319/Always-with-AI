# fastapi_app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv
from .api import chat
import os, sys
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
  sys.path.insert(0, ROOT_DIR)

load_dotenv()

app = FastAPI(title="AI Assistatn (FastAPI)")

app.add_middleware(
  SessionMiddleware,
  secret_key=os.getenv("FLASK_SECRET_KEY")
)

app.mount("/static", StaticFiles(directory=f"{BASE_DIR}/../static"), name="static")
templates = Jinja2Templates(directory=f"{BASE_DIR}/templates")

app.include_router(chat.router)

@app.get("/health")
async def health():
  return {"status": "ok"}