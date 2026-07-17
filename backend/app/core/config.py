import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "WattDash"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_DIR: Path = BASE_DIR / "app" / "database"
    DATABASE_URL: str = f"sqlite:///{DATABASE_DIR}/wattdash.db"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-jwt-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Chromium / DrissionPage settings
    CHROMIUM_PATH: str = os.getenv("CHROMIUM_PATH", "")  # Empty means auto-detect
    CHROMIUM_USER_DATA: str = os.getenv("CHROMIUM_USER_DATA", "/tmp/chromium_user_data")
    
    # Token storage
    TOKEN_FILE: Path = DATABASE_DIR / "token.txt"

    class Config:
        case_sensitive = True

settings = Settings()

# Ensure database directory exists
settings.DATABASE_DIR.mkdir(parents=True, exist_ok=True)
