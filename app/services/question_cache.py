"""
Question Cache Service - Intelligent caching for generated questions.

Provides:
- In-memory cache with TTL
- Similarity-based lookup
- Pattern recognition
- Performance optimization
"""

import hashlib
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict

from app.models.api_models import Question
from app.utils.pii_safe_logging import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)


@dataclass
class CacheEntry:
    """Single cache entry with questions and metadata."""
    
    questions: List[Question]
    project_hash: str
    project_description: str
    created_at: float
    access_count: int
    last_accessed: float
    similarity_score: float = 0.0
    
    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if cache entry is expired."""
        return time.time() - self.created_at > ttl_seconds
    
    def touch(self):
        """Update access tracking."""
        self.access_count += 1
        self.last_accessed = time.time()


class QuestionCache:
    """
    Intelligent cache for generated questions.
    
    Features:
    - TTL-based expiration
    - Similarity matching
    - LRU eviction
    - Pattern learning
    """
    
    def __init__(
        self, 
        max_entries: int = 1000,
        ttl_seconds: int = 3600,  # 1 hour
        similarity_threshold: float = 0.7
    ):
        """
        Initialize question cache.
        
        Args:
            max_entries: Maximum cache entries
            ttl_seconds: Time-to-live for entries
            similarity_threshold: Minimum similarity for cache hits
        """
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self.similarity_threshold = similarity_threshold
        
        # Cache storage
        self.cache: Dict[str, CacheEntry] = {}
        self.keyword_index: Dict[str, List[str]] = defaultdict(list)
        
        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_requests": 0
        }
        
        logger.info("🧠 Question cache initialized", extra={
            "max_entries": max_entries,
            "ttl_seconds": ttl_seconds,
            "similarity_threshold": similarity_threshold
        })
    
    def _generate_project_hash(self, description: str) -> str:
        """Generate hash for project description."""
        # Normalize text for consistent hashing
        normalized = description.lower().strip()
        # Remove extra whitespace
        normalized = " ".join(normalized.split())
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]
    
    def _extract_keywords(self, description: str) -> List[str]:
        """Extract keywords from project description."""
        # Simple keyword extraction (can be improved with NLP)
        words = description.lower().split()
        
        # Filter out common words and keep meaningful ones
        stopwords = {
            'o', 'a', 'de', 'da', 'do', 'para', 'com', 'em', 'um', 'uma',
            'que', 'e', 'ou', 'se', 'por', 'no', 'na', 'dos', 'das',
            'system', 'sistema', 'preciso', 'quero', 'fazer', 'criar'
        }
        
        keywords = []
        for word in words:
            # Clean word
            clean_word = ''.join(char for char in word if char.isalnum())
            
            # Keep meaningful words (length > 3, not stopwords)
            if len(clean_word) > 3 and clean_word not in stopwords:
                keywords.append(clean_word)
        
        return keywords[:10]  # Limit to top 10 keywords
    
    def _calculate_similarity(self, desc1: str, desc2: str) -> float:
        """Calculate similarity between two project descriptions."""
        words1 = set(self._extract_keywords(desc1))
        words2 = set(self._extract_keywords(desc2))
        
        if not words1 and not words2:
            return 0.0
        if not words1 or not words2:
            return 0.0
        
        # Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _cleanup_expired(self):
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self.cache.items():
            if entry.is_expired(self.ttl_seconds):
                expired_keys.append(key)
        
        for key in expired_keys:
            self._remove_entry(key)
            
        if expired_keys:
            logger.debug(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")
    
    def _evict_lru(self):
        """Evict least recently used entries if cache is full."""
        if len(self.cache) < self.max_entries:
            return
        
        # Find least recently used entry
        lru_key = min(
            self.cache.keys(),
            key=lambda k: self.cache[k].last_accessed
        )
        
        self._remove_entry(lru_key)
        self.stats["evictions"] += 1
        
        logger.debug(f"🗑️ Evicted LRU cache entry: {lru_key}")
    
    def _remove_entry(self, key: str):
        """Remove cache entry and update indexes."""
        if key not in self.cache:
            return
        
        entry = self.cache[key]
        
        # Remove from keyword index
        keywords = self._extract_keywords(entry.project_description)
        for keyword in keywords:
            if key in self.keyword_index[keyword]:
                self.keyword_index[keyword].remove(key)
                # Clean up empty keyword lists
                if not self.keyword_index[keyword]:
                    del self.keyword_index[keyword]
        
        # Remove from main cache
        del self.cache[key]
    
    def get(self, project_description: str) -> Optional[List[Question]]:
        """
        Get cached questions for a project description.
        
        Args:
            project_description: Project description to look up
            
        Returns:
            Cached questions if found with sufficient similarity, None otherwise
        """
        self.stats["total_requests"] += 1
        
        # Clean up expired entries
        self._cleanup_expired()
        
        # Try exact hash match first
        project_hash = self._generate_project_hash(project_description)
        
        if project_hash in self.cache:
            entry = self.cache[project_hash]
            if not entry.is_expired(self.ttl_seconds):
                entry.touch()
                self.stats["hits"] += 1
                
                logger.info("🎯 Cache HIT (exact)", extra={
                    "project_hash": project_hash,
                    "access_count": entry.access_count,
                    "questions_count": len(entry.questions)
                })
                
                return entry.questions
        
        # Try similarity-based matching
        best_match = self._find_similar_entry(project_description)
        
        if best_match:
            entry, similarity = best_match
            entry.touch()
            entry.similarity_score = similarity
            self.stats["hits"] += 1
            
            logger.info("🎯 Cache HIT (similar)", extra={
                "similarity": similarity,
                "threshold": self.similarity_threshold,
                "questions_count": len(entry.questions)
            })
            
            return entry.questions
        
        # Cache miss
        self.stats["misses"] += 1
        logger.debug("❌ Cache MISS", extra={
            "project_hash": project_hash,
            "description_length": len(project_description)
        })
        
        return None
    
    def _find_similar_entry(self, description: str) -> Optional[Tuple[CacheEntry, float]]:
        """Find most similar cache entry."""
        keywords = self._extract_keywords(description)
        candidate_keys = set()
        
        # Find candidates based on keyword overlap
        for keyword in keywords:
            if keyword in self.keyword_index:
                candidate_keys.update(self.keyword_index[keyword])
        
        best_entry = None
        best_similarity = 0.0
        
        # Calculate similarity for candidates
        for key in candidate_keys:
            if key not in self.cache:
                continue
                
            entry = self.cache[key]
            if entry.is_expired(self.ttl_seconds):
                continue
            
            similarity = self._calculate_similarity(description, entry.project_description)
            
            if similarity > best_similarity and similarity >= self.similarity_threshold:
                best_similarity = similarity
                best_entry = entry
        
        return (best_entry, best_similarity) if best_entry else None
    
    def put(self, project_description: str, questions: List[Question]):
        """
        Cache questions for a project description.
        
        Args:
            project_description: Project description
            questions: Generated questions to cache
        """
        project_hash = self._generate_project_hash(project_description)
        
        # Evict LRU if necessary
        self._evict_lru()
        
        # Create cache entry
        entry = CacheEntry(
            questions=questions,
            project_hash=project_hash,
            project_description=project_description,
            created_at=time.time(),
            access_count=0,
            last_accessed=time.time()
        )
        
        # Store in cache
        self.cache[project_hash] = entry
        
        # Update keyword index
        keywords = self._extract_keywords(project_description)
        for keyword in keywords:
            self.keyword_index[keyword].append(project_hash)
        
        logger.info("💾 Questions cached", extra={
            "project_hash": project_hash,
            "questions_count": len(questions),
            "keywords": keywords[:5],  # Log first 5 keywords
            "cache_size": len(self.cache)
        })
    
    def invalidate(self, project_description: str = None):
        """
        Invalidate cache entries.
        
        Args:
            project_description: If provided, invalidate specific entry.
                               If None, clear entire cache.
        """
        if project_description:
            project_hash = self._generate_project_hash(project_description)
            self._remove_entry(project_hash)
            logger.info(f"🗑️ Invalidated cache entry: {project_hash}")
        else:
            self.cache.clear()
            self.keyword_index.clear()
            logger.info("🗑️ Cleared entire question cache")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats["total_requests"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_size": len(self.cache),
            "max_entries": self.max_entries,
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "evictions": self.stats["evictions"],
            "keyword_index_size": len(self.keyword_index),
            "ttl_seconds": self.ttl_seconds,
            "similarity_threshold": self.similarity_threshold
        }


# Global cache instance
_global_cache: Optional[QuestionCache] = None


def get_question_cache() -> QuestionCache:
    """Get global question cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = QuestionCache()
    return _global_cache


def clear_question_cache():
    """Clear global question cache."""
    global _global_cache
    if _global_cache:
        _global_cache.invalidate()
        _global_cache = None