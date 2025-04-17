from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_migrate import Migrate 
from openai import OpenAI
from dotenv import load_dotenv
import os
import anthropic
from datetime import datetime
from models import db, Prompt 
import json
import uuid
import threading
import yaml
import traceback

load_dotenv()

CHAT_LOG_FILE = "chat_log.json"
SUMMARY_FILE = "chatsummary.json"
USER_HISTORY_FILE = "user_history.json"
MAX_RALLIES = 7
YAML_PATH = "prompts/specific/finance.yaml"
MAX_TOKENS_INPUT  = 8_000   # Claude に渡す入力上限
MAX_TOKENS_OUTPUT = 512     # 期待する出力上限
SAFETY_MARGIN     = 500     # header 系を見込んだ余白

anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

anthropic_client = anthropic.Anthropic(
  api_key=anthropic_api_key,
)


app = Flask(__name__, static_url_path='/static')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 
app.secret_key = os.getenv("FLASK_SECRET_KEY")
db.init_app(app)
migrate = Migrate(app, db)

def load_json(filepath, default):
  try:
    with open(filepath, "r") as f:
      return json.load(f)
  except (FileNotFoundError, json.JSONDecodeError):
    return default

def to_pretty_json(data):
    return json.dumps(data, ensure_ascii=False, indent=2)

def save_json(filepath, data):
  with open(filepath, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

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
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    anthropic_client = anthropic.Anthropic(
      api_key=anthropic_api_key,
    )
    user_history = load_json("user_history.json", {})
    user_history_json = to_pretty_json(user_history)
    summary = load_json("chatsummary.json", [])
    summary_json = to_pretty_json(summary)
    summarizing_prompt = summarizing_prompt = f"""You are an expert conversation summarizer.

    Your task is to analyze and summarize a JSON-formatted chat history between a user and an AI assistant. The goal is to extract key details and provide a clear, structured summary of the conversation.

    Use the following output format:

    ---

    ### Chat Summary

    #### 1. **Overview**
    Briefly describe the overall context of the conversation, the participants, and the tone.

    #### 2. **Key Points**
    List 5-7 bullet points that highlight the most important facts, insights, or decisions discussed during the conversation.

    #### 3. **Topic Timeline** (optional)
    If applicable, outline the main topics discussed in chronological order.

    #### 4. **Follow-up Items**
    List any remaining questions, action items, or topics that could be explored further.

    #### 5. **Context Notes**
    Mention any relevant background, such as the fictional setting, tone of the assistant, or relationship between participants.

    ---

    Focus on clarity and usefulness. If the conversation is based on a fictional character (e.g., anime, games), preserve the tone and role-playing context in your summary.

    Now, here is the summary of this conversation:
    {summary_json}

    And also here is the conversation history with users that is last 7 rallies:
    {user_history_json}
    """

    anthropic_summary = anthropic_client.messages.create(
      model="claude-3-7-sonnet-20250219",
      max_tokens=2048,
      messages=[
        {"role": "user", "content": summarizing_prompt}
      ]
    )
    summary = [{"role": "developer", "content": anthropic_summary.content[0].text}]
    save_json(SUMMARY_FILE, summary)
    print("Summary generated successfully")
  except Exception as e:
    print(f"Error generating summary: {e}")

### new version

def count_claude_tokens(text: str) -> int:
  return len(text) // 3

# def compress_history(messages: list[dict], tokenizer=count_claude_tokens, max_tokens=MAX_TOKENS_INPUT):
#   kept, token_total = [], 0

#   for m in reversed(messages):
#     cost = tokenizer(m["content"])
#     if token_total + cost > max_tokens - SAFETY_MARGIN:
#       break
#     kept.insert(0, m)
#     token_total += cost
  
#   older = messages[:len(messages) - len(kept)]
#   if older:
#     summary_text = summarize_messages(older)
#     kept.insert(0, {"role": "system", "content": f"<previous summary> {summary_text}"})

#   return kept

# def summarize_messages(msgs: list[dict]) -> str:
#   joined = "\n".join([f"{m['role']}: {m['content']}" for m in msgs])
#   prompt = "Summarize next 3 conversation rallies with users: \n" + joined[:4000]

#   resp = anthropic_client.messages.create(
#       model="claude-3-7-sonnet-20250219",
#       max_tokens=2048,
#       system="You are a skilful summariser.",
#       messages=[
#         {"role": "user", "content": prompt}
#       ]
#     )
#   return resp.content[0].text.strip()

### new version


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
  try:
    user_identifier = request.remote_addr
    user_id = get_user_id(user_identifier)
    history = load_json("chat_log.json", [])
    history_json = to_pretty_json(history)

    summary = load_json("chatsummary.json", [])
    summary_json = to_pretty_json(summary)

    user_history = load_json("user_history.json", {})
    user_history_json = to_pretty_json(user_history)

    data = request.get_json()
    user_input = data.get("message", "")
    print(f"User input: {user_input[:50]}...")

    user_message = {
        "role": "user", 
        "content": user_input, 
        "user_id": user_id,
        "timestamp": datetime.now().isoformat()
    }
    history.append(user_message)
    # print("Comporessing history...")
    # trimmed_history = compress_history(history)
    # print(trimmed_history)
    selected_prompt_id = session.get("selected_prompt_id")
    print(selected_prompt_id)
    base_prompt = "you are helpful AI assistant"
    if selected_prompt_id:
      prompt_obj = Prompt.query.filter_by(id=selected_prompt_id).first()
      if prompt_obj:
        print(f"Found prompt: {prompt_obj.name}")
        base_prompt = prompt_obj.content
      else:
        print("Prompt object not found for ID:", selected_prompt_id)

      print("Calling Anthropic API...")
      prompt = f"""
      {base_prompt}

      ---
      ###Summary fo conversation
      {summary_json}
      ###Recent conversation with users
      {user_history_json}
      """

      try:
        resp = anthropic_client.messages.create(
          model="claude-3-7-sonnet-20250219",
          max_tokens=2048,
          system=prompt,
          messages=[
            {"role": "user", "content": user_input}
          ]
        )
      except Exception as e:
        return jsonify({"error": str(e)}), 500
    assistant_text = resp.content[0].text
  
    assistant_message = {
        "role": "assistant", 
        "content": assistant_text, 
        "user_id": user_id,
        "id": str(uuid.uuid4()),  # Adding message ID like in the second code
        "timestamp": datetime.now().isoformat()
    }
    history.append(assistant_message)
    save_json(CHAT_LOG_FILE, history)

    try:
      summarize_user_history = anthropic_client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=2048,
        system="summarize the resopnse in one sentence in order to keep the conversation with users natural",
        messages=[
          {"role": "user", "content": assistant_text}
        ]
      )
    except Exception as e:
      return jsonify({"error": str(e)}), 500
    assistant_summary_message = {
        "role": "assistant", 
        "content": summarize_user_history.content[0].text, 
        "user_id": user_id,
        "id": str(uuid.uuid4()),  # Adding message ID like in the second code
        "timestamp": datetime.now().isoformat()
    }

    message_pair = {
        "user": user_message,
        "assistant": assistant_summary_message,
        "timestamp": datetime.now().isoformat()
    }
    update_user_messages(user_identifier, message_pair)

    if len(history) % 7 == 0:
      threading.Thread(
        target=generate_summary_in_background,
        args=(history_json,)
      ).start()

    return jsonify({
        "response": assistant_text,
        "timestamp": datetime.now().isoformat()
    })
  except Exception as e:
    error_details = traceback.format_exc()
    print(f"Error in/chat: {str(e)}\n{error_details}")
    return jsonify({"error": str(e), "details": error_details}), 500

@app.route("/clear", methods=["POST"])
def clear_chat_data():
  save_json(CHAT_LOG_FILE, [])
  save_json(SUMMARY_FILE, [])
  save_json(USER_HISTORY_FILE, {})
  return jsonify({"status": "success", "message": "チャットデータをクリアしました"})

@app.route("/prompt", methods=["GET"])
def get_prompts():
  prompts = Prompt.query.all()
  return render_template("list.html", data=prompts)

@app.route("/prompt/<int:prompt_id>", methods=["GET"])
def get_prompt(prompt_id):
  prompt = Prompt.query.filter_by(id=prompt_id).first()

  if not prompt:
    return render_template("error.html", message="プロンプトが見つかりません"), 404

  return render_template("edit.html", data=prompt)

@app.route("/prompt/<int:prompt_id>", methods=["PATCH"])
def update_prompt(prompt_id):
  prompt = Prompt.query.filter_by(id=prompt_id).first()
  if not prompt:
    return render_template("error.html", message="プロンプトが見つかりません"), 404
  p_data = request.get_json()
  if "content" in p_data:
    prompt.content = p_data["content"]

  db.session.commit()
  return render_template("edit.html", data=prompt)

@app.route("/prompt/<int:prompt_id>", methods=["DELETE"])
def delete_task(prompt_id):
  prompt = Prompt.query.filter_by(id=prompt_id).first()

  if not prompt:
    return render_template("error.html", message="プロンプトが見つかりません"), 404
  db.session.delete(prompt)
  db.session.commit()
  return render_template("edit.html", data=prompt)

@app.route("/prompts/create", methods=["POST"])
def create_prompt():
  p_data = request.get_json()

  if not p_data or "content" not in p_data or not isinstance(p_data["content"], str):
    return render_template("error.html", message="プロンプトが見つかりません"), 404

  new_prompt = Prompt(
    name=p_data["name"],
    content=p_data["content"],
    description=p_data["description"]    
  )
  db.session.add(new_prompt)
  db.session.commit()

  return render_template("edit.html", data=new_prompt)

@app.route("/select")
def select_prompt_page():
  prompts = Prompt.query.all()
  return render_template("select.html", prompts=prompts)

@app.route("/api/prompt/<int:prompt_id>")
def get_prompt_api(prompt_id):
  prompt = Prompt.query.filter_by(id=prompt_id).first()

  if not prompt:
    return render_template("error.html", message="prompt is not found"), 404
  
  return jsonify({
    "id": prompt.id,
    "name": prompt.name,
    "description": prompt.description,
    "content": prompt.content
  })

@app.route("/api/select-prompt", methods=["POST"])
def select_prompt_api():
  data = request.get_json()
  prompt_id = data.get("prompt_id")

  if not prompt_id:
    return jsonify({"success": False, "message": "prompt id is not assingend"}), 400

  prompt = Prompt.query.filter_by(id=prompt_id).first()
  if not prompt:
    return jsonify({"success": False, "message": "prompt is not found"}), 404

  print(f"selected_prompt_idを{prompt_id}に設定します")
  session["selected_prompt_id"] = prompt_id
  session["selected_prompt_name"] = prompt.name

  session.modified = True

  return jsonify({
    "success": True,
    "prompt_id": prompt_id,
    "prompt_name": prompt.name 
  })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)