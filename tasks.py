# tasks.py
from celery import shared_task
import json
import os
import logging
from datetime import datetime
from anthropic import Anthropic
from openai import OpenAI
import aiofiles
import asyncio
import config

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
openrouter_client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=os.getenv("OPENROUTER_API_KEY")
)


async def load_json(filepath, default):
  try:
    async with aiofiles.open(filepath, "r", encoding='utf-8') as f:
      content = await f.read()
      return json.loads(content)
  except (FileNotFoundError, json.JSONDecodeError):
    return default

async def save_json(filepath, data):
  async with aiofiles.open(filepath, "w", encoding='utf-8') as f:
    await f.write(json.dumps(data, indent=2, ensure_ascii=False))

async def to_pretty_json(data):
  return json.dumps(data, ensure_ascii=False, indent=2)

CHATROOM_FILE = "data/chatroom.json"

async def get_user_files(user_id):
  return {
    "chat_log": f"data/chat_log_{user_id}.json",
    "summary": f"data/summary_{user_id}.json",
    "user_history": f"data/user_history_{user_id}.json"
  }

async def get_or_create_chatroom(user_id):
  chatrooms = await load_json(CHATROOM_FILE, {})

  if user_id not in chatrooms:
    user_files = await get_user_files(user_id)
    await save_json(user_files["chat_log"], [])
    await save_json(user_files["summary"], [])
    await save_json(user_files["user_history"], {})

    chatrooms[user_id] = {
      "creaated_ai": datetime.now().isoformat(),
      "files": user_files
    }
    await save_json(CHATROOM_FILE, chatrooms)
  return chatrooms[user_id]

async def get_last_conversation_pair(user_id):
  chatroom = await get_or_create_chatroom(user_id)
  history = await load_json(chatroom["files"]["chat_log"], [])
  if len(history) < 2:
    return None
  for i in range(len(history) - 2, -1, -1):
    if history[i]["role"] == "user" and history[i + 1]["role"] == "assistant":
      return {
        "user": history[i],
        "assistant": history[i + 1]
      }
  return None 

@shared_task
def generate_summary_task(history_json, user_id):

  def run_async(coro):
    return asyncio.run(coro)
  try:
    chatroom = run_async(get_or_create_chatroom(user_id))
    user_files = chatroom["files"]
    last_pair = run_async(get_last_conversation_pair(user_id))
    if last_pair:
      last_two_json = json.dumps(last_pair, ensure_ascii=False, indent=2)
    else:
      last_two_json = "We can't find the conversation history"
    user_history = run_async(load_json(user_files["user_history"], {}))
    user_history_json = run_async(to_pretty_json(user_history))
    summary = run_async(load_json(user_files["summary"], []))
    summary_json = run_async(to_pretty_json(summary))
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

    And this is the last conversation with users:
    {last_two_json}
    """
    models_to_try = [
      "claude-3-7-sonnet-20250219",
      "gpt-4o"
    ]
    models_to_try = [m for m in models_to_try if m is not None]
    last_exception = None
    for current_model in models_to_try:
      try:    
        resp = openrouter_client.chat.completions.create(
          model=current_model,
          max_tokens=4000,
          messages=[
            {"role": "user", "content": summarizing_prompt}
          ]
        )
        summary = [{"role": "developer", "content": resp.content[0].text}]
        run_async(save_json(user_files["summary"], summary))
        print(f"Summary generated successfully for user {user_id}")
        return
      except Exception as e:
        logging.warning(f"Failed to generate summary with model {current_model}: {str(e)}")
        last_exception = e
        continue
    
    # If all models fail
    logging.error("Failed to generate summary with any model")
    raise last_exception or ValueError("No models could generate a summary")
  except Exception as e:
    print(f"Error generating summary: {e}")
    import traceback
    print(traceback.format_exc())