"""App settings read from environment variables (.env supported)."""
import os

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tasks.db")
TOKEN_HOURS = int(os.getenv("TOKEN_HOURS", "24"))
