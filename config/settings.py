"""Application settings configuration using pydantic-settings."""
# pylint: disable=too-few-public-methods
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings - loaded from environment variables."""

    # App Settings
    APP_NAME: str = "Ads Manager"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # API Security
    API_KEY: str = "change-me-in-production"  # WICHTIG: In .env setzen!
    ALLOWED_IPS: str = ""  # Kommagetrennte Liste erlaubter IPs (leer = alle erlaubt)

    # Database
    DATABASE_URL: str = "sqlite:///./ads_manager.db"

    # Google Ads (später aktivieren)
    GOOGLE_ADS_DEVELOPER_TOKEN: Optional[str] = None
    GOOGLE_ADS_CLIENT_ID: Optional[str] = None
    GOOGLE_ADS_CLIENT_SECRET: Optional[str] = None
    GOOGLE_ADS_REFRESH_TOKEN: Optional[str] = None
    GOOGLE_ADS_LOGIN_CUSTOMER_ID: Optional[str] = None
    GOOGLE_ADS_CUSTOMER_ID: Optional[str] = None

    # Meta Ads
    META_APP_ID: Optional[str] = None
    META_APP_SECRET: Optional[str] = None
    META_ACCESS_TOKEN: Optional[str] = None
    # Mehrere Meta Accounts (JSON-String: {"name": {"app_id": "...", "token": "..."}})
    META_ACCOUNTS: Optional[str] = None

    class Config:
        """Pydantic model configuration."""

        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
