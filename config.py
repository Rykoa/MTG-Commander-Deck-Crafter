import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = "claude-opus-4-6"

SCRYFALL_BASE_URL = "https://api.scryfall.com"
SCRYFALL_RATE_LIMIT_DELAY = 0.1  # 100ms between requests per Scryfall guidelines

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "knowledge")
