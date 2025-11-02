from pathlib import Path

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
