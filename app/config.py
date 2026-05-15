import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    app_env: str = os.getenv("APP_ENV", "development")
    app_secret_key: str = os.getenv("APP_SECRET_KEY", "dev-only-change-me")
    document_crypto_key: str = os.getenv("DOCUMENT_CRYPTO_KEY", "")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./securedocs.db")
    private_storage_dir: str = os.getenv("PRIVATE_STORAGE_DIR", "private_storage")
    session_cookie_name: str = os.getenv("SESSION_COOKIE_NAME", "securedocs_session")
    session_cookie_secure: bool = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    session_max_age_seconds: int = int(os.getenv("SESSION_MAX_AGE_SECONDS", "3600"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
