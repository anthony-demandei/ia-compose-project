from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Environment
    environment: str = "development"

    # AI Configuration
    # Provider selection
    ai_provider: str = "gemini"  # Options: "openai", "gemini"
    
    # OpenAI Configuration
    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"  # Options: gpt-4, gpt-4o, gpt-4o-mini, gpt-3.5-turbo
    ai_model: str = "gpt-3.5-turbo"  # Deprecated, use openai_model
    
    # Gemini Configuration
    gemini_api_key: str = "AIzaSyBzEr9w7CZ4nwp4p-Szqfqc1YgOCqm8nos"  # Default key provided
    gemini_model: str = "gemini-2.0-flash-exp"  # Options: gemini-2.0-flash-exp, gemini-1.5-pro, gemini-1.5-flash

    # GCS Configuration (optional for local development)
    gcs_bucket_name: str = "test-bucket"
    gcs_credentials_path: str = "./gcp-credentials.json"

    # Firestore Configuration (optional for local development)
    firestore_project_id: str = "test-project"

    # Local Storage Configuration
    use_local_storage: bool = True
    local_storage_path: str = "./storage"
    local_documents_path: str = "./storage/documents"
    local_sessions_path: str = "./storage/sessions"

    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    redis_password: str = ""
    use_redis_cache: bool = False  # Default to False for local dev

    # API Configuration
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    max_session_duration: int = 3600  # 1 hour

    # JWT Configuration
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"

    # Logging
    log_level: str = "INFO"

    # Multi-Agent Configuration
    enable_multi_agent: bool = False
    agent_coordination_mode: str = "collaborative"
    consensus_threshold: float = 0.7
    confidence_threshold: float = 0.6

    # Embedding Configuration
    embedding_model: str = "text-embedding-3-small"
    classification_model: str = "gpt-3.5-turbo"  # For classification tasks

    # ZEP Memory Configuration
    zep_api_url: str = "https://api.getzep.com"
    zep_project_key: str = "z_1dWlkIjoiODcwZTQ0M2UtNDgyYi00MTllLTg2OGYtNDNiYTI3N2ExYWUyIn0.aVB7DnD8hmzrQZsPKY_Egv4H5ZxhOL9cDZnBjR0KiC9NBxCqzB1wV7Nt_WV08ZJ2YHEVOLUZKMNnCMgN_E6Ikw"
    zep_account_id: str = "f6c33da2-03f8-4589-9fe7-2b3cc7a570f7"
    enable_zep_memory: bool = True

    # Universal User Configuration
    zep_universal_user_id: str = "demandei_universal_user"
    zep_universal_user_email: str = "system@demandei.com"
    zep_universal_user_name: str = "Demandei System"

    # Question Selection Configuration
    max_questions_per_selection: int = 15
    similarity_threshold: float = 0.7
    enable_context_inference: bool = True
    enable_smart_filtering: bool = True

    model_config = {"env_file": ".env", "case_sensitive": False, "extra": "ignore"}


# Global settings instance
_settings = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
