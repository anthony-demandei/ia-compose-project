"""
AI Provider Factory for creating and managing AI providers.
Allows dynamic selection between OpenAI, Gemini, and other providers.
"""

import os
from typing import Optional
from enum import Enum

from app.services.ai_provider import AIProvider, AIProviderType
from app.services.openai_provider import OpenAIProvider
from app.services.gemini_provider import GeminiProvider
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


class AIProviderFactory:
    """Factory class for creating AI providers."""
    
    @staticmethod
    def create_provider(
        provider_type: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> AIProvider:
        """
        Create an AI provider instance.
        
        Args:
            provider_type: Type of provider ("openai", "gemini"). If None, uses env var AI_PROVIDER
            api_key: API key for the provider. If None, uses env var
            model_name: Model name. If None, uses default for provider
            
        Returns:
            AIProvider instance
            
        Raises:
            ValueError: If provider type is not supported
        """
        # Get provider type from env if not specified
        if provider_type is None:
            provider_type = os.getenv("AI_PROVIDER", "gemini").lower()
        else:
            provider_type = provider_type.lower()
        
        logger.info(f"Creating AI provider of type: {provider_type}")
        
        # Create provider based on type
        if provider_type == "openai":
            # Get OpenAI configuration
            if api_key is None:
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY not found in environment variables")
            
            if model_name is None:
                model_name = os.getenv("OPENAI_MODEL", "gpt-4")
            
            logger.info(f"Using OpenAI provider with model: {model_name}")
            return OpenAIProvider(api_key=api_key, model_name=model_name)
        
        elif provider_type == "gemini":
            # Get Gemini configuration
            if api_key is None:
                # Try to get from env, but use provided key as fallback
                api_key = os.getenv("GEMINI_API_KEY", "AIzaSyBzEr9w7CZ4nwp4p-Szqfqc1YgOCqm8nos")
                if not api_key:
                    # Use the provided key
                    api_key = "AIzaSyBzEr9w7CZ4nwp4p-Szqfqc1YgOCqm8nos"
            
            if model_name is None:
                model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
            
            logger.info(f"Using Gemini provider with model: {model_name}")
            return GeminiProvider(api_key=api_key, model_name=model_name)
        
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")
    
    @staticmethod
    def get_default_provider() -> AIProvider:
        """
        Get the default AI provider based on environment configuration.
        
        Returns:
            Default AIProvider instance
        """
        return AIProviderFactory.create_provider()
    
    @staticmethod
    def switch_provider(provider_type: str) -> AIProvider:
        """
        Switch to a different AI provider.
        
        Args:
            provider_type: Type of provider to switch to
            
        Returns:
            New AIProvider instance
        """
        logger.info(f"Switching AI provider to: {provider_type}")
        return AIProviderFactory.create_provider(provider_type=provider_type)


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