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
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Setu")
    API_V1_STR: str = os.getenv("API_V1_STR", "/api/v1")
    SECRET_KEY: str = os.getenv("SETU_SECRET_KEY", "setu-secret-key-production-safety-2026")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # 7 days for farmers
    
    # Database configuration (PostgreSQL only in the current backend)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://setu_user:setu_password@127.0.0.1:5432/setu"
    )

    # Security & Access Control
    INITIAL_ADMIN_PASSWORD: str = os.getenv("INITIAL_ADMIN_PASSWORD", "admin")
    DEVICE_API_KEY: str = os.getenv("DEVICE_API_KEY", "setu-iot-device-key-2026")
    ALLOWED_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000,http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ]
    FIREBASE_CREDENTIALS_PATH: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
    FIREBASE_SERVICE_ACCOUNT_JSON: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")

    # Twilio / WhatsApp notifications
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID") or os.getenv("TWILIO_ACCOUNT_SSID", "")
    TWILIO_ACCOUNT_SSID: str = os.getenv("TWILIO_ACCOUNT_SSID") or os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_FROM: str = os.getenv("TWILIO_WHATSAPP_FROM", "")
    TWILIO_WHATSAPP_TO: str = os.getenv("TWILIO_WHATSAPP_TO", "")

    # Regional defaults (Global Worldwide Dynamic Geocoding)
    DEFAULT_REGION: str = os.getenv("DEFAULT_REGION", "Global Sericulture Network")
    DEFAULT_LATITUDE: float = float(os.getenv("DEFAULT_LATITUDE", "0.0"))
    DEFAULT_LONGITUDE: float = float(os.getenv("DEFAULT_LONGITUDE", "0.0"))

settings = Settings()

