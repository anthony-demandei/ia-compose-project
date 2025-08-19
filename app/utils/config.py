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
    
    # Primary and Fallback Model Configuration
    gemini_primary_model: str = "gemini-1.5-pro"  # Main model for generation
    gemini_fallback_model: str = "gemini-1.5-flash"  # Fallback when primary fails
    gemini_last_resort_model: str = "gemini-2.0-flash-exp"  # Last resort option
    
    # Legacy model field for backward compatibility
    gemini_model: str = "gemini-1.5-pro"  # Deprecated, use primary_model instead

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
    # CORS is now hardcoded in main.py based on environment
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

    # Redis Cache Configuration
    enable_redis_cache: bool = True
    redis_url: str = ""  # Full Redis URL (optional, overrides other Redis settings)
    redis_host: str = "localhost"  # Use "redis" in Docker
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_username: str = ""  # For Redis 6.0+ ACL
    redis_ssl: bool = False
    redis_ssl_cert_reqs: str = "required"  # none, optional, required
    redis_ssl_ca_certs: str = ""
    redis_ssl_certfile: str = ""
    redis_ssl_keyfile: str = ""
    
    # Redis Connection Pool Settings
    redis_max_connections: int = 10
    redis_retry_on_timeout: bool = True
    redis_health_check_interval: int = 30
    redis_connection_timeout: int = 5  # seconds
    redis_socket_timeout: int = 5  # seconds
    
    # Redis Cache TTL Settings
    redis_ttl_questions: int = 3600  # 1 hour for questions
    redis_ttl_documents: int = 86400  # 24 hours for documents
    redis_ttl_sessions: int = 7200  # 2 hours for sessions
    
    # Redis Fallback Configuration
    redis_enable_fallback: bool = True  # Use in-memory cache when Redis fails
    redis_fallback_timeout: int = 2  # Seconds before falling back

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
