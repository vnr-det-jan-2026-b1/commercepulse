"""Application configuration loaded from environment / Secret Manager."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    # GCP
    GCP_PROJECT: str = "commercepulse-project"
    GCP_REGION:  str = "asia-south1"

    # BigQuery datasets
    BQ_DATASET_RAW:    str = "cp_raw"
    BQ_DATASET_BRONZE: str = "cp_bronze"
    BQ_DATASET_SILVER: str = "cp_silver"
    BQ_DATASET_GOLD:   str = "cp_gold"
    BQ_DATASET_ML:     str = "cp_ml"

    # Cloud Run / API
    API_VERSION:    str = "v1"
    ALLOWED_ORIGINS: list = ["*"]

    # Redis (Memorystore)
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_TTL_SECONDS: int = 3600

    # Gemini
    GEMINI_API_KEY:      str = ""           # AI Studio key — takes priority over Vertex AI
    VERTEX_LOCATION:     str = "us-central1"
    GEMINI_MODEL:        str = "gemini-1.5-flash"

    # Pub/Sub
    PUBSUB_EVENTS_TOPIC: str = "commercepulse-events"

    # GCS
    GCS_UPLOAD_BUCKET:   str = "commercepulse-raw-uploads-prod"



settings = Settings()
