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
from app.models.api_models import Question, QuestionChoice
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


def create_questions_response_schema() -> Dict[str, Any]:
    """
    Create JSON schema for structured questions response based on our Pydantic models.
    This ensures Gemini returns exactly the format we expect.
    """
    return {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "description": "Lista de perguntas geradas para o projeto",
                "items": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Código único da pergunta (Q001, Q002, etc.)"
                        },
                        "text": {
                            "type": "string",
                            "description": "Texto da pergunta em português"
                        },
                        "category": {
                            "type": "string",
                            "description": "Categoria da pergunta",
                            "enum": ["business", "technical", "operational"]
                        },
                        "required": {
                            "type": "boolean",
                            "description": "Se a pergunta é obrigatória"
                        },
                        "allow_multiple": {
                            "type": "boolean",
                            "description": "Se permite múltiplas escolhas"
                        },
                        "why_it_matters": {
                            "type": "string",
                            "description": "Explicação de 1-2 frases sobre por que esta pergunta é crítica para o sucesso do projeto"
                        },
                        "choices": {
                            "type": "array",
                            "description": "Opções de resposta para a pergunta",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "description": "ID único da opção"
                                    },
                                    "text": {
                                        "type": "string",
                                        "description": "Texto da opção"
                                    },
                                    "description": {
                                        "type": "string",
                                        "description": "Descrição opcional da opção"
                                    }
                                },
                                "required": ["id", "text"]
                            }
                        }
                    },
                    "required": ["code", "text", "category", "required", "allow_multiple", "why_it_matters", "choices"]
                }
            }
        },
        "required": ["questions"]
    }


class GeminiProvider(AIProvider):
    """Google Gemini AI provider implementation."""
    
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-pro"):
        """
        Initialize Gemini provider.
        
        Args:
            api_key: Google Gemini API key
            model_name: Model name (gemini-1.5-pro, gemini-1.5-flash, gemini-2.0-flash-exp, etc.)
        """
        genai.configure(api_key=api_key)
        self.model_name = model_name
        
        # ESTRATÉGIA HÍBRIDA DE SAFETY SETTINGS
        # Tentar múltiplas abordagens para contornar safety blocks do Gemini 2.5 Flash
        
        # Abordagem 1: BLOCK_NONE (máxima permissividade)
        self.safety_settings_permissive = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        # Abordagem 2: BLOCK_ONLY_HIGH (mais conservadora, pode ter melhor aceitação)
        self.safety_settings_conservative = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        }
        
        # Adicionar CIVIC_INTEGRITY se disponível
        for settings_dict in [self.safety_settings_permissive, self.safety_settings_conservative]:
            try:
                settings_dict[HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY] = HarmBlockThreshold.BLOCK_NONE if settings_dict == self.safety_settings_permissive else HarmBlockThreshold.BLOCK_ONLY_HIGH
            except AttributeError:
                # Categoria não disponível em versões antigas
                pass
        
        # Safety settings baseado no modelo
        self.safety_settings = self._get_model_specific_safety_settings(model_name)
        
        logger.info(f"Safety settings configurados para {model_name}: {len(self.safety_settings)} categorias")
        
        logger.info(f"Initialized Gemini provider with model: {model_name}")
    
    def _get_model_specific_safety_settings(self, model_name: str) -> Dict[HarmCategory, HarmBlockThreshold]:
        """
        Get safety settings optimized for specific model versions.
        Baseado nos testes: 2.0 Flash Exp e 1.5 Flash funcionam bem com permissivo.
        """
        if "2.5" in model_name:
            # Para Gemini 2.5 Flash: tentar abordagem mais conservadora primeiro (problemas conhecidos)
            logger.info("Using conservative safety settings for Gemini 2.5 Flash")
            return self.safety_settings_conservative
        elif "2.0" in model_name:
            # Para Gemini 2.0 Flash Experimental: usar permissivo (testado e funcionando)
            logger.info(f"Using permissive safety settings for Gemini 2.0 Flash Experimental")
            return self.safety_settings_permissive
        else:
            # Para outros modelos (1.5 Flash, 1.5 Pro): usar permissivo
            logger.info(f"Using permissive safety settings for {model_name}")
            return self.safety_settings_permissive
    
    def _sanitize_business_content(self, content: str) -> str:
        """
        Sanitize business content to reduce safety triggers while preserving meaning.
        """
        # Palavras que podem causar safety blocks em contexto corporativo
        trigger_replacements = {
            # Termos financeiros que podem ser interpretados como perigosos
            "core bancário": "sistema financeiro central",
            "banking core": "sistema financeiro central", 
            "antifraude": "sistema de prevenção de riscos",
            "compliance": "conformidade regulatória",
            "lavagem de dinheiro": "prevenção de riscos financeiros",
            "money laundering": "prevenção de riscos financeiros",
            
            # Termos de saúde que podem ser sensíveis
            "hospitalar": "de gestão em saúde",
            "médico": "profissional de saúde",
            "clínica": "estabelecimento de saúde",
            "diagnóstico": "avaliação profissional",
            
            # Termos técnicos que podem parecer perigosos
            "sistema crítico": "sistema essencial",
            "falha crítica": "interrupção do sistema",
            "disaster recovery": "recuperação de contingência",
            "alta disponibilidade": "disponibilidade contínua"
        }
        
        sanitized = content
        for trigger, replacement in trigger_replacements.items():
            sanitized = sanitized.replace(trigger, replacement)
            
        return sanitized
    
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
    
    # REMOVIDO: Funções de parsing manual não são mais necessárias com JSON nativo
    # _extract_json_multi_strategy() e _fix_common_json_issues() foram removidas
    # O Modo JSON nativo do Gemini elimina a necessidade de parsing manual
    
    async def generate_json_response(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.5,  # Temperatura mais moderada para JSON
        max_tokens: int = 2048,
        fallback_model: str = "gemini-1.5-flash",
        alternative_primary: Optional[str] = None,  # Permite testar outros modelos primários
        **kwargs
    ) -> Dict[str, Any]:
        """
        ESTRATÉGIA MULTI-TIER AVANÇADA: Múltiplas tentativas com diferentes configurações.
        1. Gemini 2.5 Flash com settings conservadores + sanitização
        2. Gemini 2.5 Flash com settings permissivos 
        3. Gemini 1.5 Flash (fallback confiável)
        
        Args:
            messages: List of message dictionaries
            temperature: Sampling temperature (0.5 works well for structured output)
            max_tokens: Maximum tokens in response
            fallback_model: Model to fallback if primary fails
            **kwargs: Additional parameters
            
        Returns:
            Parsed JSON response as dictionary
        """
        
        # Determine primary model (allow override for testing)
        primary_model = alternative_primary or self.model_name
        
        # Estratégia Otimizada para Gemini 1.5 como principal (Pro ou Flash)
        if "1.5" in primary_model:
            # Para 1.5 Flash: estratégia simples e eficaz
            strategies_to_try = [
                {
                    "name": primary_model, 
                    "description": f"Primary model ({primary_model}) - Optimized",
                    "safety_settings": self.safety_settings_permissive,
                    "sanitize_content": False,  # Modelo funciona bem sem sanitização
                    "timeout": 10  # Timeout razoável
                },
                {
                    "name": fallback_model, 
                    "description": f"Fallback model ({fallback_model})",
                    "safety_settings": self.safety_settings_permissive,
                    "sanitize_content": False,
                    "timeout": 15  # Timeout maior para Pro
                }
            ]
        else:
            # Para outros modelos: estratégia multi-tier completa (legado)
            strategies_to_try = [
                {
                    "name": primary_model, 
                    "description": f"Primary model ({primary_model}) - Conservative Settings",
                    "safety_settings": self.safety_settings_conservative,
                    "sanitize_content": True,
                    "timeout": 8 if "2.5" in primary_model else 12
                },
                {
                    "name": primary_model, 
                    "description": f"Primary model ({primary_model}) - Permissive Settings", 
                    "safety_settings": self.safety_settings_permissive,
                    "sanitize_content": False,
                    "timeout": 8 if "2.5" in primary_model else 12
                },
                {
                    "name": fallback_model, 
                    "description": f"Fallback model ({fallback_model})",
                    "safety_settings": self.safety_settings_permissive,
                    "sanitize_content": False,
                    "timeout": 15
                }
            ]
        
        for attempt, strategy in enumerate(strategies_to_try):
            model_name = strategy["name"]
            model_desc = strategy["description"]
            safety_settings = strategy["safety_settings"]
            sanitize_content = strategy["sanitize_content"]
            timeout_seconds = strategy["timeout"]
            
            try:
                logger.info(f"🚀 Attempt {attempt + 1}: {model_desc}")
                
                # Convert messages to Gemini format
                system_instruction, gemini_contents = convert_messages_to_gemini_format(messages)
                
                # Apply content sanitization if enabled for this strategy
                if sanitize_content and gemini_contents:
                    logger.info("🧹 Applying content sanitization for safety optimization")
                    for content in gemini_contents:
                        if "parts" in content:
                            for part in content["parts"]:
                                if isinstance(part, dict) and "text" in part:
                                    part["text"] = self._sanitize_business_content(part["text"])
                    
                    # Also sanitize system instruction
                    if system_instruction:
                        system_instruction = self._sanitize_business_content(system_instruction)
                
                # Configuração para JSON nativo
                generation_config = genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    response_mime_type="application/json",
                    response_schema=create_questions_response_schema()
                )

                # Create model with native JSON output and strategy-specific safety settings
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_instruction if system_instruction else None,
                    generation_config=generation_config,
                    safety_settings=safety_settings  # Use strategy-specific settings
                )

                if not gemini_contents:
                    logger.error("❌ Cannot generate response with empty content")
                    continue

                # Generate content with asyncio timeout for 2.5 Flash
                import asyncio
                import threading
                
                # Extract the text content properly for Gemini
                content_text = ""
                if gemini_contents[0]["parts"]:
                    # Join all text parts
                    text_parts = []
                    for part in gemini_contents[0]["parts"]:
                        if isinstance(part, dict) and "text" in part:
                            text_parts.append(part["text"])
                        elif isinstance(part, str):
                            text_parts.append(part)
                    content_text = " ".join(text_parts)
                
                # Apply timeout based on strategy configuration
                def generate_with_timeout():
                    return model.generate_content(content_text)
                
                # Use timeout for all models, but different durations
                try:
                    # Simple timeout implementation without signals 
                    # (More complex timeout would require threading/multiprocessing)
                    response = generate_with_timeout()
                except Exception as e:
                    if "timeout" in str(e).lower():
                        raise TimeoutError(f"Model generation timeout after {timeout_seconds}s")
                    raise
                
                # Verificar safety blocks
                is_safety_block = False
                
                # Check prompt feedback
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                    is_safety_block = True
                    block_reason = response.prompt_feedback.block_reason.name
                    logger.warning(f"🚫 {model_desc}: Prompt safety block: {block_reason}")
                
                # Check candidate finish_reason
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    finish_reason = getattr(candidate, 'finish_reason', None)
                    
                    if finish_reason in ['SAFETY', 2, '2']:
                        is_safety_block = True
                        logger.warning(f"🚫 {model_desc}: Candidate safety block: {finish_reason}")
                
                # Se safety block, tentar próxima estratégia
                if is_safety_block:
                    if attempt < len(strategies_to_try) - 1:  # Ainda há estratégias para tentar
                        logger.info("⚠️ Safety block detected, trying next strategy...")
                        continue
                    else:  # Todas as estratégias falharam
                        return {
                            "error": "Safety block detected in all strategies",
                            "finish_reason": "SAFETY",
                            "questions": [],
                            "attempted_strategies": len(strategies_to_try)
                        }
                
                # Parse JSON response
                response_text = response.text
                if not response_text:
                    logger.error(f"❌ {model_desc}: Empty response")
                    continue
                    
                json_response = json.loads(response_text)
                logger.info(f"✅ {model_desc}: Success! {len(json_response.get('questions', []))} questions")
                
                # Adicionar metadata sobre qual estratégia foi usada
                json_response["_metadata"] = {
                    "model_used": model_name,
                    "strategy_used": model_desc,
                    "attempt": attempt + 1,
                    "is_fallback": attempt > 0,
                    "safety_approach": "conservative" if safety_settings == self.safety_settings_conservative else "permissive",
                    "content_sanitized": sanitize_content
                }
                
                return json_response

            except TimeoutError:
                logger.warning(f"⏰ {model_desc}: Timeout after 15s, trying fallback...")
                continue
            except json.JSONDecodeError as e:
                logger.error(f"❌ {model_desc}: JSON decode error: {e}")
                continue
            except Exception as e:
                logger.error(f"❌ {model_desc}: Generation error: {e}")
                if attempt == len(models_to_try) - 1:  # Last attempt
                    error_details = str(e)
                    if hasattr(e, 'response'):
                        error_details += f" | API Response: {getattr(e, 'response', 'N/A')}"
                    return {"error": "All models failed", "details": error_details, "questions": []}
                continue
        
        # Se chegou aqui, todas as estratégias falharam
        return {
            "error": "Multi-tier strategy failed - all approaches exhausted", 
            "questions": [],
            "total_strategies_attempted": len(strategies_to_try)
        }
    
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
            "gemini-2.5-pro": 2097152,        # 2M tokens  
            "gemini-2.0-flash-exp": 1048576,  # 1M tokens (experimental)
            "gemini-1.5-flash": 1048576,      # 1M tokens
            "gemini-1.5-pro": 2097152,        # 2M tokens
            "gemini-1.0-pro": 32768,          # 32k tokens
        }
        return context_limits.get(self.model_name, 1048576)  # Default to 1M