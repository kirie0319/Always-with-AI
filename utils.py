# utils.py
import json, os, config, uuid
from datetime import datetime

MAX_RALLIES = 6

def load_json(filepath, default):
  try:
    with open(filepath, "r") as f:
      return json.load(f)
  except (FileNotFoundError, json.JSONDecodeError):
    return default

def save_json(filepath, data):
  with open(filepath, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

def to_pretty_json(data):
  return json.dumps(data, ensure_ascii=False, indent=2)
  
def get_last_conversation_pair():
  history = load_json(config.CHAT_LOG_FILE, [])
  if len(history) < 2:
    return None
  
  for i in range(len(history) -2, -1, -1):
    if history[i]["role"] == "user" and history[i +1]["role"] == "assistant":
      return {
        "user": history[i],
        "assistant": history[i +1]
      }
  return None

def get_user_id(user_identifier):
  user_history = load_json(config.USER_HISTORY_FILE, {})

  if user_identifier is None or isinstance(user_history, list):
    user_history = {}

  if user_identifier not in user_history:
    user_history[user_identifier] = {
      "user_id": str(uuid.uuid4()),
      "created_at": datetime.now().isoformat(),
      "messages": []
    }
    save_json(config.USER_HISTORY_FILE, user_history)

  return user_history[user_identifier]["user_id"]

def update_user_messages(user_identifier, message_pair):
  user_history = load_json(config.USER_HISTORY_FILE, {})
  history = load_json(config.CHAT_LOG_FILE, [])

  if user_history is None or isinstance(user_history, list):
    user_history = {}

  if user_identifier not in user_history:
    get_user_id(user_identifier)
    user_history = load_json(config.USER_HISTORY_FILE, {})

    if user_history is None or isinstance(user_history, list):
      user_history = {}
      user_history[user_identifier] = {
        "user_id": str(uuid.uuid4()),
        "created_at": datetime.now().isoformat(),
        "messages": []
      }
  if "messages" not in user_history[user_identifier]:
    user_history[user_identifier]["messages"] = []

  if len(history) > 2:
    user_history[user_identifier]["messages"].append(history[-4:-2])

  if len(user_history[user_identifier]["messages"]) > MAX_RALLIES:
    user_history[user_identifier]["messages"] = user_history[user_identifier]["messages"][-MAX_RALLIES:]

  save_json(config.USER_HISTORY_FILE, user_history)