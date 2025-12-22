# app/core/config.py

from pydantic_settings import BaseSettings
from pathlib import Path
from functools import lru_cache


class Settings(BaseSettings):
    # --- PROJECT ---
    PROJECT_NAME: str = "Customs Calculator API"

    # --- POSTGRES ---
    POSTGRES_USER: str
    POSTGRES_PASS: str
    POSTGRES_PORT: int
    POSTGRES_NAME: str
    POSTGRES_HOST: str

    # --- DATABASE ---
    DATABASE_URL: str | None = None

    # --- PATHS ---
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    MEDIA_DIR: Path = BASE_DIR / "media"
    DUTIES_DIR: Path = MEDIA_DIR / "duties"
    EXCISE_DIR: Path = MEDIA_DIR / "excise"
    TNVED_DIR: Path = MEDIA_DIR / "tnved"

    class Config:
        env_file = ".env"
        case_sensitive = True

    def model_post_init(self, __context):
        self.DATABASE_URL = (
            f"postgresql://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASS}@"
            f"{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/"
            f"{self.POSTGRES_NAME}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
