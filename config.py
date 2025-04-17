# config.py
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DEBUG = os.getenv("DEBUG", "True").lower() == "true"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5001))

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

DEFAULT_AI_PROVIDER = os.getenv("DEFAULT_AI_PROVIDER", "anthropic")
DEFAULT_ANTHROPIC_MODEL = os.getenv("DEFAULT_ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219")
DEFAULT_OPENAI_MODEL = os.getenv("DEFAULT_OPENAI_MODEL", "gpt-4o")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", 1024))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))

MAX_RALLIES = int(os.getenv("MAX_RALLIES", 7))

PROMPTS_DIR = os.getenv("PROMPTS_DIR", "prompts")
CHAT_LOG_FILE = "chat_log.json"
SUMMARY_FILE = "chatsummary.json"
USER_HISTORY_FILE = "user_history.json"
MAX_RALLIES = 6
YAML_PATH = "prompts/specific/finance.yaml"
MAX_TOKENS_INPUT  = 8_000   # Claude に渡す入力上限
MAX_TOKENS_OUTPUT = 512     # 期待する出力上限
SAFETY_MARGIN     = 500     # header 系を見込んだ余白