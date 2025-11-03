from pathlib import Path

try:
    from config_local import OPENAI_API_KEY
except ImportError:
    OPENAI_API_KEY = "your-api-key-here"

class PathConfig:
    # ------------------------------
    # DIR setup
    # ------------------------------

    BASE_DIR = Path(__file__).resolve().parent
    UPLOAD_DIR = BASE_DIR / "uploads"
    TEMPLATES_DIR = BASE_DIR / "templates"

class AuthConfig:
    # ------------------------------
    # Auth Options
    # ------------------------------
    SECRET_KEY = "supersecretkey123"
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60

class RAGConfig:
    LLM_PROVIDER = "openai"
    OPENAI_API_KEY = OPENAI_API_KEY
    OPENAI_MODEL = "gpt-4.1-nano"
    OPENAI_TIMEOUT = 120
    RAG_TOP_K = 5
    RAG_ENABLE_SUMMARY = "true"
    RAG_CACHE_TTL = 3600