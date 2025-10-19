from pydantic import BaseSettings

class Settings(BaseSettings):
    POSTGRES_USER: str = "codebot"
    POSTGRES_PASSWORD: str = "codebotpassword801"
    POSTGRES_DB: str = "codebot_dev"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    SECRET_KEY: str = "change-later"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    
settings = Settings()
