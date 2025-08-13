"""
Abstract AI Provider Interface for supporting multiple AI backends.
Allows seamless switching between OpenAI, Google Gemini, and other providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


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
    OPENAI = "openai"
    GEMINI = "gemini"
    
    
def convert_messages_to_gemini_format(messages: List[Dict[str, Any]]) -> Tuple[str, List[Dict]]:
    """
    Convert OpenAI message format to Gemini format.
    
    Args:
        messages: OpenAI-style messages with roles (system, user, assistant)
        
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


def convert_gemini_response_to_openai_format(gemini_response) -> str:
    """
    Convert Gemini response to OpenAI-like format.
    
    Args:
        gemini_response: Response from Gemini API
        
    Returns:
        Text content from the response
    """
    try:
        # Handle different response structures
        if hasattr(gemini_response, 'text'):
            return gemini_response.text
        elif hasattr(gemini_response, 'candidates') and gemini_response.candidates:
            # Get first candidate's content
            candidate = gemini_response.candidates[0]
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                # Join all text parts
                text_parts = []
                for part in candidate.content.parts:
                    if hasattr(part, 'text'):
                        text_parts.append(part.text)
                return ' '.join(text_parts)
        # Fallback to string conversion
        return str(gemini_response)
    except Exception as e:
        return f"Error extracting response: {str(e)}"