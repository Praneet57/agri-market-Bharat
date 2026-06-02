from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "AgriMarketplace"
    SECRET_KEY: str = "changeme-secret-key-32-chars-min"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DEBUG: bool = True
    DATABASE_URL: str = "postgresql+asyncpg://agriuser:agripass@localhost:5432/agridb"
    SYNC_DATABASE_URL: str = "postgresql://agriuser:agripass@localhost:5432/agridb"
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    RAZORPAY_KEY_ID: str = "rzp_test_demo"
    RAZORPAY_KEY_SECRET: str = "demo_secret"
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET_NAME: str = "agri-marketplace"
    S3_PUBLIC_URL: str = ""
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "noreply@agrimarket.com"
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    ALLOWED_ORIGINS: str = "http://localhost,http://localhost:8000,http://127.0.0.1:8000"

    @property
    def origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
