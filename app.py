from flask import Flask, request, jsonify, render_template, redirect, url_for
from openai import OpenAI
from dotenv import load_dotenv
import os
import anthropic
from datetime import datetime
import json
import uuid
import threading
import yaml

load_dotenv()

CHAT_LOG_FILE = "chat_log.json"
SUMMARY_FILE = "chatsummary.json"
USER_HISTORY_FILE = "user_history.json"
MAX_RALLIES = 7
YAML_PATH = "prompts/specific/finance.yaml"

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
      max_tokens=1024,
      messages=[
        {"role": "user", "content": summarizing_prompt}
      ]
    )
    summary = [{"role": "developer", "content": anthropic_summary.content[0].text}]
    save_json(SUMMARY_FILE, summary)
    print("Summary generated successfully")
  except Exception as e:
    print(f"Error generating summary: {e}")


# openai_api_key = os.getenv("OPENAI_API_KEY")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

# openai_client = OpenAI(api_key=openai_api_key)
anthropic_client = anthropic.Anthropic(
  api_key=anthropic_api_key,
)


app = Flask(__name__, static_url_path='/static')

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
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

    user_message = {
        "role": "user", 
        "content": user_input, 
        "user_id": user_id,
        "timestamp": datetime.now().isoformat()
    }
    history.append(user_message)
    with open(YAML_PATH, "r", encoding="utf-8") as f:
      prompt_data = yaml.safe_load(f)
    base_propmt = prompt_data["content"]

    prompt = f"""
    {base_propmt}

    ---
    ###Summary fo conversation
    {summary_json}
    ###Recent conversation with users
    {user_history_json}
    """

    

    # openai_response = openai_client.responses.create(
    #     model="gpt-4o",
    #     input=user_input,
    #     instructions=prompt,
    #     store=False
    # )

    anthropic_message = anthropic_client.messages.create(
      model="claude-3-7-sonnet-20250219",
      max_tokens=1024,
      system=prompt,
      messages=[
        {"role": "user", "content": user_input}
      ]
    )
    

    assistant_message = {
        "role": "assistant", 
        "content": anthropic_message.content[0].text, 
        "user_id": user_id,
        "id": str(uuid.uuid4()),  # Adding message ID like in the second code
        "timestamp": datetime.now().isoformat()
    }
    history.append(assistant_message)
    save_json(CHAT_LOG_FILE, history)

    message_pair = {
        "user": user_message,
        "assistant": assistant_message,
        "timestamp": datetime.now().isoformat()
    }
    update_user_messages(user_identifier, message_pair)

    if len(history) % 7 == 0:
      threading.Thread(
        target=generate_summary_in_background,
        args=(history_json,)
      ).start()

    return jsonify({
        "response": anthropic_message.content[0].text,
        "timestamp": datetime.now().isoformat()
    })

@app.route("/clear", methods=["POST"])
def clear_chat_data():
  save_json(CHAT_LOG_FILE, [])
  save_json(SUMMARY_FILE, [])
  save_json(USER_HISTORY_FILE, {})
  return jsonify({"status": "success", "message": "チャットデータをクリアしました"})

@app.route("/edit", methods=["GET"])
def show_editor():
  if not os.path.exists(YAML_PATH):
    return "YAML file not found", 404
  with open(YAML_PATH, "r", encoding="utf-8") as f:
    data = yaml.safe_load(f)
  return render_template("edit.html", data=data)

@app.route("/update", methods=["POST"])
def update_yaml():
  new_content = request.form.get("content", "")

  if os.path.exists(YAML_PATH):
    with open(YAML_PATH, "r", encoding="utf-8") as f:
      data = yaml.safe_load(f)
  else:
    return "YAML file is not found", 404
  data["content"] = new_content
  with open(YAML_PATH, "w", encoding="utf-8") as f:
    yaml.dump(data, f, allow_unicode=True, sort_keys=False)
  return redirect(url_for("show_editor", saved="true"))

if __name__ == '__main__':
    # port = int(os.environ.get('PORT', 5000))
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)