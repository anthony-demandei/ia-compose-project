"""
AI Provider Factory with intelligent model fallback.

Creates and manages Gemini AI providers with automatic failover
between primary, fallback, and last resort models for maximum reliability.
"""

import os
from typing import Dict, Optional
from enum import Enum

from app.services.ai_provider import AIProvider, AIProviderType
from app.services.gemini_provider import GeminiProvider
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


class AIProviderFactory:
    """Intelligent factory for AI provider creation with fallback support."""

    @staticmethod
    def create_provider(
        api_key: Optional[str] = None,
        primary_model: Optional[str] = None,
        fallback_model: Optional[str] = None,
        last_resort_model: Optional[str] = None,
    ) -> AIProvider:
        """
        Create Gemini AI provider with intelligent model fallback chain.

        Args:
            api_key: Gemini API key (uses env GEMINI_API_KEY if None)
            primary_model: Primary model (uses env GEMINI_PRIMARY_MODEL if None)
            fallback_model: Fallback model (uses env GEMINI_FALLBACK_MODEL if None) 
            last_resort_model: Last resort model (uses env GEMINI_LAST_RESORT_MODEL if None)

        Returns:
            Configured GeminiProvider with complete fallback chain
        """
        # Resolve API key from environment or use default
        resolved_api_key = AIProviderFactory._resolve_api_key(api_key)
        
        # Resolve model configuration from environment
        model_config = AIProviderFactory._resolve_model_config(
            primary_model, fallback_model, last_resort_model
        )
        
        # Log the resolved configuration
        AIProviderFactory._log_provider_config(model_config)
        
        return GeminiProvider(
            api_key=resolved_api_key,
            primary_model=model_config["primary"],
            fallback_model=model_config["fallback"], 
            last_resort_model=model_config["last_resort"],
        )
    
    @staticmethod
    def _resolve_api_key(api_key: Optional[str]) -> str:
        """Resolve Gemini API key from parameter or environment."""
        if api_key:
            return api_key
            
        env_key = os.getenv("GEMINI_API_KEY")
        if env_key:
            return env_key
            
        # Fallback to hardcoded key for development
        return "AIzaSyBzEr9w7CZ4nwp4p-Szqfqc1YgOCqm8nos"
    
    @staticmethod
    def _resolve_model_config(
        primary: Optional[str], 
        fallback: Optional[str], 
        last_resort: Optional[str]
    ) -> Dict[str, str]:
        """Resolve model configuration from parameters or environment."""
        return {
            "primary": (
                primary 
                or os.getenv("GEMINI_PRIMARY_MODEL") 
                or os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
            ),
            "fallback": (
                fallback 
                or os.getenv("GEMINI_FALLBACK_MODEL", "gemini-1.5-flash")
            ),
            "last_resort": (
                last_resort 
                or os.getenv("GEMINI_LAST_RESORT_MODEL", "gemini-2.0-flash-exp")
            ),
        }
    
    @staticmethod
    def _log_provider_config(model_config: Dict[str, str]) -> None:
        """Log the resolved provider configuration."""
        chain = f"{model_config['primary']} → {model_config['fallback']} → {model_config['last_resort']}"
        logger.info(f"🤖 Gemini provider configured with fallback chain: {chain}")

    @staticmethod
    def get_default_provider() -> AIProvider:
        """
        Get default AI provider with environment-based configuration.

        Returns:
            Fully configured AIProvider instance
        """
        return AIProviderFactory.create_provider()


# Global provider instance (singleton pattern)
_default_provider: Optional[AIProvider] = None


def get_ai_provider() -> AIProvider:
    """
    Get global AI provider instance (singleton).
    
    Lazily creates the provider on first access using environment configuration.

    Returns:
        Configured AIProvider instance
    """
    global _default_provider
    if _default_provider is None:
        _default_provider = AIProviderFactory.get_default_provider()
    return _default_provider


def set_ai_provider(provider: AIProvider) -> None:
    """
    Override the global AI provider instance.

    Args:
        provider: AIProvider instance to use globally
    """
    global _default_provider
    _default_provider = provider
    logger.info(f"🔄 Global AI provider updated: {provider.get_model_name()}")
