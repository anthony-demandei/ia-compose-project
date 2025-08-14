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
        primary_model: Optional[str] = None,
        fallback_model: Optional[str] = None,
        last_resort_model: Optional[str] = None,
    ) -> AIProvider:
        """
        Create an AI provider instance (Gemini only) with model fallback chain.

        Args:
            api_key: API key for Gemini. If None, uses env var or default
            primary_model: Primary model name. If None, uses env var or default
            fallback_model: Fallback model name. If None, uses env var or default
            last_resort_model: Last resort model name. If None, uses env var or default

        Returns:
            GeminiProvider instance with fallback chain
        """
        if api_key is None:
            api_key = os.getenv(
                "GEMINI_API_KEY", "AIzaSyBzEr9w7CZ4nwp4p-Szqfqc1YgOCqm8nos"
            )
            if not api_key:
                api_key = "AIzaSyBzEr9w7CZ4nwp4p-Szqfqc1YgOCqm8nos"
        if primary_model is None:
            primary_model = os.getenv("GEMINI_PRIMARY_MODEL") or os.getenv(
                "GEMINI_MODEL", "gemini-1.5-pro"
            )

        if fallback_model is None:
            fallback_model = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-1.5-flash")

        if last_resort_model is None:
            last_resort_model = os.getenv(
                "GEMINI_LAST_RESORT_MODEL", "gemini-2.0-flash-exp"
            )

        logger.info(
            f"Using Gemini provider with fallback chain: {primary_model} -> {fallback_model} -> {last_resort_model}"
        )
        return GeminiProvider(
            api_key=api_key,
            primary_model=primary_model,
            fallback_model=fallback_model,
            last_resort_model=last_resort_model,
        )

    @staticmethod
    def get_default_provider() -> AIProvider:
        """
        Get the default AI provider based on environment configuration.

        Returns:
            Default AIProvider instance
        """
        return AIProviderFactory.create_provider()


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
