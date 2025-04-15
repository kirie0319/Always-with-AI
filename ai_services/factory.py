# ai_services/factory.py
from .anthropic import AnthropicService
from .openai import OpenAIService
import config

class AIServiceFactory:
  @staticmethod
  def create_service(provider, api_key):
    if provider.lower() == "anthropic":
      return AnthropicService(api_key)
    elif provider.lower() == "openai":
      return OpenAIService(api_key)
    else:
      raise ValueError(f"Unknown AI provider: {provider}")

class MultimodalAIService:
  def __init__(self, anthropic_key=None, openai_key=None, primary=None):
    self.services = {}

    if anthropic_key:
      self.services["anthropic"] = AnthropicService(anthropic_key)
    if openai_key:
      self.services["openai"] = OpenAIService(openai_key)
    
    if not self.services:
      raise ValueError("Need the API key at least one to initialize AI service")
    
    available_providers = list(self.services.keys())
    if primary and primary in self.services:
      self.primary = primary
    else:
      self.primary = config.DEFAULT_AI_PROVIDER if config.DEFAULT_AI_PROVIDER in self.services else available_providers[0]

    self.secondary = None
    secondary_options = [p for p in available_providers if p != self.primary]
    if secondary_options:
      self.secondary = secondary_options[0]


  def generate_response(self, messages, options=None):
    options = options or {}
    provider = options.get("provider", self.primary)

    if provider not in self.services:
      if not self.services:
        raise ValueError("no avalable AI service")
      provider = self.primary
    try:
      return self.services[provider].generate_response(messages, options)
    except Exception as e:
      print(f"Error with {provider}: {str(e)}")

      if self.secondary and provider != self.secondary:
        print(f"Failing over to {self.secondary}")
        try:
          return self.services[self.secondary].generate_response(messages, options)
        except Exception as fallback_error:
          raise Exception(f"All AI services failed. Primary error: {e}, Fallback error: {fallback_error}")
      else:
        raise
  
  def get_available_models(self):
    result = {}
    for provider, service in self.services.items():
      result[provider] = service.get_models()
    return result

  def get_available_providers(self):
    return list(self.services.keys())