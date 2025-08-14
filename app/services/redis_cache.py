"""
Redis Cache Service for caching questions and documents.
Provides persistent caching with TTL and fallback to in-memory cache.
"""

import json
import hashlib
import logging
from typing import Dict, List, Optional, Any
from datetime import timedelta
import redis.asyncio as aioredis
import redis
from redis.exceptions import RedisError

from app.models.api_models import Question, StackDocumentation
from app.utils.pii_safe_logging import get_pii_safe_logger
from app.utils.config import get_settings

logger = get_pii_safe_logger(__name__)


class RedisCache:
    """
    High-performance Redis cache with intelligent fallback.
    
    Provides async caching for questions and documents with automatic
    failover to in-memory cache when Redis is unavailable.
    
    Features:
    • Async Redis operations with connection pooling
    • TTL-based expiration (questions: 1h, documents: 24h)
    • Automatic fallback to in-memory cache
    • JSON serialization with Pydantic model support
    • Comprehensive SSL and authentication support
    """

    def __init__(self):
        """Initialize Redis cache with intelligent connection management."""
        self.settings = get_settings()
        
        # Redis clients
        self._async_client: Optional[aioredis.Redis] = None
        self._sync_client: Optional[redis.Redis] = None
        
        # Fallback storage
        self._memory_cache: Dict[str, Any] = {}
        
        # Connection state
        self._is_connected = False
        
        # Cache configuration
        self.questions_ttl = self.settings.redis_ttl_questions
        self.documents_ttl = self.settings.redis_ttl_documents
        self.cache_enabled = self.settings.enable_redis_cache

        if self.cache_enabled:
            self._establish_connection()

    def _establish_connection(self):
        """Establish Redis connection with comprehensive error handling."""
        try:
            connection_config = self._build_connection_config()
            
            # Create async client
            self._async_client = aioredis.Redis(**connection_config)
            
            # Create sync client with timeout adjustments
            sync_config = connection_config.copy()
            sync_config["socket_connect_timeout"] = self.settings.redis_connection_timeout
            self._sync_client = redis.Redis(**sync_config)

            # Verify connection
            self._sync_client.ping()
            self._is_connected = True

            connection_info = self._format_connection_info()
            logger.info(f"✅ Redis cache connected: {connection_info}")

        except Exception as error:
            logger.warning(f"⚠️ Redis unavailable, using memory fallback: {error}")
            self._is_connected = False

    def _build_connection_config(self) -> Dict[str, Any]:
        """Build Redis connection configuration from environment settings."""
        # URL-based configuration (preferred for cloud deployments)
        if self.settings.redis_url:
            return self._build_url_config()
        
        # Parameter-based configuration (preferred for local/Docker)
        return self._build_parameter_config()
    
    def _build_url_config(self) -> Dict[str, Any]:
        """Build connection config from Redis URL."""
        return {
            "url": self.settings.redis_url,
            "decode_responses": True,
            "max_connections": self.settings.redis_max_connections,
            "retry_on_timeout": self.settings.redis_retry_on_timeout,
            "health_check_interval": self.settings.redis_health_check_interval,
            "socket_timeout": self.settings.redis_socket_timeout,
        }
    
    def _build_parameter_config(self) -> Dict[str, Any]:
        """Build connection config from individual parameters."""
        config = {
            "host": self.settings.redis_host,
            "port": self.settings.redis_port,
            "db": self.settings.redis_db,
            "decode_responses": True,
            "max_connections": self.settings.redis_max_connections,
            "retry_on_timeout": self.settings.redis_retry_on_timeout,
            "health_check_interval": self.settings.redis_health_check_interval,
            "socket_timeout": self.settings.redis_socket_timeout,
        }
        
        # Add authentication if configured
        self._add_auth_config(config)
        
        # Add SSL configuration if enabled
        self._add_ssl_config(config)
        
        return config
    
    def _add_auth_config(self, config: Dict[str, Any]) -> None:
        """Add authentication configuration to connection config."""
        if self.settings.redis_username:
            config["username"] = self.settings.redis_username
        if self.settings.redis_password:
            config["password"] = self.settings.redis_password
    
    def _add_ssl_config(self, config: Dict[str, Any]) -> None:
        """Add SSL configuration to connection config."""
        if not self.settings.redis_ssl:
            return
            
        config["ssl"] = True
        config["ssl_cert_reqs"] = self.settings.redis_ssl_cert_reqs
        
        # Optional SSL certificate files
        if self.settings.redis_ssl_ca_certs:
            config["ssl_ca_certs"] = self.settings.redis_ssl_ca_certs
        if self.settings.redis_ssl_certfile:
            config["ssl_certfile"] = self.settings.redis_ssl_certfile
        if self.settings.redis_ssl_keyfile:
            config["ssl_keyfile"] = self.settings.redis_ssl_keyfile

    def _format_connection_info(self) -> str:
        """Format connection info for logging (password-safe)."""
        if self.settings.redis_url:
            return self._format_url_info()
        return self._format_parameter_info()
    
    def _format_url_info(self) -> str:
        """Format Redis URL info for logging."""
        url_parts = self.settings.redis_url.split("@")
        if len(url_parts) > 1:
            return f"Redis URL ending with @{url_parts[-1]}"
        return "Redis URL connection"
    
    def _format_parameter_info(self) -> str:
        """Format parameter-based connection info for logging."""
        ssl_suffix = " (SSL)" if self.settings.redis_ssl else ""
        return f"{self.settings.redis_host}:{self.settings.redis_port}/{self.settings.redis_db}{ssl_suffix}"

    async def _ensure_connection(self) -> bool:
        """Verify Redis connection is active and healthy."""
        if not self.cache_enabled:
            return False

        if self._is_connected and self._async_client:
            try:
                await self._async_client.ping()
                return True
            except (RedisError, ConnectionError):
                self._is_connected = False
                logger.warning("Redis connection lost, switching to memory cache")

        return False

    def _create_cache_key(self, prefix: str, identifier: str) -> str:
        """Create namespaced cache key."""
        return f"{prefix}:{identifier}"

    def _hash_project_description(self, description: str) -> str:
        """Generate deterministic hash for project description."""
        return hashlib.md5(description.encode()).hexdigest()

    # === QUESTIONS CACHE ===

    async def get_cached_questions(
        self, project_description: str
    ) -> Optional[List[Question]]:
        """
        Retrieve cached questions for a project description.

        Args:
            project_description: Project description to lookup

        Returns:
            List of Question objects if found in cache, None otherwise
        """
        if not self.cache_enabled:
            return None

        cache_key = self._build_questions_cache_key(project_description)
        
        # Try Redis cache first (faster, persistent)
        questions = await self._get_questions_from_redis(cache_key)
        if questions is not None:
            return questions
        
        # Fallback to memory cache
        return self._get_questions_from_memory(cache_key)
    
    def _build_questions_cache_key(self, project_description: str) -> str:
        """Build cache key for project questions."""
        project_hash = self._hash_project_description(project_description)
        return self._create_cache_key("questions", project_hash)
    
    async def _get_questions_from_redis(self, cache_key: str) -> Optional[List[Question]]:
        """Attempt to retrieve questions from Redis cache."""
        if not await self._ensure_connection():
            return None
            
        try:
            cached_data = await self._async_client.get(cache_key)
            if not cached_data:
                return None
                
            questions_data = json.loads(cached_data)
            questions = [Question(**q) for q in questions_data]
            
            logger.info(f"✅ Questions retrieved from Redis (key: {cache_key[:20]}...)")
            return questions
            
        except Exception as error:
            logger.error(f"Redis retrieval error: {error}")
            return None
    
    def _get_questions_from_memory(self, cache_key: str) -> Optional[List[Question]]:
        """Attempt to retrieve questions from memory cache."""
        cache_entry = self._memory_cache.get(cache_key)
        if not cache_entry:
            return None
            
        if not self._is_memory_entry_valid(cache_entry):
            return None
            
        questions_data = cache_entry["data"]
        questions = [Question(**q) for q in questions_data]
        
        logger.info(f"✅ Questions retrieved from memory (key: {cache_key[:20]}...)")
        return questions

    async def cache_questions(
        self,
        project_description: str,
        questions: List[Question],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Store questions in cache for future retrieval.

        Args:
            project_description: Project description key
            questions: Question objects to cache
            ttl: Time to live in seconds (uses default if None)

        Returns:
            True if successfully cached
        """
        if not self.cache_enabled:
            return False

        cache_key = self._build_questions_cache_key(project_description)
        cache_ttl = ttl or self.questions_ttl
        questions_data = [q.dict() for q in questions]

        # Attempt Redis caching first
        if await self._cache_questions_to_redis(cache_key, questions_data, cache_ttl):
            return True
        
        # Fall back to memory caching
        return self._cache_questions_to_memory(cache_key, questions_data, cache_ttl)
    
    async def _cache_questions_to_redis(self, cache_key: str, questions_data: List[Dict], ttl: int) -> bool:
        """Attempt to cache questions to Redis."""
        if not await self._ensure_connection():
            return False
            
        try:
            await self._async_client.setex(cache_key, ttl, json.dumps(questions_data))
            logger.info(f"✅ Questions cached to Redis (key: {cache_key[:20]}..., TTL: {ttl}s)")
            return True
        except Exception as error:
            logger.error(f"Redis caching error: {error}")
            return False
    
    def _cache_questions_to_memory(self, cache_key: str, questions_data: List[Dict], ttl: int) -> bool:
        """Cache questions to memory as fallback."""
        import time
        
        self._memory_cache[cache_key] = {
            "data": questions_data,
            "expires_at": time.time() + ttl,
        }
        
        logger.info(f"✅ Questions cached to memory (key: {cache_key[:20]}..., TTL: {ttl}s)")
        return True

    # === DOCUMENTS CACHE ===

    async def get_cached_document(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached document for a session.

        Args:
            session_id: Session identifier

        Returns:
            Document data if found in cache, None otherwise
        """
        if not self.cache_enabled:
            return None

        cache_key = self._build_document_cache_key(session_id)
        
        # Try Redis cache first
        document = await self._get_document_from_redis(cache_key, session_id)
        if document is not None:
            return document
            
        # Fallback to memory cache
        return self._get_document_from_memory(cache_key, session_id)
    
    def _build_document_cache_key(self, session_id: str) -> str:
        """Build cache key for session documents."""
        return self._create_cache_key("doc", session_id)
    
    async def _get_document_from_redis(self, cache_key: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Attempt to retrieve document from Redis cache."""
        if not await self._ensure_connection():
            return None
            
        try:
            cached_data = await self._async_client.get(cache_key)
            if not cached_data:
                return None
                
            document_data = json.loads(cached_data)
            logger.info(f"✅ Document retrieved from Redis (session: {session_id[:8]}...)")
            return document_data
            
        except Exception as error:
            logger.error(f"Redis document retrieval error: {error}")
            return None
    
    def _get_document_from_memory(self, cache_key: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Attempt to retrieve document from memory cache."""
        cache_entry = self._memory_cache.get(cache_key)
        if not cache_entry:
            return None
            
        if not self._is_memory_entry_valid(cache_entry):
            return None
            
        logger.info(f"✅ Document retrieved from memory (session: {session_id[:8]}...)")
        return cache_entry["data"]
    
    def _is_memory_entry_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if memory cache entry is still valid (not expired)."""
        expires_at = cache_entry.get("expires_at", 0)
        if expires_at <= 0:
            return False
            
        import time
        return time.time() < expires_at

    async def cache_document(
        self, session_id: str, document_data: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """
        Store document in cache for future retrieval.

        Args:
            session_id: Session identifier
            document_data: Document data to cache
            ttl: Time to live in seconds (defaults to 24 hours)

        Returns:
            True if successfully cached
        """
        if not self.cache_enabled:
            return False

        cache_key = self._build_document_cache_key(session_id)
        cache_ttl = ttl or self.documents_ttl
        
        # Attempt Redis caching first
        if await self._cache_document_to_redis(cache_key, document_data, cache_ttl, session_id):
            return True
        
        # Fall back to memory caching
        return self._cache_document_to_memory(cache_key, document_data, cache_ttl, session_id)
    
    async def _cache_document_to_redis(self, cache_key: str, document_data: Dict[str, Any], ttl: int, session_id: str) -> bool:
        """Attempt to cache document to Redis."""
        if not await self._ensure_connection():
            return False
            
        try:
            await self._async_client.setex(cache_key, ttl, json.dumps(document_data))
            ttl_hours = ttl / 3600
            logger.info(f"✅ Document cached to Redis (session: {session_id[:8]}..., TTL: {ttl}s / {ttl_hours:.1f}h)")
            return True
        except Exception as error:
            logger.error(f"Redis document caching error: {error}")
            return False
    
    def _cache_document_to_memory(self, cache_key: str, document_data: Dict[str, Any], ttl: int, session_id: str) -> bool:
        """Cache document to memory as fallback."""
        import time
        
        self._memory_cache[cache_key] = {
            "data": document_data,
            "expires_at": time.time() + ttl,
        }
        
        ttl_hours = ttl / 3600
        logger.info(f"✅ Document cached to memory (session: {session_id[:8]}..., TTL: {ttl}s / {ttl_hours:.1f}h)")
        return True

    async def invalidate_document(self, session_id: str) -> bool:
        """
        Remove cached document for a session.

        Args:
            session_id: Session identifier

        Returns:
            True if invalidation completed
        """
        if not self.cache_enabled:
            return False

        cache_key = self._build_document_cache_key(session_id)
        
        # Clear from Redis if available
        await self._invalidate_redis_document(cache_key, session_id)
        
        # Clear from memory cache
        self._invalidate_memory_document(cache_key, session_id)
        
        return True
    
    async def _invalidate_redis_document(self, cache_key: str, session_id: str) -> None:
        """Remove document from Redis cache."""
        if not await self._ensure_connection():
            return
            
        try:
            await self._async_client.delete(cache_key)
            logger.info(f"✅ Document invalidated in Redis (session: {session_id[:8]}...)")
        except Exception as error:
            logger.error(f"Redis invalidation error: {error}")
    
    def _invalidate_memory_document(self, cache_key: str, session_id: str) -> None:
        """Remove document from memory cache."""
        if cache_key in self._memory_cache:
            del self._memory_cache[cache_key]
            logger.info(f"✅ Document invalidated in memory (session: {session_id[:8]}...)")

    # === STATS & MANAGEMENT ===

    async def get_stats(self) -> Dict[str, Any]:
        """Retrieve comprehensive cache statistics."""
        stats = self._get_base_stats()
        
        # Add Redis statistics if available
        if await self._ensure_connection():
            redis_stats = await self._get_redis_stats()
            stats.update(redis_stats)
        
        return stats
    
    def _get_base_stats(self) -> Dict[str, Any]:
        """Get basic cache statistics."""
        return {
            "cache_enabled": self.cache_enabled,
            "redis_connected": self._is_connected,
            "memory_cache_entries": len(self._memory_cache),
            "ttl_questions_seconds": self.questions_ttl,
            "ttl_documents_seconds": self.documents_ttl,
        }
    
    async def _get_redis_stats(self) -> Dict[str, Any]:
        """Get Redis-specific statistics."""
        try:
            redis_info = await self._async_client.info()
            return {
                "redis_connected": True,
                "redis_used_memory": redis_info.get("used_memory_human", "N/A"),
                "redis_total_keys": await self._async_client.dbsize(),
                "redis_uptime_seconds": redis_info.get("uptime_in_seconds", 0),
            }
        except Exception as error:
            logger.error(f"Redis stats error: {error}")
            return {"redis_connected": False}

    async def clear_expired(self):
        """Remove expired entries from memory cache."""
        import time
        
        current_time = time.time()
        expired_keys = self._find_expired_keys(current_time)
        
        self._remove_expired_keys(expired_keys)
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired memory cache entries")
    
    def _find_expired_keys(self, current_time: float) -> List[str]:
        """Find all expired keys in memory cache."""
        expired_keys = []
        
        for key, entry in self._memory_cache.items():
            expires_at = entry.get("expires_at", 0)
            if expires_at > 0 and expires_at < current_time:
                expired_keys.append(key)
                
        return expired_keys
    
    def _remove_expired_keys(self, expired_keys: List[str]) -> None:
        """Remove expired keys from memory cache."""
        for key in expired_keys:
            del self._memory_cache[key]

    async def close(self):
        """Gracefully close Redis connection."""
        if self._async_client:
            await self._async_client.close()
            self._async_client = None
            self._is_connected = False
            logger.info("Redis connection closed gracefully")


# Singleton instance
_redis_cache: Optional[RedisCache] = None


def get_redis_cache() -> RedisCache:
    """Get or create Redis cache singleton."""
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = RedisCache()
    return _redis_cache
