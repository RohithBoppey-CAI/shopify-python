# core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    Manages application settings and environment variables using Pydantic.
    """

    # Load variables from a .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Shopify App Credentials (from .env or injected by CLI)
    SHOPIFY_APP_KEY: str = Field(..., alias="SHOPIFY_APP_KEY")
    SHOPIFY_APP_SECRET: str = Field(..., alias="SHOPIFY_APP_SECRET")
    SHOPIFY_APP_SCOPES: str = "read_products,read_orders"

    APP_URL: str = Field(..., alias="SHOPIFY_APP_URL")

    # Database URL for storing tokens and sync status
    DATABASE_URL: str = "sqlite:///./shopify_app.db"


settings = Settings()
