"""
Application configuration using Pydantic Settings
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    secret_key: str = "change-me-to-random-string-min-32-chars"
    debug: bool = False
    app_name: str = "jspow"
    app_version: str = "1.0.0"

    # Server
    host: str = "0.0.0.0"
    port: int = 8002

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/jspow"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Ollama (LLaVA)
    ollama_host: str = "http://192.168.50.248:11434"
    ollama_model: str = "llava"
    ollama_timeout: int = 120

    # Nextcloud
    nextcloud_url: str = "https://nextcloud.lan"
    nextcloud_username: str = "admin"
    nextcloud_password: str = "change-me"
    nextcloud_base_path: str = "/jspow"

    # Cloudflare
    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""

    # Cloudflare R2
    cloudflare_r2_account_id: str = ""
    cloudflare_r2_access_key_id: str = ""
    cloudflare_r2_secret_access_key: str = ""
    cloudflare_r2_bucket: str = "jspow-images"
    cloudflare_r2_endpoint: str = ""
    cloudflare_r2_originals_path: str = "originals/"
    cloudflare_r2_working_path: str = "working/"
    cloudflare_r2_exports_path: str = "exports/"
    cloudflare_r2_metadata_path: str = "metadata/"

    # Cloudflare Stream
    cloudflare_stream_account_id: str = ""
    cloudflare_stream_api_token: str = ""

    # Feature Flags
    feature_flags: List[str] = Field(default_factory=list)
    enable_cloudflare_r2: bool = False
    enable_cloudflare_stream: bool = False
    enable_manifest_generation: bool = False

    # Storage
    storage_root: str = "/app/storage"
    storage_originals_dirname: str = "originals"
    storage_working_dirname: str = "working"
    storage_exports_dirname: str = "exports"
    storage_metadata_dirname: str = "metadata"
    default_project_code: str = "general"
    upload_dir: str = "/app/storage/working"
    max_upload_size_mb: int = 100
    allowed_image_extensions: str = "jpg,jpeg,png,gif,webp,bmp,tiff"
    allowed_video_extensions: str = "mp4,mov,avi,mkv,webm"

    # Processing
    max_batch_size: int = 50
    process_timeout_seconds: int = 300

    @property
    def allowed_image_exts(self) -> List[str]:
        """Get allowed image extensions as list"""
        return [ext.strip().lower() for ext in self.allowed_image_extensions.split(",")]

    @property
    def allowed_video_exts(self) -> List[str]:
        """Get allowed video extensions as list"""
        return [ext.strip().lower() for ext in self.allowed_video_extensions.split(",")]


# Global settings instance
settings = Settings()
