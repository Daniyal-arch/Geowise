"""
GEOWISE Redis Caching Layer
Cache expensive spatial computations and API results
"""

from typing import Optional, Any, List
import json
import hashlib
from datetime import timedelta

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)


class CacheManager:
    """Redis cache manager for spatial data."""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self.client: Optional[redis.Redis] = None
        self.enabled = REDIS_AVAILABLE
        
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available - caching disabled")
    
    async def connect(self):
        """Connect to Redis."""
        if not self.enabled:
            return
        
        try:
            self.client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.client.ping()
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self.enabled = False
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.client:
            await self.client.close()
    
    @staticmethod
    def _generate_key(prefix: str, params: dict) -> str:
        """Generate cache key from parameters."""
        param_str = json.dumps(params, sort_keys=True)
        hash_str = hashlib.md5(param_str.encode()).hexdigest()
        return f"{prefix}:{hash_str}"
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.enabled or not self.client:
            return None
        
        try:
            value = await self.client.get(key)
            if value:
                logger.debug(f"Cache hit: {key}")
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache with TTL."""
        if not self.enabled or not self.client:
            return False
        
        try:
            ttl = ttl or settings.CACHE_TTL
            value_json = json.dumps(value)
            await self.client.setex(key, ttl, value_json)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.enabled or not self.client:
            return False
        
        try:
            await self.client.delete(key)
            logger.debug(f"Cache delete: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def get_fire_query(self, params: dict) -> Optional[List[dict]]:
        """Get cached fire query results."""
        key = self._generate_key("fires:query", params)
        return await self.get(key)
    
    async def set_fire_query(self, params: dict, data: List[dict], ttl: int = 3600) -> bool:
        """Cache fire query results."""
        key = self._generate_key("fires:query", params)
        return await self.set(key, data, ttl)
    
    async def get_aggregation(self, params: dict) -> Optional[List[dict]]:
        """Get cached aggregation results."""
        key = self._generate_key("fires:aggregation", params)
        return await self.get(key)
    
    async def set_aggregation(self, params: dict, data: List[dict], ttl: int = 7200) -> bool:
        """Cache aggregation results."""
        key = self._generate_key("fires:aggregation", params)
        return await self.set(key, data, ttl)
    
    async def get_correlation(self, params: dict) -> Optional[dict]:
        """Get cached correlation analysis."""
        key = self._generate_key("analysis:correlation", params)
        return await self.get(key)
    
    async def set_correlation(self, params: dict, data: dict, ttl: int = 86400) -> bool:
        """Cache correlation analysis (24h TTL)."""
        key = self._generate_key("analysis:correlation", params)
        return await self.set(key, data, ttl)


cache_manager = CacheManager()