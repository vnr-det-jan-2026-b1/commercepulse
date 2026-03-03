"""Application settings via Pydantic BaseSettings."""
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # PostgreSQL
    POSTGRES_HOST:     str = "localhost"
    POSTGRES_PORT:     int = 5432
    POSTGRES_DB:       str = "commercepulse"
    POSTGRES_USER:     str = "commercepulse"
    POSTGRES_PASSWORD: str = "changeme"

    # Application
    APP_ENV:  str = "development"
    API_KEY:  str = "dev-api-key"

    # Redis (Celery broker/result backend)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Embedding model
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMS:  int = 384

    # AI Agents API (runs by default on 8001 locally to avoid clash)
    AI_AGENTS_URL: str = "http://localhost:8001"

    @property
    def _pw(self) -> str:
        """URL-encode the password so special chars (@ % : /) don't break the DSN."""
        return quote_plus(self.POSTGRES_PASSWORD)

    @property
    def async_db_url(self) -> str:
        base = (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self._pw}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
        # Supabase requires SSL; local docker does not
        if "supabase.co" in self.POSTGRES_HOST:
            base += "?ssl=require"
        return base

    @property
    def sync_db_url(self) -> str:
        base = (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self._pw}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
        if "supabase.co" in self.POSTGRES_HOST:
            base += "?sslmode=require"
        return base


settings = Settings()

