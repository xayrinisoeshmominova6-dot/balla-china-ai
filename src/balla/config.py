"""Sozlamalar.

Barcha sozlamalar va maxfiy kalitlar `.env` faylidan (yoki muhit
o'zgaruvchilaridan) o'qiladi. Kalitlar hech qachon kodga yozilmaydi.

Kalitlar `SecretStr` turida saqlanadi: agar kimdir sozlamalarni
ekranga yoki logga chiqarsa, kalit o'rniga `**********` ko'rinadi.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Claude ---
    anthropic_api_key: SecretStr | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    claude_model: str = Field(default="claude-opus-5-5", alias="BALLA_CLAUDE_MODEL")
    claude_effort: str = Field(default="high", alias="BALLA_CLAUDE_EFFORT")

    # --- Instagram (ixtiyoriy) ---
    instagram_access_token: SecretStr | None = Field(default=None, alias="INSTAGRAM_ACCESS_TOKEN")
    instagram_business_account_id: str | None = Field(
        default=None, alias="INSTAGRAM_BUSINESS_ACCOUNT_ID"
    )
    # graph.instagram.com — "Instagram Login" orqali olingan token uchun (tavsiya etiladi)
    # graph.facebook.com  — "Facebook Login" (Facebook sahifa orqali) olingan token uchun
    instagram_api_host: str = Field(default="graph.instagram.com", alias="INSTAGRAM_API_HOST")
    instagram_api_version: str = Field(default="v23.0", alias="INSTAGRAM_API_VERSION")

    # --- Saqlash ---
    database_path: Path = Field(default=Path("output/balla.db"), alias="BALLA_DATABASE_PATH")

    @property
    def has_claude_key(self) -> bool:
        return bool(self.anthropic_api_key and self.anthropic_api_key.get_secret_value())

    @property
    def instagram_configured(self) -> bool:
        return bool(
            self.instagram_access_token
            and self.instagram_access_token.get_secret_value()
            and self.instagram_business_account_id
        )

    @property
    def resolved_database_path(self) -> Path:
        p = self.database_path
        return p if p.is_absolute() else PROJECT_ROOT / p


@lru_cache
def get_settings() -> Settings:
    return Settings()
