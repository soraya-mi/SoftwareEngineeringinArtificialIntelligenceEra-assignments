from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CHANGEFLOW_",
        env_file=".env",
        extra="ignore",
    )

    environment: str = "development"
    database_url: str = "sqlite:///changeflow.dev.db"
    jwt_issuer: str = Field(min_length=1)
    jwt_audience: str = Field(min_length=1)
    jwt_jwks_url: str = Field(min_length=1)
    jwt_algorithm: str = "RS256"


@lru_cache
def get_settings() -> Settings:
    return Settings()
