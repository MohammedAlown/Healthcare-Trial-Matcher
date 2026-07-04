from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Healthcare Clinical Trial Matcher"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    OPENAI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    DATABASE_URL: str = ""
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
