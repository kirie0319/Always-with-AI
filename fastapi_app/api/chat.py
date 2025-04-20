# fast_app/api/chat.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from anthropic import Anthropic, APIStatusError
from datetime import datetime
from dotenv import load_dotenv
from models import db, Prompt 
from .deps import provide_session
import json, uuid, threading, yaml, traceback, sys, time, os
from colorama import Fore, Style, init 
from tasks import generate_summary_task
from utils import load_json, save_json, to_pretty_json, get_last_conversation_pair, get_user_id, update_user_messages, MAX_RALLIES

load_dotenv()

YAML_PATH = "prompts/specific/finance.yaml"
MAX_TOKENS_INPUT  = 8_000   # Claude に渡す入力上限
MAX_TOKENS_OUTPUT = 512     # 期待する出力上限
SAFETY_MARGIN     = 500     # header 系を見込んだ余白

anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

anthropic_client = anthropic.Anthropic(
  api_key=anthropic_api_key,
)

router = APIRouter()

@router.post("/chat")
async def chat_dummy(
  request: Request,
  session = Depends(provide_session)
):
  # receive the data
  body = await request.json()
  user_input = data.get("message", "")

  # user infomation
  user_identifier = request.client.host 
  user_id = get_user_id(user_identifier)

  # history information
  history       = load_json("chat_log.json", [])
  history_json  = to_pretty_json(history)
  summary_json  = to_pretty_json(load_json("chatsummary.json", []))
  user_hist_obj = load_json("user_history.json", {})
  user_hist_json = to_pretty_json(user_hist_obj)
  last_pair     = get_last_conversation_pair()
  last_two_json = json.dumps(last_pair, ensure_ascii=False, indent=2) if last_pair else "会話履歴が見つかりませんでした。"

  # prompt
  selected_id = request.session.get("selected_prompt_id")
  base_prompt = "you are helpful AI assistant"
  if selected_id:
    prompt_obj = db_session.query(Prompt).get(selected_id)
    if prompt_obj:
      base_prompt = prompt_obj.content
  system_prompt = f"""{base_prompt}
  ---
  ###Summary of conversation
  {summary_json}
  ###Recent conversation with users
  {user_hist_json}
  ###Last conversations with users
  {last_two_json}
  """
  async def evnet_stream():
    request_text = ""
    try:
      with anthropic_client.messages.stream(
        model="claude-3-7-sonnet-20250219",
        max_tokens=8000,
        system=system_prompt,
        messages=[
          {
            "role": "user",
            "content": user_input
          }
        ]
      ) as stream:
          for chunk in stream.text_stream:
            resq_text += chunk
            yield f"data: {json.dumps({'text': chunk})}\n\n"
    except APIStatusError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return
    assistant_msg = {
      "role": "assistant", "content": resq_text,
      "user_id": user_id, "id": str(uuid.uuid4()),
      "timestamp": datetime.now().isoformat()
    }
    history.append(
      {
        "role": "user",
        "content": user_input,
        "user": user_id,
        "timestamp": datetime.now().isoformat()
      }
    )
    history.append(assistant_msg)
    save_json("chat_log.json", history)

    generate_summary_task.delay(history_json)

    message_pair = {
      "user": history[-2],
      "assistant": assistant_msg,
      "timestamp": datetime.now().isoformat()
    }
    update_user_messages(user_identifier, message_pair)
  return StreamingResponse(evnet_stream(), media_type="text/event-stream")
  