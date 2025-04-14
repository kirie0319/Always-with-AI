# prompts/loader.py
import os
import yaml
from datetime import datetime
import config

class PromptLoader:
  def __init__(self, prompts_dir=None):
    self.prompts_dir = prompts_dir or config.PROMPTS_DIR

    for dir_path in [
      self.prompts_dir,
      os.path.join(self.prompts_dir, "system"),
      os.path.join(self.prompts_dir, "general"),
      os.path.join(self.prompts_dir, "specific")
    ]:
      os.makedirs(dir_path, exist_ok=True)
  def load_prompt(self, category, name):
    prompt_path = os.path.join(self.prompts_dir, category, f"{name}.yaml")

    try:
      with open(prompt_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)
    except FileNotFoundError:
      raise ValueError(f"Prompt not found: {category}/{name}")
    except yaml.YAMLError:
      raise ValueError(f"Invalid YAML in prompt file: {category}/{name}")
    
  def list_prompts(self):
    result = {}
    for category in os.listdir(self.prompts_dir):
      category_path = os.path.join(self.prompts_dir, category)

      if os.path.isdir(category_path) and not category.startswith('__'):
        prompt_files = []

        for filename in os.listdir(category_path):
          if filename.endswith(".yaml"):
            prompt_name = os.path.splittext(filename)[0]
            prompt_files.append(prompt_name)

        if prompt_files:
          result[category]= prompt_files

    return result
  
  def process_variables(self, content, variables=None):
    variables = variables or {}
    default_vars = {
      "date": datetime.now().strftime('%Y-%m-%d'),
    }

    vars_dict = {**default_vars, **variables}

    processed_content = content
    for var_name, var_value in vars_dict.items():
      placeholder = f"{{{{{var_name}}}}}"
      processed_content.replace(placeholder, str(var_value))

    return processed_content