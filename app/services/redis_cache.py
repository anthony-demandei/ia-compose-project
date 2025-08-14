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
    Redis cache service for questions and documents.
    
    Features:
    - Async Redis operations
    - TTL-based expiration
    - Fallback to in-memory cache
    - JSON serialization
    - Connection pooling
    """
    
    def __init__(self):
        """Initialize Redis cache with connection pool."""
        self.settings = get_settings()
        self._redis_client: Optional[aioredis.Redis] = None
        self._sync_redis_client: Optional[redis.Redis] = None
        self._memory_cache: Dict[str, Any] = {}  # Fallback cache
        self._connected = False
        
        # Cache settings
        self.questions_ttl = self.settings.redis_ttl_questions
        self.documents_ttl = self.settings.redis_ttl_documents
        self.enabled = self.settings.enable_redis_cache
        
        if self.enabled:
            self._init_connection()
    
    def _init_connection(self):
        """Initialize Redis connection pool with comprehensive configuration."""
        try:
            # Build connection parameters
            connection_params = self._build_connection_params()
            
            # Create connection pool for async operations
            self._redis_client = aioredis.Redis(**connection_params)
            
            # Create sync client for initialization checks
            sync_params = connection_params.copy()
            sync_params['socket_connect_timeout'] = self.settings.redis_connection_timeout
            self._sync_redis_client = redis.Redis(**sync_params)
            
            # Test connection
            self._sync_redis_client.ping()
            self._connected = True
            
            connection_info = self._get_connection_info()
            logger.info(f"✅ Redis cache connected: {connection_info}")
            
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed, using in-memory cache: {str(e)}")
            self._connected = False
    
    def _build_connection_params(self) -> Dict[str, Any]:
        """Build Redis connection parameters from settings."""
        # If Redis URL is provided, parse it
        if self.settings.redis_url:
            return {
                "url": self.settings.redis_url,
                "decode_responses": True,
                "max_connections": self.settings.redis_max_connections,
                "retry_on_timeout": self.settings.redis_retry_on_timeout,
                "health_check_interval": self.settings.redis_health_check_interval,
                "socket_timeout": self.settings.redis_socket_timeout
            }
        
        # Build from individual parameters
        params = {
            "host": self.settings.redis_host,
            "port": self.settings.redis_port,
            "db": self.settings.redis_db,
            "decode_responses": True,
            "max_connections": self.settings.redis_max_connections,
            "retry_on_timeout": self.settings.redis_retry_on_timeout,
            "health_check_interval": self.settings.redis_health_check_interval,
            "socket_timeout": self.settings.redis_socket_timeout
        }
        
        # Add authentication if provided
        if self.settings.redis_password:
            params["password"] = self.settings.redis_password
        
        if self.settings.redis_username:
            params["username"] = self.settings.redis_username
        
        # Add SSL configuration if enabled
        if self.settings.redis_ssl:
            params["ssl"] = True
            params["ssl_cert_reqs"] = self.settings.redis_ssl_cert_reqs
            
            if self.settings.redis_ssl_ca_certs:
                params["ssl_ca_certs"] = self.settings.redis_ssl_ca_certs
            if self.settings.redis_ssl_certfile:
                params["ssl_certfile"] = self.settings.redis_ssl_certfile
            if self.settings.redis_ssl_keyfile:
                params["ssl_keyfile"] = self.settings.redis_ssl_keyfile
        
        return params
    
    def _get_connection_info(self) -> str:
        """Get human-readable connection info for logging."""
        if self.settings.redis_url:
            # Parse URL for display (hide password)
            url_parts = self.settings.redis_url.split('@')
            if len(url_parts) > 1:
                return f"URL ending with @{url_parts[-1]}"
            return "Redis URL"
        
        ssl_info = " (SSL)" if self.settings.redis_ssl else ""
        return f"{self.settings.redis_host}:{self.settings.redis_port}/{self.settings.redis_db}{ssl_info}"
    
    async def _ensure_connection(self) -> bool:
        """Ensure Redis connection is active."""
        if not self.enabled:
            return False
            
        if self._connected and self._redis_client:
            try:
                await self._redis_client.ping()
                return True
            except (RedisError, ConnectionError):
                self._connected = False
                logger.warning("Redis connection lost, falling back to memory cache")
        
        return False
    
    def _generate_key(self, prefix: str, identifier: str) -> str:
        """Generate cache key with prefix."""
        return f"{prefix}:{identifier}"
    
    def _hash_project(self, project_description: str) -> str:
        """Generate hash for project description."""
        return hashlib.md5(project_description.encode()).hexdigest()
    
    # === QUESTIONS CACHE ===
    
    async def get_cached_questions(self, project_description: str) -> Optional[List[Question]]:
        """
        Get cached questions for a project description.
        
        Args:
            project_description: The project description to lookup
            
        Returns:
            List of Question objects if cached, None otherwise
        """
        if not self.enabled:
            return None
        
        project_hash = self._hash_project(project_description)
        cache_key = self._generate_key("questions", project_hash)
        
        # Try Redis first
        if await self._ensure_connection():
            try:
                cached_data = await self._redis_client.get(cache_key)
                if cached_data:
                    questions_data = json.loads(cached_data)
                    questions = [Question(**q) for q in questions_data]
                    logger.info(f"✅ Questions retrieved from Redis cache (key: {cache_key[:20]}...)")
                    return questions
            except Exception as e:
                logger.error(f"Error retrieving from Redis: {e}")
        
        # Fallback to memory cache
        if cache_key in self._memory_cache:
            cache_entry = self._memory_cache[cache_key]
            if cache_entry.get('expires_at', 0) > 0:  # Check if not expired
                import time
                if time.time() < cache_entry['expires_at']:
                    questions_data = cache_entry['data']
                    questions = [Question(**q) for q in questions_data]
                    logger.info(f"✅ Questions retrieved from memory cache (key: {cache_key[:20]}...)")
                    return questions
        
        return None
    
    async def cache_questions(
        self, 
        project_description: str, 
        questions: List[Question],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache questions for a project description.
        
        Args:
            project_description: The project description
            questions: List of Question objects to cache
            ttl: Optional TTL in seconds (defaults to config value)
            
        Returns:
            True if cached successfully
        """
        if not self.enabled:
            return False
        
        project_hash = self._hash_project(project_description)
        cache_key = self._generate_key("questions", project_hash)
        ttl = ttl or self.questions_ttl
        
        # Serialize questions
        questions_data = [q.dict() for q in questions]
        
        # Try Redis first
        if await self._ensure_connection():
            try:
                await self._redis_client.setex(
                    cache_key,
                    ttl,
                    json.dumps(questions_data)
                )
                logger.info(f"✅ Questions cached in Redis (key: {cache_key[:20]}..., TTL: {ttl}s)")
                return True
            except Exception as e:
                logger.error(f"Error caching to Redis: {e}")
        
        # Fallback to memory cache
        import time
        self._memory_cache[cache_key] = {
            'data': questions_data,
            'expires_at': time.time() + ttl
        }
        logger.info(f"✅ Questions cached in memory (key: {cache_key[:20]}..., TTL: {ttl}s)")
        return True
    
    # === DOCUMENTS CACHE ===
    
    async def get_cached_document(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached document for a session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            Document data if cached, None otherwise
        """
        if not self.enabled:
            return None
        
        cache_key = self._generate_key("doc", session_id)
        
        # Try Redis first
        if await self._ensure_connection():
            try:
                cached_data = await self._redis_client.get(cache_key)
                if cached_data:
                    document_data = json.loads(cached_data)
                    logger.info(f"✅ Document retrieved from Redis cache (session: {session_id[:8]}...)")
                    return document_data
            except Exception as e:
                logger.error(f"Error retrieving document from Redis: {e}")
        
        # Fallback to memory cache
        if cache_key in self._memory_cache:
            cache_entry = self._memory_cache[cache_key]
            if cache_entry.get('expires_at', 0) > 0:
                import time
                if time.time() < cache_entry['expires_at']:
                    logger.info(f"✅ Document retrieved from memory cache (session: {session_id[:8]}...)")
                    return cache_entry['data']
        
        return None
    
    async def cache_document(
        self,
        session_id: str,
        document_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache generated document for a session.
        
        Args:
            session_id: The session identifier
            document_data: The document data to cache
            ttl: Optional TTL in seconds (defaults to 24 hours)
            
        Returns:
            True if cached successfully
        """
        if not self.enabled:
            return False
        
        cache_key = self._generate_key("doc", session_id)
        ttl = ttl or self.documents_ttl
        
        # Try Redis first
        if await self._ensure_connection():
            try:
                await self._redis_client.setex(
                    cache_key,
                    ttl,
                    json.dumps(document_data)
                )
                logger.info(f"✅ Document cached in Redis (session: {session_id[:8]}..., TTL: {ttl}s / {ttl/3600:.1f}h)")
                return True
            except Exception as e:
                logger.error(f"Error caching document to Redis: {e}")
        
        # Fallback to memory cache
        import time
        self._memory_cache[cache_key] = {
            'data': document_data,
            'expires_at': time.time() + ttl
        }
        logger.info(f"✅ Document cached in memory (session: {session_id[:8]}..., TTL: {ttl}s / {ttl/3600:.1f}h)")
        return True
    
    async def invalidate_document(self, session_id: str) -> bool:
        """
        Invalidate cached document for a session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            True if invalidated successfully
        """
        if not self.enabled:
            return False
        
        cache_key = self._generate_key("doc", session_id)
        
        # Try Redis first
        if await self._ensure_connection():
            try:
                await self._redis_client.delete(cache_key)
                logger.info(f"✅ Document cache invalidated in Redis (session: {session_id[:8]}...)")
            except Exception as e:
                logger.error(f"Error invalidating in Redis: {e}")
        
        # Also remove from memory cache
        if cache_key in self._memory_cache:
            del self._memory_cache[cache_key]
            logger.info(f"✅ Document cache invalidated in memory (session: {session_id[:8]}...)")
        
        return True
    
    # === STATS & MANAGEMENT ===
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "enabled": self.enabled,
            "connected": self._connected,
            "memory_cache_size": len(self._memory_cache),
            "questions_ttl": self.questions_ttl,
            "documents_ttl": self.documents_ttl
        }
        
        if await self._ensure_connection():
            try:
                info = await self._redis_client.info()
                stats.update({
                    "redis_connected": True,
                    "redis_used_memory": info.get("used_memory_human", "N/A"),
                    "redis_keys": await self._redis_client.dbsize(),
                    "redis_uptime": info.get("uptime_in_seconds", 0)
                })
            except Exception as e:
                logger.error(f"Error getting Redis stats: {e}")
        
        return stats
    
    async def clear_expired(self):
        """Clear expired entries from memory cache."""
        import time
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._memory_cache.items()
            if entry.get('expires_at', 0) > 0 and entry['expires_at'] < current_time
        ]
        
        for key in expired_keys:
            del self._memory_cache[key]
        
        if expired_keys:
            logger.info(f"Cleared {len(expired_keys)} expired entries from memory cache")
    
    async def close(self):
        """Close Redis connection."""
        if self._redis_client:
            await self._redis_client.close()
            logger.info("Redis connection closed")


# Singleton instance
_redis_cache: Optional[RedisCache] = None


def get_redis_cache() -> RedisCache:
    """Get or create Redis cache singleton."""
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = RedisCache()
    return _redis_cache