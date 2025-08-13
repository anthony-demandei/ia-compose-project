"""
OpenAI Provider implementation for backward compatibility.
Maintains existing OpenAI functionality while using the new AIProvider interface.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from openai import AsyncOpenAI
import tiktoken

from app.services.ai_provider import AIProvider, AIResponse
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


class OpenAIProvider(AIProvider):
    """OpenAI provider implementation."""
    
    def __init__(self, api_key: str, model_name: str = "gpt-4"):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            model_name: Model name (gpt-4, gpt-3.5-turbo, etc.)
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model_name = model_name
        
        # Initialize tokenizer
        try:
            self.encoding = tiktoken.encoding_for_model(model_name)
        except:
            self.encoding = tiktoken.get_encoding("cl100k_base")  # Default encoding
            
        logger.info(f"Initialized OpenAI provider with model: {model_name}")
    
    async def generate_response(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate a text response from OpenAI.
        
        Args:
            messages: List of message dictionaries with role and content
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            **kwargs: Additional OpenAI-specific parameters
            
        Returns:
            Generated text response
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            text_response = response.choices[0].message.content
            logger.debug(f"Generated response with {len(text_response)} characters")
            return text_response
            
        except Exception as e:
            logger.error(f"Error generating OpenAI response: {str(e)}")
            raise
    
    async def generate_json_response(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a JSON response from OpenAI.
        
        Args:
            messages: List of message dictionaries
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            **kwargs: Additional parameters
            
        Returns:
            Parsed JSON response as dictionary
        """
        try:
            # Use response_format for JSON
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                **kwargs
            )
            
            text_response = response.choices[0].message.content
            
            # Parse JSON
            try:
                json_response = json.loads(text_response)
                logger.debug(f"Successfully parsed JSON response with {len(json_response)} keys")
                return json_response
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw response: {text_response[:500]}")
                return {"error": "Failed to parse JSON", "raw_response": text_response[:500]}
                
        except Exception as e:
            logger.error(f"Error generating JSON response: {str(e)}")
            raise
    
    async def generate_multimodal_response(
        self,
        messages: List[Dict[str, Any]],
        images: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate response with multimodal input using GPT-4 Vision.
        
        Args:
            messages: List of message dictionaries
            images: List of base64 encoded images
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            **kwargs: Additional parameters
            
        Returns:
            Generated text response
        """
        try:
            # If images are provided separately, add them to the last user message
            if images and messages:
                # Find last user message
                for i in range(len(messages) - 1, -1, -1):
                    if messages[i].get("role") == "user":
                        # Convert to multimodal format if needed
                        if isinstance(messages[i]["content"], str):
                            messages[i]["content"] = [
                                {"type": "text", "text": messages[i]["content"]}
                            ]
                        # Add images
                        for img in images:
                            messages[i]["content"].append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img}",
                                    "detail": "high"
                                }
                            })
                        break
            
            # Use GPT-4 Vision for multimodal
            vision_model = "gpt-4-vision-preview" if "gpt-4" in self.model_name else self.model_name
            
            response = await self.client.chat.completions.create(
                model=vision_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            text_response = response.choices[0].message.content
            logger.debug(f"Generated multimodal response with {len(text_response)} characters")
            return text_response
            
        except Exception as e:
            logger.error(f"Error generating multimodal response: {str(e)}")
            raise
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string using tiktoken.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        try:
            if not text:
                return 0
            return len(self.encoding.encode(str(text)))
        except Exception as e:
            logger.warning(f"Failed to count tokens with tiktoken, using estimate: {e}")
            # Fallback to rough estimate (1 token ≈ 4 characters)
            return len(text) // 4
    
    def get_model_name(self) -> str:
        """Get the name of the current model being used."""
        return self.model_name
    
    def get_context_limit(self) -> int:
        """Get the context window limit for the current model."""
        # OpenAI model context limits
        context_limits = {
            "gpt-4": 8192,
            "gpt-4-32k": 32768,
            "gpt-4-turbo": 128000,
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            "gpt-3.5-turbo": 4096,
            "gpt-3.5-turbo-16k": 16384,
        }
        return context_limits.get(self.model_name, 4096)  # Default to 4k