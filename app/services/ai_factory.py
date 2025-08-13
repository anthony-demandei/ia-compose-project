"""
AI Provider Factory for creating and managing AI providers.
Allows dynamic selection between OpenAI, Gemini, and other providers.
"""

import os
from typing import Optional
from enum import Enum

from app.services.ai_provider import AIProvider, AIProviderType
from app.services.gemini_provider import GeminiProvider
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


class AIProviderFactory:
    """Factory class for creating AI providers."""
    
    @staticmethod
    def create_provider(
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> AIProvider:
        """
        Create an AI provider instance (Gemini only).
        
        Args:
            api_key: API key for Gemini. If None, uses env var or default
            model_name: Model name. If None, uses default
            
        Returns:
            GeminiProvider instance
        """
        # Get Gemini configuration
        if api_key is None:
            # Try to get from env, but use provided key as fallback
            api_key = os.getenv("GEMINI_API_KEY", "AIzaSyBzEr9w7CZ4nwp4p-Szqfqc1YgOCqm8nos")
            if not api_key:
                # Use the provided key
                api_key = "AIzaSyBzEr9w7CZ4nwp4p-Szqfqc1YgOCqm8nos"
        
        if model_name is None:
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        logger.info(f"Using Gemini provider with model: {model_name}")
        return GeminiProvider(api_key=api_key, model_name=model_name)
    
    @staticmethod
    def get_default_provider() -> AIProvider:
        """
        Get the default AI provider based on environment configuration.
        
        Returns:
            Default AIProvider instance
        """
        return AIProviderFactory.create_provider()
    


# Global singleton instance for easy access
_default_provider: Optional[AIProvider] = None


def get_ai_provider() -> AIProvider:
    """
    Get the global AI provider instance.
    Creates one if it doesn't exist.
    
    Returns:
        AIProvider instance
    """
    global _default_provider
    if _default_provider is None:
        _default_provider = AIProviderFactory.get_default_provider()
    return _default_provider


def set_ai_provider(provider: AIProvider):
    """
    Set the global AI provider instance.
    
    Args:
        provider: AIProvider instance to use globally
    """
    global _default_provider
    _default_provider = provider
    logger.info(f"Global AI provider set to: {provider.get_model_name()}")