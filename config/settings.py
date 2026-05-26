"""
Recepta - Central Configuration
All settings are loaded from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# ─── Project Paths ───────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = DATA_DIR / "logs"
DB_DIR = DATA_DIR / "chroma_db"
VOICES_DIR = DATA_DIR / "voices"
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(VOICES_DIR, exist_ok=True)
os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

# ─── App Mode ────────────────────────────────────────────────────────────────
DEBUG = os.getenv("RECEPTA_DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("RECEPTA_LOG_LEVEL", "INFO")
MULTI_TENANT = os.getenv("RECEPTA_MULTI_TENANT", "false").lower() == "true"

# ─── STT - Speaches (local faster-whisper) ───────────────────────────────────
SPEACHES_BASE_URL = os.getenv("SPEACHES_BASE_URL", "http://localhost:8000")
SPEACHES_API_KEY = os.getenv("SPEACHES_API_KEY", "recepta-local")
SPEACHES_MODEL = os.getenv("SPEACHES_MODEL", "whisper-1")
SPEACHES_USE_WEBSOCKET = os.getenv("SPEACHES_USE_WEBSOCKET", "true").lower() == "true"

# ─── LLM - Ollama (local) ────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
OLLAMA_STREAM = os.getenv("OLLAMA_STREAM", "true").lower() == "true"
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "30"))
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
OLLAMA_MAX_TOKENS = int(os.getenv("OLLAMA_MAX_TOKENS", "512"))
OLLAMA_CONTEXT_LENGTH = int(os.getenv("OLLAMA_CONTEXT_LENGTH", "4096"))

# ─── TTS - Kokoro ────────────────────────────────────────────────────────────
KOKORO_MODEL_PATH = os.getenv("KOKORO_MODEL_PATH", "")
KOKORO_VOICE = os.getenv("KOKORO_VOICE", "af_bella")  # Default: American female
KOKORO_DEVICE = os.getenv("KOKORO_DEVICE", "cpu")
KOKORO_SPEED = float(os.getenv("KOKORO_SPEED", "1.0"))

# ─── LiveKit ─────────────────────────────────────────────────────────────────
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "wss://your-project.livekit.cloud")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
LIVEKIT_ROOM_NAME = os.getenv("LIVEKIT_ROOM_NAME", "recepta-room")
LIVEKIT_IDENTITY = os.getenv("LIVEKIT_IDENTITY", "recepta-agent")

# ─── Google Calendar ─────────────────────────────────────────────────────────
GOOGLE_CALENDAR_CREDENTIALS_FILE = os.getenv(
    "GOOGLE_CALENDAR_CREDENTIALS_FILE",
    str(PROJECT_ROOT / "config" / "google_credentials.json")
)
GOOGLE_CALENDAR_TOKEN_FILE = os.getenv(
    "GOOGLE_CALENDAR_TOKEN_FILE",
    str(PROJECT_ROOT / "config" / "google_token.json")
)
GOOGLE_CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]

# ─── ChromaDB ────────────────────────────────────────────────────────────────
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(DB_DIR))
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "recepta_knowledge")
CHROMA_EMBEDDING_FN = os.getenv("CHROMA_EMBEDDING_FN", "ollama")

# ─── n8n (optional automation) ──────────────────────────────────────────────
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")
N8N_ENABLED = os.getenv("N8N_ENABLED", "false").lower() == "true"

# ─── Phone / SIP (future) ───────────────────────────────────────────────────
PHONE_PROVIDER = os.getenv("PHONE_PROVIDER", "")  # twilio, telnyx, etc.
PHONE_ACCOUNT_SID = os.getenv("PHONE_ACCOUNT_SID", "")
PHONE_AUTH_TOKEN = os.getenv("PHONE_AUTH_TOKEN", "")
PHONE_FROM_NUMBER = os.getenv("PHONE_FROM_NUMBER", "")

# ─── Audio Settings ──────────────────────────────────────────────────────────
SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
CHANNELS = int(os.getenv("AUDIO_CHANNELS", "1"))
FRAME_DURATION_MS = int(os.getenv("AUDIO_FRAME_DURATION_MS", "20"))
VAD_THRESHOLD = float(os.getenv("VAD_THRESHOLD", "0.5"))
VAD_FRAME_DURATION_MS = int(os.getenv("VAD_FRAME_DURATION_MS", "30"))
SILENCE_TIMEOUT_SECONDS = float(os.getenv("SILENCE_TIMEOUT_SECONDS", "1.5"))

# ─── Response Settings ──────────────────────────────────────────────────────
MAX_RESPONSE_TIME_SECONDS = int(os.getenv("MAX_RESPONSE_TIME_SECONDS", "30"))
INTERRUPTIBLE = os.getenv("INTERRUPTIBLE", "true").lower() == "true"
ENABLE_BAIL_WORDS = os.getenv("ENABLE_BAIL_WORDS", "true").lower() == "true"
BAIL_WORDS = ["goodbye", "bye", "thanks", "thank you", "that's all", "that is all", "no thanks"]

# ─── Analytics ───────────────────────────────────────────────────────────────
ANALYTICS_ENABLED = os.getenv("ANALYTICS_ENABLED", "true").lower() == "true"
ANALYTICS_DB_PATH = os.getenv("ANALYTICS_DB_PATH", str(DATA_DIR / "analytics.db"))
