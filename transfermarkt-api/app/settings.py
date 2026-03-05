from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Explicitly load the .env file
load_dotenv(".env")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env",extra="allow")
    RATE_LIMITING_ENABLE: bool = False
    RATE_LIMITING_FREQUENCY: str = "2/3seconds"
    
    # Rate limiting configuration
    DEFAULT_MAX_REQUESTS: int = 50  # Increased to 20 for development
    DEFAULT_RESET_DURATION: int = 86400  # 24 hours in seconds


settings = Settings()
