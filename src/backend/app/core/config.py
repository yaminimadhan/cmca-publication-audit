# src/backend/app/core/config.py
import os
from dotenv import load_dotenv

# Load .env from the project root (the folder you run uvicorn from)
load_dotenv()

class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "CMCA Audit API")

    # You already created the DB/table in Postgres
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:March%402025@localhost:5432/cmca_audit"
    )

    # Auth/JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "CHANGE_ME_IN_PROD")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")

settings = Settings()
