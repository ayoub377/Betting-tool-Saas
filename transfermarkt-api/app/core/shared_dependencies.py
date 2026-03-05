# shared_dependencies.py
import os
from typing import Optional
from fastapi import HTTPException
from dotenv import load_dotenv

# Load environment variables from .env file when this module is imported
# Try multiple possible locations for the .env file
import os
from pathlib import Path

# Get the project root directory (assuming this file is in app/core/)
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"

# Try to load from the project root first, then fallback to default behavior
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

# Global variable to store the API key, loaded from environment
THE_ODDS_API_KEY: Optional[str] = os.getenv("ODDS_API_KEY")

def get_configured_api_key() -> str:
    """
    FastAPI dependency to get the configured The Odds API key.
    Raises HTTPException if the API key is not configured.
    """
    if not THE_ODDS_API_KEY:
        raise HTTPException(
            status_code=503, # Service Unavailable
            detail={
                "type": "ConfigurationError",
                "message": "The server is not configured with The Odds API key. Please ensure the ODDS_API_KEY environment variable is set."
            }
        )
    return THE_ODDS_API_KEY
