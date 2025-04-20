# tasks.py
from celery import shared_task
import json
import os
from datetime import datetime
from anthropic import Anthropic
from utils import load_json, save_json, to_pretty_json, get_last_conversation_pair
import config

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

@shared_task
def generate_summary_task(history_json):
  last_pair = get_last_conversation_pair()
  if last_pair:
    last_two_json = json.dumps(last_pair, ensure_ascii=False, indent=2)
  else:
    last_two_json = "会話履歴が見つかりませんでした。"
  try:
    user_history = load_json(config.USER_HISTORY_FILE, {})
    user_history_json = to_pretty_json(user_history)
    summary = load_json(config.SUMMARY_FILE, [])
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

    And this is the last conversation with users:
    {last_two_json}
    """
    resp = client.messages.create(
      model="claude-3-7-sonnet-20250219",
      max_tokens=4000,
      messages=[
        {"role": "user", "content": summarizing_prompt}
      ]
    )
    summary = [{"role": "developer", "content": resp.content[0].text}]
    save_json(config.SUMMARY_FILE, summary)
    print("Summary generated successfully")
  except Exception as e:
    print(f"Error generating summary: {e}")