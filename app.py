from flask import Flask, request, jsonify, render_template
from openai import OpenAI
from dotenv import load_dotenv
import os
import anthropic
from datetime import datetime
import json
import uuid

load_dotenv()

CHAT_LOG_FILE = "chat_log.json"
SUMMARY_FILE = "chatsummary.json"
USER_HISTORY_FILE = "user_history.json"
MAX_RALLIES = 7

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

openai_api_key = os.getenv("OPENAI_API_KEY")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

openai_client = OpenAI(openai_api_key)
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

    prompt = f"""
    ルフィーみたく振る舞ってみて。
    the below things are the summary of conversation and chat history with users so please continue the conversation naturally:

    ---
    ###Summary fo conversation
    {summary_json}
    ###Recent conversation with users
    {user_history_json}
    """

    summarizing_prompt = f"""You are an expert conversation summarizer.

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

    Now, here is the chat history to summarize:
    {history_json}
    """

    openai_response = openai_client.responses.create(
        model="gpt-4o",
        input=user_input,
        instructions=prompt,
        store=False
    )

    anthropic_message = anthropic_client.messages.create(
      model="claude-3-7-sonnet-20250219",
      max_tokens=1024,
      system=prompt,
      messages=[
        {"role": "user", "content": user_input}
      ]
    )
    
    anthropic_summary = anthropic_client.messages.create(
      model="claude-3-7-sonnet-20250219",
      max_tokens=1024,
      messages=[
        {"role": "user", "content": summarizing_prompt}
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

    summary = [{"role": "developer", "content": anthropic_summary.content[0].text}]
    save_json(SUMMARY_FILE, summary)

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

if __name__ == '__main__':
    app.run(debug=True)