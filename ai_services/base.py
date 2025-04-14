# ai_services/base.py
from abc import ABC, abstractmethod

class AIService(ABC):
  @abstractmethod
  def generate_response(self, user_input, system_prompt="", model=None, max_tokens=1024):
    pass 
  
  @abstractmethod
  def get_models(self):
    pass 