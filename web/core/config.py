# core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Manages application settings and environment variables using Pydantic.
    """
    # Load variables from a .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Shopify App Credentials
    SHOPIFY_APP_KEY: str
    SHOPIFY_APP_SECRET: str
    SHOPIFY_APP_SCOPES: str = "read_products,read_orders"

    # Application URL (Use ngrok for local development)
    APP_URL: str

    # Database URL for storing tokens and sync status
    DATABASE_URL: str = "sqlite:///./shopify_app.db"

settings = Settings()
 