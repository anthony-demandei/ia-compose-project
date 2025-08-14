from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Core Environment
    environment: str = "development"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8001

    # Authentication - Demandei API Key (REQUIRED)
    demandei_api_key: str = "your_demandei_api_key_here"

    # AI Configuration - Google Gemini Only
    gemini_api_key: str = "AIzaSyBzEr9w7CZ4nwp4p-Szqfqc1YgOCqm8nos"
    gemini_model: str = "gemini-2.0-flash-exp"  # Options: gemini-2.5-flash, gemini-2.0-flash-exp, gemini-1.5-flash, gemini-1.5-pro

    # Document Generation Configuration
    doc_min_lines_per_stack: int = 500
    doc_max_generation_attempts: int = 3
    doc_generation_temperature: float = 0.8
    doc_generation_max_tokens: int = 8000

    # Question Engine Configuration
    question_max_per_selection: int = 15
    question_similarity_threshold: float = 0.7
    question_cache_ttl_seconds: int = 3600
    question_generation_temperature: float = 0.5
    question_generation_max_tokens: int = 2048

    # Storage Configuration
    use_local_storage: bool = True
    local_storage_path: str = "./storage"
    local_documents_path: str = "./storage/documents"
    local_sessions_path: str = "./storage/sessions"

    # Session Management
    max_session_duration: int = 3600  # 1 hour in seconds
    session_cleanup_interval: int = 300  # 5 minutes

    # API Configuration
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080", "http://localhost:8000"]
    max_request_size: int = 10485760  # 10MB
    request_timeout: int = 120  # 2 minutes

    # Logging Configuration
    log_level: str = "INFO"
    enable_pii_safe_logging: bool = True
    log_file_path: str = "./logs/app.log"
    log_rotation_size: str = "10MB"
    log_retention_days: int = 30

    # Performance Configuration
    enable_response_compression: bool = True
    enable_request_validation: bool = True
    max_concurrent_requests: int = 100

    # Cloud Storage Configuration (Optional - for production)
    gcs_bucket_name: str = ""
    gcs_credentials_path: str = ""
    firestore_project_id: str = ""

    model_config = {"env_file": ".env", "case_sensitive": False, "extra": "ignore"}


# Global settings instance
_settings = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
