# ai_services/anthropic.py
import time
import random
from anthropic._exceptions import OverloadedError
from anthropic import Anthropic
from .base import AIService
import config

class AnthropicService(AIService):
  def __init__(self, api_key):
    self.client = Anthropic(api_key=api_key)
    self.models = ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307", "claude-3-7-sonnet-20250219"]

  def generate_response(self, messages, options=None):
    options = options or {}
    max_retries = options.get("max_retries", config.MAX_RETRIES)
    model = options.get("model", config.DEFAULT_ANTHROPIC_MODEL)
    max_tokens = options.get("max_tokens", config.MAX_TOKENS)
    system_content = options.get("system", None)

    formatted_messages = []

    for msg in messages:
      formatted_messages.append(msg)

    retries = 0
    while retries < max_retries:
      try:
        response = self.client.messages.create(
          model=model,
          max_tokens=max_tokens,
          system=system_content,
          messages=formatted_messages
        )
        return {
          "content": response.content[0].text,
          "provider": "anthropic",
          "model": model 
        }
      except OverloadedError:
        retries += 1
        if retries >= max_retries:
          raise
        backoff_time = (2 ** retries) + random.random()
        print(f"Anthropic API overloaded, retrying in {backoff_time:.2f} seconds...")
        time.sleep(backoff_time)
      except Exception as e:
        print(f"Anthropic API error: {str(e)}")
        raise
    
  def get_models(self):
    return self.models