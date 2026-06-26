from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application configuration settings.

    All values can be overridden via environment variables.
    This follows the 12-Factor App methodology.
    """

    # Application settings
    app_name: str = "CodeBot API"
    debug_mode: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # Security
    secret_key: str
    encryption_key: str  # For encrypting GitHub OAuth tokens (Fernet key)

    # Database settings
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "db"
    postgres_port: int = 5432
    database_url: str

    # Derived database settings
    @property
    def async_database_url(self) -> str:
        """Async database URL for SQLAlchemy"""
        return self.database_url

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance.

    Using lru_cache ensures we only create one Settings instance
    and reuse it across the application (singleton pattern).
    """
    return Settings()


# For backward compatibility and convenience
settings = get_settings()
