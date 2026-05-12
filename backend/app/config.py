from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，从 .env 文件和环境变量读取。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用
    app_env: str = "development"
    log_level: str = "INFO"
    backend_port: int = 8000

    # 数据库
    database_url: str = (
        "postgresql+asyncpg://deepscribe:deepscribe_secret@localhost:5432/deepscribe"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8001

    # AI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    # JWT
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # 加密
    encryption_key: str = "dev-encryption-key-32bytes!!!"

    # 搜索
    tavily_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
