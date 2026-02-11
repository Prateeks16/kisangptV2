from pydantic_settings import BaseSettings

class Settings(BaseSettings):

    PROJECT_NAME: str = "KisanGPT Enterprise"
    API_V1_STR: str = "/api/v1"
    
    
    GEMINI_API_KEY: str
    QDRANT_URL: str
    QDRANT_API_KEY: str
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./kisan_database.db"

    class Config:
        env_file = ".env"

settings = Settings()