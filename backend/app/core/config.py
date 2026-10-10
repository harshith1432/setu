from pydantic import BaseModel
import os
from pathlib import Path

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    # Search in current directory, backend directory, and parent directory
    base_dir = Path(__file__).resolve().parent.parent.parent
    env_file = base_dir / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)
    else:
        root_env = base_dir.parent / ".env"
        if root_env.exists():
            load_dotenv(dotenv_path=root_env)
        else:
            load_dotenv()
except ImportError:
    pass

class Settings(BaseModel):
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Setu IoT Backend")
    API_V1_STR: str = os.getenv("API_V1_STR", "/api/v1")
    SECRET_KEY: str = os.getenv("SETU_SECRET_KEY", "setu-secret-key-production-safety-2026")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # 7 days for farmers
    
    # Database configuration (PostgreSQL)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@127.0.0.1:5432/setu"
    )

    # Regional defaults (Global Worldwide Dynamic Geocoding)
    DEFAULT_REGION: str = os.getenv("DEFAULT_REGION", "Global Sericulture Network")
    DEFAULT_LATITUDE: float = float(os.getenv("DEFAULT_LATITUDE", "0.0"))
    DEFAULT_LONGITUDE: float = float(os.getenv("DEFAULT_LONGITUDE", "0.0"))

settings = Settings()

