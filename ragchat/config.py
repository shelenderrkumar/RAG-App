from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: SecretStr = SecretStr("")
    chat_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    documents_dir: Path = DATA_DIR
    index_dir: Path = DATA_DIR / "index"
    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 4

    company_name: str = "Lumora Analytics"
    company_profile_pdf: Path = DATA_DIR / "company_profile.pdf"

    # Leave SMTP_HOST unset to log e-mails to the console instead of sending them.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    email_sender: str = "no-reply@example.com"

    port: int = 8000

    @field_validator("smtp_host", "smtp_username", "smtp_password", mode="before")
    @classmethod
    def _blank_is_unset(cls, value):
        return None if isinstance(value, str) and not value.strip() else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
