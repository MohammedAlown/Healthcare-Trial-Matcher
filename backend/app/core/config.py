"""
config.py - Application Settings

Uses pydantic-settings to load configuration from .env file.
Every setting has a default value so the app can start even
without a .env file.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables / .env file.

    Attributes:
        APP_NAME: Display name of the application
        APP_VERSION: Current version string
        DEBUG: Enable debug mode (extra logging, auto-reload)
        HOST: Server bind address (0.0.0.0 = all interfaces)
        PORT: Server port number
        OPENAI_API_KEY: API key for OpenAI (used in RAG milestone)
        DATABASE_URL: PostgreSQL connection string
        QDRANT_HOST: Qdrant vector DB hostname
        QDRANT_PORT: Qdrant vector DB port
    """

    APP_NAME: str = "Healthcare Clinical Trial Matcher"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    OPENAI_API_KEY: str = ""
    DATABASE_URL: str = ""
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Single global instance — import this everywhere
settings = Settings()
