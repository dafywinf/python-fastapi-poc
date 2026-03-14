"""Application configuration loaded from environment / .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings resolved from environment variables or a .env file.

    Attributes:
        database_url: PostgreSQL connection string.
        loki_url: Base URL of the Loki push API. None disables log shipping.
    """

    database_url: str
    loki_url: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()  # pyright: ignore[reportCallIssue]
