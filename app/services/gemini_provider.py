"""
Google Gemini AI Provider implementation.
Supports Gemini 2.0 Flash and other Gemini models.
"""

import json
import logging
from typing import Dict, List, Any, Optional
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from app.services.ai_provider import (
    AIProvider, 
    AIResponse, 
    convert_messages_to_gemini_format,
    convert_gemini_response_to_standard_format
)
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


class GeminiProvider(AIProvider):
    """Google Gemini AI provider implementation."""
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        """
        Initialize Gemini provider.
        
        Args:
            api_key: Google Gemini API key
            model_name: Model name (gemini-2.5-flash, gemini-2.0-flash-exp, gemini-1.5-pro, etc.)
        """
        genai.configure(api_key=api_key)
        self.model_name = model_name
        
        # Safety settings - mais permissivo para uso profissional
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        logger.info(f"Initialized Gemini provider with model: {model_name}")
    
    async def generate_response(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate a text response from Gemini.
        
        Args:
            messages: List of message dictionaries with role and content
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            **kwargs: Additional Gemini-specific parameters
            
        Returns:
            Generated text response
        """
        try:
            # Convert messages to Gemini format
            system_instruction, gemini_contents = convert_messages_to_gemini_format(messages)
            
            # Create model with system instruction if available
            try:
                # Try with system_instruction (newer versions)
                model = genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=system_instruction if system_instruction else None,
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": max_tokens,
                        "top_p": kwargs.get("top_p", 0.95),
                        "top_k": kwargs.get("top_k", 40),
                    },
                    safety_settings=self.safety_settings
                )
            except TypeError:
                # Fallback for older versions without system_instruction
                model = genai.GenerativeModel(
                    model_name=self.model_name,
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": max_tokens,
                        "top_p": kwargs.get("top_p", 0.95),
                        "top_k": kwargs.get("top_k", 40),
                    },
                    safety_settings=self.safety_settings
                )
                # Add system instruction to first message if needed
                if system_instruction and gemini_contents:
                    # Prepend system instruction as first user message
                    system_msg = {
                        "role": "user",
                        "parts": [{"text": f"System Instructions: {system_instruction}\n\nNow, let's begin:"}]
                    }
                    gemini_contents = [system_msg] + gemini_contents
            
            # Handle empty contents (only system messages)
            if not gemini_contents:
                # If we only have system messages, create a simple user prompt
                gemini_contents = [{
                    "role": "user",
                    "parts": [{"text": "Please provide your response based on the system instructions."}]
                }]
            
            # Start chat or generate content
            if len(gemini_contents) > 1:
                # Multi-turn conversation
                chat = model.start_chat(history=gemini_contents[:-1])
                response = chat.send_message(gemini_contents[-1]["parts"])
            else:
                # Single turn
                response = model.generate_content(gemini_contents[0]["parts"])
            
            # Extract text from response
            text_response = convert_gemini_response_to_standard_format(response)
            
            logger.debug(f"Generated response with {len(text_response)} characters")
            return text_response
            
        except Exception as e:
            logger.error(f"Error generating Gemini response: {str(e)}")
            raise
    
    async def generate_json_response(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a JSON response from Gemini.
        
        Args:
            messages: List of message dictionaries
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            **kwargs: Additional parameters
            
        Returns:
            Parsed JSON response as dictionary
        """
        try:
            # Convert messages to Gemini format
            system_instruction, gemini_contents = convert_messages_to_gemini_format(messages)
            
            # Add JSON instruction to system prompt
            json_instruction = "\n\nIMPORTANT: You MUST respond with valid JSON only. No explanations or text outside the JSON structure."
            if system_instruction:
                system_instruction += json_instruction
            else:
                system_instruction = json_instruction
            
            # Create model with JSON response configuration
            try:
                # Try with response_mime_type for newer versions
                try:
                    model = genai.GenerativeModel(
                        model_name=self.model_name,
                        system_instruction=system_instruction,
                        generation_config={
                            "temperature": temperature,
                            "max_output_tokens": max_tokens,
                            "response_mime_type": "application/json",  # Force JSON response
                            "top_p": kwargs.get("top_p", 0.95),
                        },
                        safety_settings=self.safety_settings
                    )
                except (TypeError, ValueError):
                    # Try without response_mime_type
                    model = genai.GenerativeModel(
                        model_name=self.model_name,
                        system_instruction=system_instruction,
                        generation_config={
                            "temperature": temperature,
                            "max_output_tokens": max_tokens,
                            "top_p": kwargs.get("top_p", 0.95),
                        },
                        safety_settings=self.safety_settings
                    )
            except TypeError:
                # Fallback for older versions without system_instruction
                model = genai.GenerativeModel(
                    model_name=self.model_name,
                    generation_config={
                        "temperature": temperature,
                        "max_output_tokens": max_tokens,
                        "top_p": kwargs.get("top_p", 0.95),
                    },
                    safety_settings=self.safety_settings
                )
                # Add JSON instruction to first message
                if system_instruction and gemini_contents:
                    system_msg = {
                        "role": "user",
                        "parts": [{"text": f"{system_instruction}\n\nRespond with valid JSON:"}]
                    }
                    gemini_contents = [system_msg] + gemini_contents
            
            # Handle empty contents
            if not gemini_contents:
                gemini_contents = [{
                    "role": "user",
                    "parts": [{"text": "Generate the JSON response based on the instructions."}]
                }]
            
            # Generate response
            if len(gemini_contents) > 1:
                chat = model.start_chat(history=gemini_contents[:-1])
                response = chat.send_message(gemini_contents[-1]["parts"])
            else:
                response = model.generate_content(gemini_contents[0]["parts"])
            
            # Extract and parse JSON
            text_response = convert_gemini_response_to_standard_format(response)
            
            # Clean up the response (remove markdown if present)
            if text_response.startswith("```json"):
                text_response = text_response[7:]
            if text_response.startswith("```"):
                text_response = text_response[3:]
            if text_response.endswith("```"):
                text_response = text_response[:-3]
            text_response = text_response.strip()
            
            # Parse JSON
            try:
                json_response = json.loads(text_response)
                logger.debug(f"Successfully parsed JSON response with {len(json_response)} keys")
                return json_response
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw response: {text_response[:500]}")
                # Try to extract JSON from the response
                import re
                json_match = re.search(r'\{.*\}', text_response, re.DOTALL)
                if json_match:
                    try:
                        json_response = json.loads(json_match.group())
                        return json_response
                    except:
                        pass
                # Return a default structure
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
        Generate response with multimodal input (text + images).
        
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
                                "image_url": {"url": f"data:image/jpeg;base64,{img}"}
                            })
                        break
            
            # Use regular generate_response which handles multimodal
            return await self.generate_response(messages, temperature, max_tokens, **kwargs)
            
        except Exception as e:
            logger.error(f"Error generating multimodal response: {str(e)}")
            raise
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string using Gemini's tokenizer.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        try:
            # Create a model instance for token counting
            model = genai.GenerativeModel(self.model_name)
            # Use Gemini's count_tokens method
            token_count = model.count_tokens(text)
            if hasattr(token_count, 'total_tokens'):
                return token_count.total_tokens
            return len(text) // 4  # Rough estimate if count fails
        except Exception as e:
            logger.warning(f"Failed to count tokens with Gemini, using estimate: {e}")
            # Fallback to rough estimate (1 token ≈ 4 characters)
            return len(text) // 4
    
    def get_model_name(self) -> str:
        """Get the name of the current model being used."""
        return self.model_name
    
    def get_context_limit(self) -> int:
        """Get the context window limit for the current model."""
        # Gemini context limits
        context_limits = {
            "gemini-2.5-flash": 1048576,      # 1M tokens
            "gemini-2.0-flash-exp": 1048576,  # 1M tokens
            "gemini-1.5-flash": 1048576,      # 1M tokens
            "gemini-1.5-pro": 2097152,        # 2M tokens
            "gemini-1.0-pro": 32768,          # 32k tokens
        }
        return context_limits.get(self.model_name, 1048576)  # Default to 1M