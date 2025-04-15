# ai_services/openai.py
import time 
import random
from openai import OpenAI
from .base import AIService
import config

class OpenAIService(AIService):
  def __init__(self, api_key):
    self.client = OpenAI(api_key=api_key)
    self.models = ["gpt-4o", "gpt-4", "gpt-3.5-turbo"]

  def generate_response(self, messages, options=None):
    options = options or {}
    max_retries = options.get("max_retries", config.MAX_RETRIES)
    model = options.get("model", config.DEFAULT_OPENAI_MODEL)
    max_tokens = options.get("max_tokens", config.MAX_TOKENS)
    retries = 0
    while retries < max_retries:
      try:
        response = self.client.responses.create(
          model=model,
          input=messages
        )
        return {
          "cotent": response.output_text,
          "provider": "openai",
          "model": model
        }
      except Exception as e:
        print(f"OpneAI API error: {str(e)}")
        raise 
  
  def get_models(self):
    return self.models