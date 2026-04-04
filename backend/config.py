from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Anthropic
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"

    # Database (PostgreSQL via Supabase or local)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/docflow"

    # Redis + Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # AWS S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "docflow-ai"
    s3_presigned_url_expiry: int = 3600  # seconds

    # Clerk Auth
    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""
    clerk_webhook_secret: str = ""

    # Email (AWS SES)
    ses_from_email: str = ""  # Must be a verified identity in AWS SES console

    # HubSpot
    hubspot_default_portal_url: str = "https://api.hubapi.com"

    # App
    app_env: str = "development"
    allowed_origins: str = "http://localhost:3000"
    max_upload_bytes: int = 50 * 1024 * 1024  # 50 MB
    s3_file_retention_days: int = 90
    hours_saved_per_doc_baseline: float = 2.0  # conservative vs 3–4 hr manual baseline

    # OCR
    tesseract_cmd: str = ""  # e.g. C:/Program Files/Tesseract-OCR/tesseract.exe
    ocr_text_density_threshold: int = 100  # chars/page below which we use OCR fallback

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
