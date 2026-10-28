from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "creator-api"
    app_env: str = "local"
    log_level: str = "INFO"
    database_url: str = "sqlite+pysqlite:///./.local/db/creator.db"
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_backend: Literal["redis", "memory"] = "redis"
    rate_limit_redis_url: str | None = None
    rate_limit_limit: int = 5
    rate_limit_window_seconds: float = 1.0
    rate_limit_key_prefix: str = "creator:rate-limit:v1"
    auth_required: bool = False
    auth_jwt_secret: str | None = Field(default=None, repr=False)
    auth_jwt_issuer: str = "creator"
    auth_jwt_audience: str = "creator-api"
    auth_access_token_ttl_seconds: int = 900
    auth_refresh_token_ttl_days: int = 30
    auth_password_min_length: int = 12
    auth_login_max_attempts: int = 5
    auth_login_lockout_seconds: int = 900
    auth_cookie_sessions_enabled: bool = True
    auth_legacy_bearer_enabled: bool = True
    auth_token_body_enabled: bool = True
    auth_cookie_access_name: str = "creator_access"
    auth_cookie_refresh_name: str = "creator_refresh"
    auth_cookie_csrf_name: str = "creator_csrf"
    auth_cookie_access_path: str = "/api/v1"
    auth_cookie_refresh_path: str = "/api/v1/auth"
    auth_cookie_csrf_path: str = "/"
    auth_cookie_same_site: Literal["strict", "lax", "none"] = "strict"
    auth_cookie_secure: bool | None = None
    auth_csrf_header_name: str = "X-CSRF-Token"
    auth_csrf_ttl_seconds: int = 900
    auth_refresh_rotation_grace_seconds: int = 30
    auth_session_absolute_ttl_days: int = 90
    auth_session_retention_days: int = 30
    auth_cors_origins: list[str] = Field(default_factory=list)
    supabase_url: str | None = None
    supabase_service_role_key: str | None = Field(default=None, repr=False)
    supabase_auth_timeout_seconds: float = 5.0
    gemini_api_key: str | None = Field(default=None, repr=False)
    gemini_text_model: str = "gemini-2.5-flash"
    gemini_image_model: str = "gemini-2.5-flash-image"
    gemini_timeout_seconds: float = 30.0
    gemini_retry_attempts: int = 3
    gemini_retry_initial_delay_seconds: float = 1.0
    gemini_retry_max_delay_seconds: float = 8.0
    crewai_enabled: bool = False
    langchain_enabled: bool = False
    gemini_embedding_model: str = "models/gemini-embedding-001"
    rag_vector_store_provider: str = "chroma"
    rag_vector_store_path: str = ".local/rag/chroma"
    rag_collection_name: str = "creator-content"
    rag_top_k: int = 5
    generation_queue_name: str = "creator:rq:generations"
    image_generation_job_timeout_seconds: int = 300
    image_generation_job_max_attempts: int = 3
    image_generation_retry_interval_seconds: list[int] = [60, 120, 240]
    image_generation_stale_processing_seconds: int = 900
    agent_workflow_max_refinements: int = Field(default=3, ge=0, le=10)
    agent_workflow_job_timeout_seconds: int = 900
    pipeline_event_max_attempts: int = 5
    pipeline_event_retry_interval_seconds: list[int] = [30, 60, 120, 300]
    pipeline_event_lease_grace_seconds: int = 60
    agent_reviewer_model: str = "gemini-2.5-flash"
    storage_provider: str = "local"
    storage_bucket: str = "creator-images"
    storage_max_object_bytes: int = 10 * 1024 * 1024
    storage_signed_url_expires_seconds: int = 3600
    local_storage_root: str = ".local/storage"

    @model_validator(mode="after")
    def validate_auth_transport(self) -> "Settings":
        if self.auth_cookie_secure is None:
            self.auth_cookie_secure = self.app_env not in {"local", "test", "development"}
        if self.auth_cookie_same_site == "none" and not self.auth_cookie_secure:
            raise ValueError("AUTH_COOKIE_SAME_SITE=none requires AUTH_COOKIE_SECURE=true")
        if "*" in self.auth_cors_origins:
            raise ValueError("AUTH_CORS_ORIGINS cannot contain '*' with credentialed cookies")
        if self.app_env in {"production", "staging"}:
            if self.rate_limit_backend == "memory":
                raise ValueError(
                    "The in-memory rate limiter is not allowed outside local environments"
                )
            if not self.auth_cookie_secure:
                raise ValueError("AUTH_COOKIE_SECURE must be true outside local development")
            if not self.auth_jwt_secret or len(self.auth_jwt_secret) < 32:
                raise ValueError("AUTH_JWT_SECRET must contain at least 32 characters")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
