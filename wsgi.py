# wsgi.py
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import uuid 
import threading
from datetime import datetime
import os

from ai_services.factory import MultimodalAIService
from prompts.loader import PromptLoader
from db.json_store import load_json, save_json, to_pretty_json
import config


load_dotenv()

CHAT_LOG_FILE = config.CHAT_LOG_FILE 
SUMMARY_FILE = config.SUMMARY_FILE
USER_HISTORY_FILE = config.USER_HISTORY_FILE
MAX_RALLIES = config.MAX_RALLIES

ai_service = MultimodalAIService(
    anthropic_key=os.getenv("ANTHROPIC_API_KEY"),
    openai_key=os.getenv("OPENAI_API_KEY"),
    primary="anthropic"  # Default to Anthropic
)

prompt_loader = PromptLoader()

app = Flask(__name__, static_url_path='/static')

def get_user_id(user_identifier):
  user_history = load_json(USER_HISTORY_FILE, {})

  if user_identifier is None or isinstance(user_history, list):
    user_history = {}

  if user_identifier not in user_history:
    user_history[user_identifier] = {
      "user_id": str(uuid.uuid4()),
      "created_at": datetime.now().isoformat(),
      "messages": []
    }
    save_json(USER_HISTORY_FILE, user_history)
  return user_history[user_identifier]["user_id"]

def update_user_messages(user_identifier, message_pair):
  user_history = load_json(USER_HISTORY_FILE, {})

  if user_history is None or isinstance(user_history, list):
    user_history = {}

  if user_identifier not in user_history:
    get_user_id(user_identifier)
    user_history = load_json(USER_HISTORY_FILE, {})

    if user_history is None or isinstance(user_history, list):
      user_history = {}
      user_history[user_identifier] = {
        "user_id": str(uuid.uuid4()),
        "created_at": datetime.now().isoformat(),
        "messages": []
      }
  if "messages" not in user_history[user_identifier]:
    user_history[user_identifier]["messages"] = []

  user_history[user_identifier]["messages"].append(message_pair)

  if len(user_history[user_identifier]["messages"]) > MAX_RALLIES:
    user_history[user_identifier]["messages"] = user_history[user_identifier]["messages"][-MAX_RALLIES:]

  save_json(USER_HISTORY_FILE, user_history) 

def generate_summary_in_background(history_json):
  try:
    # Load the summary prompt
    summary_prompt = prompt_loader.load_prompt("system", "summarizer")
      
    # Process variables in the prompt
    processed_prompt = prompt_loader.process_variables(
      summary_prompt["content"], 
      {"history": history_json}
    )
        
    # Generate summary using your service
    response = ai_service.generate_response([
      {"role": "user", "content": processed_prompt}
    ], {
      "model": "claude-3-7-sonnet-20250219",
      "max_tokens": 1024
    })
        
    summary = [{"role": "developer", "content": response["content"]}]
    save_json(SUMMARY_FILE, summary)
    print("Summary generated successfully")
  except Exception as e:
    print(f"Error generating summary: {e}")

@app.route("/")
def index():
    return render_template("index2.html")

@app.route("/providers")
def get_providers():
  providers = ai_service.get_available_providers()
  models = ai_service.get_available_models()
  return jsonify({
    "providers": providers,
    "models": models
  })

@app.route("/prompts")
def get_prompts():
  prompts = prompt_loader.list_prompts()
  return jsonify(prompts)

@app.route("/chat", methods=["POST"])
def chat():
  user_identifier = request.remote_addr
  user_id = get_user_id(user_identifier)
  history = load_json(CHAT_LOG_FILE, [])
  history_json = to_pretty_json(history)

  summary = load_json(SUMMARY_FILE, [])
  summary_json = to_pretty_json(summary)

  user_history = load_json(USER_HISTORY_FILE, {})
  user_history_json = to_pretty_json(user_history)

  data = request.get_json()
  user_input = data.get("message", "")
  provider = data.get("provider", "anthropic")
  model = data.get("model", None)
  prompt_category = data.get("prompt_category", "specific")
  prompt_name = data.get("prompt_name", "finance")

  try:
    selected_prompt = prompt_loader.load_prompt(prompt_category, prompt_name)
    
    # Process variables in the prompt
    processed_prompt = prompt_loader.process_variables(
      selected_prompt["content"], 
      {
        "summary": summary_json,
        "history": user_history_json
      }
    )
  except ValueError:
    # Fallback to default prompt
    processed_prompt = f"""
    You are an AI assistant. Provide helpful responses.
    
    Recent conversation history:
    {user_history_json}
    """
  user_message = {
    "role": "user", 
    "content": user_input, 
    "user_id": user_id,
    "timestamp": datetime.now().isoformat()
  }
  history.append(user_message)

    # Generate response using the factory
  messages = [{"role": "user", "content": user_input}]
  options = {
    "provider": provider,
    "model": model,
    "max_tokens": 1024,
    "system": processed_prompt
  }
    
  response = ai_service.generate_response(messages, options)

  assistant_message = {
    "role": "assistant", 
    "content": response["content"], 
    "user_id": user_id,
    "id": str(uuid.uuid4()),
    "timestamp": datetime.now().isoformat(),
    "provider": response["provider"],
    "model": response["model"]
  }
    
  history.append(assistant_message)
  save_json(CHAT_LOG_FILE, history)

  message_pair = {
    "user": user_message,
    "assistant": assistant_message,
    "timestamp": datetime.now().isoformat()
  }
  update_user_messages(user_identifier, message_pair)

  if len(history) % 5 == 0:
      threading.Thread(
        target=generate_summary_in_background,
        args=(history_json,)
  ).start()

  return jsonify({
    "response": response["content"],
    "timestamp": datetime.now().isoformat(),
    "provider": response["provider"],
    "model": response["model"]
  })

@app.route("/clear", methods=["POST"])
def clear_chat_data():
  save_json(CHAT_LOG_FILE, [])
  save_json(SUMMARY_FILE, [])
  save_json(USER_HISTORY_FILE, {})
  return jsonify({"status": "success", "message": "チャットデータをクリアしました"})

if __name__ == '__main__':
  port = int(os.environ.get('PORT', 5001))
  app.run(host='0.0.0.0', port=port)