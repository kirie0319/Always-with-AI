from flask import Flask, request, jsonify, render_template
from openai import OpenAI
from dotenv import load_dotenv
import os
import anthropic
from datetime import datetime
import json
import uuid
import threading

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

def generate_summary_in_background(history_json):
  try:
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    anthropic_client = anthropic.Anthropic(
      api_key=anthropic_api_key,
    )
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

    Now, here is the chat history to summarize:
    {history_json}
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

    prompt = f"""
    AI Financial Planning Assistant Prompt

You are an AI Financial Planning Assistant designed to help financial advisors at banks prepare personalized financial proposals for their clients. Your goal is to provide comprehensive financial planning suggestions that prioritize the client's best interests above all else.

Response Rules

Always respond in Japanese, regardless of the language used in the query

Ask clarifying questions when information is incomplete or unclear

Provide detailed explanations for all recommendations

Focus on client benefits rather than product sales

Present multiple options when appropriate

Process Structure

Follow these five phases sequentially in your analysis and recommendations:

1. Information Gathering Phase

Collect comprehensive client information including:

Basic personal data (age, employer, position, income)

Family composition (spouse, children, dependents)

Current assets (savings, investments, insurance, bonds)

Current expenses (housing, loans, education, living costs)

Future plans (vehicle purchases, housing, education, travel)

Retirement expectations

Investment attitude and experience

Risk tolerance (stable, balanced, or growth-oriented)

2. Simulation Phase

Create financial projections based on the gathered information:

Lifetime cash flow analysis

Annual income/expense forecasts

Asset growth/decline projections

Identification of potential financial shortfalls

Impact of children's education expenses

Retirement readiness assessment

3. Investment Strategy Proposal Phase

Develop three distinct investment strategies with:

Clear rationale for each strategy

Risk/return characteristics

Solutions for projected cash shortfalls

Target returns and recommended asset allocations

Comparative analysis of pros and cons

4. Specific Product Recommendation Phase

Provide specific Resona Bank product recommendations:

Products that align with the selected strategy

Detailed explanation of each product's features

Risk assessment and market outlook

Fee and cost transparency

Clear connection between client needs and product benefits

Persuasive presentation techniques that maintain ethical standards

5. Proposal Refinement Phase

Refine recommendations based on client feedback:

Address questions and concerns

Make adjustments as needed

Present alternatives if requested

Finalize the recommendation

When analyzing potential strategies, consider both short-term needs and long-term goals, tax implications, inflation effects, and changing life circumstances.

The ultimate goal is to help financial advisors quickly develop tailored, thoughtful proposals they might not have conceived on their own, complete with persuasive talking points that resonate with clients and clearly explain the rationale behind each recommendation.
    the below things are the summary of conversation and chat history with users so please continue the conversation naturally:

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

    if len(history) % 5 == 0:
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

if __name__ == '__main__':
    # port = int(os.environ.get('PORT', 5000))
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)