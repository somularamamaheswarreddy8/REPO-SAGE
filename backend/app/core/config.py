import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "RepoSage"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://reposage:reposage@localhost:5432/reposage",
        description="Async database connection string"
    )
    SYNC_DATABASE_URL: Optional[str] = Field(
        default="postgresql://reposage:reposage@localhost:5432/reposage",
        description="Sync database connection string for migrations"
    )

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_TASK_ALWAYS_EAGER: bool = False

    # AI Configuration
    DEFAULT_LLM_PROVIDER: str = "mock"  # "mock", "openai", "anthropic", "gemini"
    DEFAULT_EMBEDDING_PROVIDER: str = "mock"  # "mock", "openai", "gemini", "local"
    EMBEDDING_DIMENSION: int = 1536

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-pro"

    # GitHub App & Personal Token Configuration
    GITHUB_APP_ID: Optional[str] = None
    GITHUB_PRIVATE_KEY: Optional[str] = None
    GITHUB_WEBHOOK_SECRET: Optional[str] = None
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    GITHUB_TOKEN: Optional[str] = None  # Optional Personal Access Token for higher rate limits on public repos
    MOCK_GITHUB_ENABLED: bool = True  # Enable mock GitHub for zero-credential demos

    # Safety & Limits
    MAX_FILE_SIZE_BYTES: int = 500 * 1024  # 500 KB
    MAX_REPO_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    MAX_INDEX_FILES: int = 1000

    EXCLUDED_DIRS: List[str] = [
        ".git", "node_modules", "venv", ".venv", "__pycache__",
        "dist", "build", ".next", ".cache", ".idea", ".vscode",
        ".gemini", ".system_generated", "coverage", ".pytest_cache"
    ]
    EXCLUDED_EXTENSIONS: List[str] = [
        ".pyc", ".pyd", ".so", ".dylib", ".exe", ".dll", ".bin",
        ".iso", ".zip", ".tar", ".gz", ".png", ".jpg", ".jpeg",
        ".gif", ".ico", ".pdf", ".mp4", ".mov", ".woff", ".woff2",
        ".ttf", ".eot", ".svg", ".lock", ".db", ".sqlite", ".sqlite3"
    ]
    SENSITIVE_PATTERNS: List[str] = [
        ".env", ".env.*", "*.pem", "*.key", "id_rsa*", "id_ed25519*",
        "credentials*", "secrets*", "*token*", "*secret*"
    ]

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"]

    # Observability
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "reposage-backend"
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = None


settings = Settings()
