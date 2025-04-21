# # app.py
# from flask import Flask, request, jsonify, render_template, redirect, url_for, session, Response
# from flask_migrate import Migrate 
# from openai import OpenAI
# from dotenv import load_dotenv
# from datetime import datetime
# from models import db, Prompt 
# import json, uuid, threading, yaml, traceback, sys, time, config, os, anthropic
# from colorama import Fore, Style, init 
# from tasks import generate_summary_task
# from utils import load_json, save_json, to_pretty_json, get_last_conversation_pair

# load_dotenv()

# MAX_RALLIES = 6
# YAML_PATH = "prompts/specific/finance.yaml"
# MAX_TOKENS_INPUT  = 8_000   # Claude に渡す入力上限
# MAX_TOKENS_OUTPUT = 512     # 期待する出力上限
# SAFETY_MARGIN     = 500     # header 系を見込んだ余白

# anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

# anthropic_client = anthropic.Anthropic(
#   api_key=anthropic_api_key,
# )


# app = Flask(__name__, static_url_path='/static')
# app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 
# app.secret_key = os.getenv("FLASK_SECRET_KEY")
# db.init_app(app)
# migrate = Migrate(app, db)

# def get_user_id(user_identifier):
#   user_history = load_json(config.USER_HISTORY_FILE, {})

#   if user_identifier is None or isinstance(user_history, list):
#     user_history = {}

#   if user_identifier not in user_history:
#     user_history[user_identifier] = {
#       "user_id": str(uuid.uuid4()),
#       "created_at": datetime.now().isoformat(),
#       "messages": []
#     }
#     save_json(config.USER_HISTORY_FILE, user_history)

#   return user_history[user_identifier]["user_id"]

# def update_user_messages(user_identifier, message_pair):
#   user_history = load_json(config.USER_HISTORY_FILE, {})
#   history = load_json(config.CHAT_LOG_FILE, [])

#   if user_history is None or isinstance(user_history, list):
#     user_history = {}

#   if user_identifier not in user_history:
#     get_user_id(user_identifier)
#     user_history = load_json(config.USER_HISTORY_FILE, {})

#     if user_history is None or isinstance(user_history, list):
#       user_history = {}
#       user_history[user_identifier] = {
#         "user_id": str(uuid.uuid4()),
#         "created_at": datetime.now().isoformat(),
#         "messages": []
#       }
#   if "messages" not in user_history[user_identifier]:
#     user_history[user_identifier]["messages"] = []

#   if len(history) > 2:
#     user_history[user_identifier]["messages"].append(history[-4:-2])

#   if len(user_history[user_identifier]["messages"]) > MAX_RALLIES:
#     user_history[user_identifier]["messages"] = user_history[user_identifier]["messages"][-MAX_RALLIES:]

#   save_json(config.USER_HISTORY_FILE, user_history)

# def stream_response(user_input):
#   max_retries = 5
#   retry_count = 0
#   backoff_time = 1
#   while retry_count < max_retries:
#     try:
#       with anthropic_client.messages.stream(
#         model="claude-3-7-sonnet-20250219",
#         max_tokens=4000,
#         system="You are helpfull AI assistant",
#         messages=[
#           {"role": "user", "content": user_input}
#         ]
#       ) as stream:
#           assistant_response = ""
#           for text in stream.text_stream:
#             print(text, end="", flush=True)
#             assistant_response += text 
#     except anthropic.APIStatusError as e:
#       if hasattr(e, '_status_code') and e._status_code == 429 or 'overloaded_error' in str(e):
#         retry_count += 1
#         if retry_count < max_retries:
#           print(f"\n{Fore.YELLOW}APIが混雑しています。{backoff_time}秒後に再試行します...{Style.RESET_ALL}")
#           import time
#           time.sleep(backoff_time)
#           backoff_time *= 2
#           print(f"\n{Fore.BLUE}Claude: {Style.RESET_ALL}", end="")
#         else:
#           print(f"\n{Fore.RED}APIが混雑しているため、リクエストを完了できませんでした。しばらく時間をおいてお試しください。{Style.RESET_ALL}\n")
#           return
#       else:
#         print(f"\n{Fore.RED}エラーが発生しました: {e}{Style.RESET_ALL}\n")
#         return

# @app.route("/")
# def index():
#     return render_template("index.html")

# @app.route("/chat", methods=["POST"])
# def chat():
#   max_retries = 5
#   retry_count = 0
#   backoff_time = 1
#   try:
#     last_pair = get_last_conversation_pair()
#     if last_pair:
#       last_two_json = json.dumps(last_pair, ensure_ascii=False, indent=2)
#     else:
#       last_two_json = "会話履歴が見つかりませんでした。"
#     user_identifier = request.remote_addr
#     user_id = get_user_id(user_identifier)
#     history = load_json("chat_log.json", [])
#     history_json = to_pretty_json(history)

#     summary = load_json("chatsummary.json", [])
#     summary_json = to_pretty_json(summary)

#     user_history = load_json("user_history.json", {})
#     user_history_json = to_pretty_json(user_history)

#     data = request.get_json()
#     user_input = data.get("message", "")
#     print(f"User input: {user_input[:50]}...")

#     user_message = {
#         "role": "user", 
#         "content": user_input, 
#         "user_id": user_id,
#         "timestamp": datetime.now().isoformat()
#     }
#     history.append(user_message)
#     selected_prompt_id = session.get("selected_prompt_id")
#     print(selected_prompt_id)
#     base_prompt = "you are helpful AI assistant"
#     if selected_prompt_id:
#       prompt_obj = Prompt.query.filter_by(id=selected_prompt_id).first()
#       if prompt_obj:
#         print(f"Found prompt: {prompt_obj.name}")
#         base_prompt = prompt_obj.content
#       else:
#         print("Prompt object not found for ID:", selected_prompt_id)
    

#       print("Calling Anthropic API...")
#       prompt = f"""
#       {base_prompt}

#       ---
#       ###Summary fo conversation
#       {summary_json}
#       ###Recent conversation with users
#       {user_history_json}
#       ###Last conversation with users
#       {last_two_json}
#       """


#       def generate():
#         resp = ""
#         retry_count = 0
#         backoff_time = 1
#         try:
#           with anthropic_client.messages.stream(
#             model="claude-3-7-sonnet-20250219",
#             max_tokens=8000,
#             system=prompt,
#             messages=[
#               {"role": "user", "content": user_input}
#             ]
#           ) as stream:
#               for text in stream.text_stream:
#                 print(text, end="", flush=True)
#                 resp += text
#                 assistant_text = resp
#                 yield f"data: {json.dumps({'text': text})}\n\n"
#           assistant_message = {
#             "role": "assistant", 
#             "content": assistant_text, 
#             "user_id": user_id,
#             "id": str(uuid.uuid4()),  # Adding message ID like in the second code
#             "timestamp": datetime.now().isoformat()
#           }
#           history.append(assistant_message)
#           save_json(config.CHAT_LOG_FILE, history)

#           try:
#             summarize_user_history = anthropic_client.messages.create(
#               model="claude-3-haiku-20240307",
#               max_tokens=2048,
#               system="""You are an expert conversation summarizer.

#               Your task is to analyze and summarize response of AI assistant. The goal is to extract key details and provide a clear, short, structured summary of the conversation.

#               Use the following output format:

#               ---

#               ### Chat Summary

#               #### 1. **Overview**
#               Briefly describe the overall context of the conversation, the participants, and the tone.

#               #### 2. **Key Points**
#               List 5-7 bullet points that highlight the most important facts, insights, or decisions discussed during the conversation.

#               #### 3. **Topic Timeline** (optional)
#               If applicable, outline the main topics discussed in chronological order.

#               #### 4. **Follow-up Items**
#               List any remaining questions, action items, or topics that could be explored further.

#               #### 5. **Context Notes**
#               Mention any relevant background, such as the fictional setting, tone of the assistant, or relationship between participants.

#               ---
#               """,
#               messages=[
#                 {"role": "user", "content": assistant_text}
#               ]
#             )
#           except Exception as e:
#             yield f"data: {json.dumps({'error': str(e)})}\n\n"
#           assistant_summary_message = {
#               "role": "assistant", 
#               "content": summarize_user_history.content[0].text, 
#               "user_id": user_id,
#               "id": str(uuid.uuid4()),  # Adding message ID like in the second code
#               "timestamp": datetime.now().isoformat()
#           }

#           message_pair = {
#               "user": user_message,
#               "assistant": assistant_summary_message,
#               "timestamp": datetime.now().isoformat()
#           }
#           update_user_messages(user_identifier, message_pair)

#           if len(history) % 1 == 0:
#             generate_summary_task.delay(history_json)
#         except anthropic.APIStatusError as e:
#           if hasattr(e, '_status_code') and e._status_code == 429 or 'overloaded_error' in str(e):
#             retry_count += 1
#             if retry_count < max_retries:
#               print(f"\n{Fore.YELLOW}APIが混雑しています。{backoff_time}秒後に再試行します...{Style.RESET_ALL}")
#               import time
#               time.sleep(backoff_time)
#               backoff_time *= 2
#               print(f"\n{Fore.BLUE}Claude: {Style.RESET_ALL}", end="")
#             else:
#               print(f"\n{Fore.RED}APIが混雑しているため、リクエストを完了できませんでした。しばらく時間をおいてお試しください。{Style.RESET_ALL}\n")
#               yield f"data: {json.dumps({'error': str(e)})}\n\n"
#           else:
#             print(f"\n{Fore.RED}エラーが発生しました: {e}{Style.RESET_ALL}\n")
#             return jsonify({"error": str(e)}), 500
#         except Exception as e:
#           yield f"data: {json.dumps({'error': str(e)})}\n\n"
#           error_details = traceback.format_exc()
#           print(f"Error in/chat: {str(e)}\n{error_details}")
#       return Response(generate(), mimetype='text/event-stream')
#   except Exception as e:
#     error_details = traceback.format_exc()
#     print(f"Error in/chat: {str(e)}\n{error_details}")
#     return jsonify({"error": str(e), "details": error_details}), 500

# @app.route("/clear", methods=["POST"])
# def clear_chat_data():
#   save_json(config.CHAT_LOG_FILE, [])
#   save_json(config.SUMMARY_FILE, [])
#   save_json(config.USER_HISTORY_FILE, {})
#   return jsonify({"status": "success", "message": "チャットデータをクリアしました"})

# @app.route("/prompt", methods=["GET"])
# def get_prompts():
#   prompts = Prompt.query.all()
#   return render_template("list.html", data=prompts)

# @app.route("/prompt/<int:prompt_id>", methods=["GET"])
# def get_prompt(prompt_id):
#   prompt = Prompt.query.filter_by(id=prompt_id).first()

#   if not prompt:
#     return render_template("error.html", message="プロンプトが見つかりません"), 404

#   return render_template("edit.html", data=prompt)

# @app.route("/prompt/<int:prompt_id>", methods=["PATCH"])
# def update_prompt(prompt_id):
#   prompt = Prompt.query.filter_by(id=prompt_id).first()
#   if not prompt:
#     return render_template("error.html", message="プロンプトが見つかりません"), 404
#   p_data = request.get_json()
#   if "content" in p_data:
#     prompt.content = p_data["content"]

#   db.session.commit()
#   return render_template("edit.html", data=prompt)

# @app.route("/prompt/<int:prompt_id>", methods=["DELETE"])
# def delete_task(prompt_id):
#   prompt = Prompt.query.filter_by(id=prompt_id).first()

#   if not prompt:
#     return render_template("error.html", message="プロンプトが見つかりません"), 404
#   db.session.delete(prompt)
#   db.session.commit()
#   return render_template("edit.html", data=prompt)

# @app.route("/prompts/create", methods=["POST"])
# def create_prompt():
#   p_data = request.get_json()

#   if not p_data or "content" not in p_data or not isinstance(p_data["content"], str):
#     return render_template("error.html", message="プロンプトが見つかりません"), 404

#   new_prompt = Prompt(
#     name=p_data["name"],
#     content=p_data["content"],
#     description=p_data["description"]    
#   )
#   db.session.add(new_prompt)
#   db.session.commit()

#   return render_template("edit.html", data=new_prompt)

# @app.route("/select")
# def select_prompt_page():
#   prompts = Prompt.query.all()
#   return render_template("select.html", prompts=prompts)

# @app.route("/api/prompt/<int:prompt_id>")
# def get_prompt_api(prompt_id):
#   prompt = Prompt.query.filter_by(id=prompt_id).first()

#   if not prompt:
#     return render_template("error.html", message="prompt is not found"), 404
  
#   return jsonify({
#     "id": prompt.id,
#     "name": prompt.name,
#     "description": prompt.description,
#     "content": prompt.content
#   })

# @app.route("/api/select-prompt", methods=["POST"])
# def select_prompt_api():
#   data = request.get_json()
#   prompt_id = data.get("prompt_id")

#   if not prompt_id:
#     return jsonify({"success": False, "message": "prompt id is not assingend"}), 400

#   prompt = Prompt.query.filter_by(id=prompt_id).first()
#   if not prompt:
#     return jsonify({"success": False, "message": "prompt is not found"}), 404

#   print(f"selected_prompt_idを{prompt_id}に設定します")
#   session["selected_prompt_id"] = prompt_id
#   session["selected_prompt_name"] = prompt.name

#   session.modified = True

#   return jsonify({
#     "success": True,
#     "prompt_id": prompt_id,
#     "prompt_name": prompt.name 
#   })

# if __name__ == '__main__':
#     # port = int(os.environ.get('PORT', 5000))
#     port = int(os.environ.get('PORT', 5001))
#     app.run(host='0.0.0.0', port=port)
from wsgi import app