"""
Abstract AI Provider Interface for supporting multiple AI backends.
Allows seamless switching between OpenAI, Google Gemini, and other providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """Abstract base class for AI providers (OpenAI, Gemini, etc.)"""
    
    @abstractmethod
    async def generate_response(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate a text response from the AI model.
        
        Args:
            messages: List of message dictionaries with role and content
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    async def generate_json_response(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a JSON response from the AI model.
        
        Args:
            messages: List of message dictionaries
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Parsed JSON response as dictionary
        """
        pass
    
    @abstractmethod
    async def generate_multimodal_response(
        self,
        messages: List[Dict[str, Any]],
        images: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate response with multimodal input (text + images).
        
        Args:
            messages: List of message dictionaries
            images: List of base64 encoded images
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Get the name of the current model being used."""
        pass
    
    @abstractmethod
    def get_context_limit(self) -> int:
        """Get the context window limit for the current model."""
        pass


@dataclass
class AIResponse:
    """Standardized response format from AI providers."""
    content: str
    usage: Optional[Dict[str, int]] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None
    
    
class AIProviderType(Enum):
    """Supported AI provider types."""
    GEMINI = "gemini"
    
    
def convert_messages_to_gemini_format(messages: List[Dict[str, Any]]) -> Tuple[str, List[Dict]]:
    """
    Convert standard message format to Gemini format.
    
    Args:
        messages: Messages with roles (system, user, assistant)
        
    Returns:
        Tuple of (system_instruction, gemini_contents)
    """
    system_instruction = ""
    gemini_contents = []
    
    for message in messages:
        role = message.get("role", "")
        content = message.get("content", "")
        
        if role == "system":
            # Gemini uses system_instruction separately
            if system_instruction:
                system_instruction += "\n\n"
            system_instruction += content
        elif role == "user":
            # Convert to Gemini user format
            if isinstance(content, str):
                gemini_contents.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })
            elif isinstance(content, list):
                # Handle multimodal content
                parts = []
                for item in content:
                    if item.get("type") == "text":
                        parts.append({"text": item.get("text", "")})
                    elif item.get("type") == "image_url":
                        # Extract base64 data
                        image_data = item.get("image_url", {}).get("url", "")
                        if image_data.startswith("data:"):
                            # Remove data URL prefix
                            base64_data = image_data.split(",")[1] if "," in image_data else image_data
                            parts.append({"inline_data": {
                                "mime_type": "image/jpeg",
                                "data": base64_data
                            }})
                if parts:
                    gemini_contents.append({"role": "user", "parts": parts})
        elif role == "assistant":
            # Convert to Gemini model format
            gemini_contents.append({
                "role": "model",
                "parts": [{"text": content}]
            })
    
    return system_instruction, gemini_contents


def convert_gemini_response_to_standard_format(gemini_response) -> str:
    """
    Convert Gemini response to standard text format with robust error handling.
    
    Args:
        gemini_response: Response from Gemini API
        
    Returns:
        Text content from the response
    """
    try:
        # Handle direct text attribute
        if hasattr(gemini_response, 'text') and gemini_response.text:
            return gemini_response.text
            
        # Handle candidates structure
        if hasattr(gemini_response, 'candidates') and gemini_response.candidates:
            # Safely get first candidate
            try:
                candidate = gemini_response.candidates[0]
                
                # Try to get content.parts
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts') and candidate.content.parts:
                    text_parts = []
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                    
                    if text_parts:
                        return ' '.join(text_parts)
                
                # Fallback: try candidate.text directly
                if hasattr(candidate, 'text') and candidate.text:
                    return candidate.text
                    
            except (IndexError, AttributeError) as e:
                logger.warning(f"Error accessing candidates: {e}")
        
        # Try to access parts directly if it's a simple structure
        if hasattr(gemini_response, 'parts'):
            text_parts = []
            for part in gemini_response.parts:
                if hasattr(part, 'text') and part.text:
                    text_parts.append(part.text)
            if text_parts:
                return ' '.join(text_parts)
        
        # Final fallback: string conversion
        response_str = str(gemini_response)
        if response_str and response_str != "None":
            return response_str
            
        # If all else fails
        return "No response content available"
        
    except Exception as e:
        logger.error(f"Error extracting Gemini response: {e}")
        return f"Error extracting response: {str(e)}"