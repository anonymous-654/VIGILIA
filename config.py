from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(os.getenv("AGENTS_WILD_DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

RAW_SESSION_DIR = DATA_DIR / "sessions"
CORRUPTION_DIR = DATA_DIR / "corruptions"
EVAL_DIR = DATA_DIR / "evaluations"
REPLAY_DIR = DATA_DIR / "replayed_sessions"

RAW_SESSION_DIR.mkdir(parents=True, exist_ok=True)
CORRUPTION_DIR.mkdir(parents=True, exist_ok=True)
EVAL_DIR.mkdir(parents=True, exist_ok=True)
REPLAY_DIR.mkdir(parents=True, exist_ok=True)

AZUREOPENAI_ENDPOINT = os.getenv("AZUREOPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

API_VERSION = os.getenv("AZURE_API_VERSION", "2024-12-01-preview")
LOCAL_BASE_URL = os.getenv("LOCAL_BASE_URL", "http://gl1504.arc-ts.umich.edu:8001/v1")
LOCAL_API_KEY = os.getenv("LOCAL_API_KEY", "EMPTY")

DEFAULT_SEED = 42
DEFAULT_MAX_TURNS = 200
DEFAULT_NUM_SEGMENTS = 5
DEFAULT_STYLE_TYPES = ["plain", "credibility", "emotion", "anecdote"]