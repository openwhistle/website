"""A stand-in for the app's config.py: tests/test_release_source.py parses it."""

from pydantic_settings import BaseSettings, SettingsConfigDict

_MIN_SECRET_KEY_LEN = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    secret_key: str
    demo_mode: bool = False
    app_version: str = "9.9.9"
