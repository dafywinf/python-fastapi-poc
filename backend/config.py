"""Application configuration loaded from environment / .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings resolved from environment variables or a .env file.

    Attributes:
        database_url: PostgreSQL connection string.
        loki_url: Base URL of the Loki push API. None disables log shipping.
        jwt_secret_key: Secret used to sign and verify JWT tokens.
        jwt_algorithm: Algorithm used for JWT encoding (default HS256).
        access_token_expire_minutes: Lifetime of issued access tokens in minutes.
        admin_username: Username for the built-in admin account.
        admin_password_hash: bcrypt hash of the admin account password.
    """

    database_url: str
    loki_url: str | None = None
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    admin_username: str = "admin"
    admin_password_hash: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()  # pyright: ignore[reportCallIssue]
