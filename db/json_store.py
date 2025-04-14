# db/json_store.py
import json
import os

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