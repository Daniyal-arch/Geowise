"""
Base service class for external API integrations.

Provides:
- Async HTTP client with connection pooling
- Exponential backoff retry logic
- Rate limiting
- Response caching
- Structured error logging
- Timeout handling
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
import asyncio
from datetime import datetime, timedelta
import hashlib
import json

import aiohttp
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.utils.logger import get_logger
from app.utils.exceptions import (
    ExternalAPIError,
    RateLimitExceededError,
    APITimeoutError,
)

logger = get_logger(__name__)


class BaseService(ABC):
    """
    Base class for external API services.
    
    Features:
    - Async HTTP with connection pooling (100 connections max)
    - Exponential backoff: 3 attempts with 1s → 2s → 4s delays
    - Rate limiting: Configurable requests per second
    - In-memory caching with TTL
    - Automatic timeout handling (30s default)
    - Structured error logging with context
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        rate_limit_per_second: float = 10.0,
        cache_ttl_seconds: int = 300,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.rate_limit_per_second = rate_limit_per_second
        self.cache_ttl_seconds = cache_ttl_seconds

        self._session: Optional[aiohttp.ClientSession] = None
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._rate_limiter = asyncio.Semaphore(int(rate_limit_per_second))
        self._last_request_time = 0.0

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self):
        """Initialize HTTP session with connection pooling."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
            )
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout,
                raise_for_status=False,
            )
            logger.info(
                f"HTTP session created for {self.__class__.__name__}",
                extra={"base_url": self.base_url},
            )

    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info(f"HTTP session closed for {self.__class__.__name__}")

    def _get_cache_key(self, url: str, params: Optional[Dict] = None) -> str:
        """Generate cache key from URL and parameters."""
        cache_str = f"{url}:{json.dumps(params, sort_keys=True) if params else ''}"
        return hashlib.md5(cache_str.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Retrieve value from cache if not expired."""
        if cache_key in self._cache:
            value, expires_at = self._cache[cache_key]
            if datetime.utcnow() < expires_at:
                logger.debug(f"Cache hit: {cache_key[:8]}...")
                return value
            else:
                del self._cache[cache_key]
                logger.debug(f"Cache expired: {cache_key[:8]}...")
        return None

    def _set_cache(self, cache_key: str, value: Any):
        """Store value in cache with TTL."""
        expires_at = datetime.utcnow() + timedelta(seconds=self.cache_ttl_seconds)
        self._cache[cache_key] = (value, expires_at)
        logger.debug(
            f"Cache set: {cache_key[:8]}...",
            extra={"ttl_seconds": self.cache_ttl_seconds},
        )

    async def _wait_for_rate_limit(self):
        """Enforce rate limiting between requests."""
        async with self._rate_limiter:
            now = asyncio.get_event_loop().time()
            time_since_last = now - self._last_request_time
            min_interval = 1.0 / self.rate_limit_per_second

            if time_since_last < min_interval:
                await asyncio.sleep(min_interval - time_since_last)

            self._last_request_time = asyncio.get_event_loop().time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True,
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        use_cache: bool = True,
    ) -> Union[Dict, str, bytes]:
        """
        Make HTTP request with retry logic and caching.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (will be appended to base_url)
            params: Query parameters
            json_data: JSON body for POST/PUT
            headers: Additional headers
            use_cache: Whether to use caching (only for GET)
            
        Returns:
            Response data (dict for JSON, str for text, bytes for binary)
            
        Raises:
            ExternalAPIError: API returned error response
            APITimeoutError: Request timed out
            RateLimitExceededError: Rate limit exceeded
        """
        await self.connect()

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        cache_key = self._get_cache_key(url, params) if use_cache and method == "GET" else None

        if cache_key:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached

        await self._wait_for_rate_limit()

        request_headers = headers or {}
        if self.api_key:
            request_headers["Authorization"] = f"Bearer {self.api_key}"

        logger.debug(
            f"Making {method} request",
            extra={
                "url": url,
                "params": params,
                "has_body": json_data is not None,
            },
        )

        try:
            async with self._session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=request_headers,
            ) as response:
                if response.status == 429:
                    logger.warning(f"Rate limit exceeded for {url}")
                    raise RateLimitExceededError(
                        f"Rate limit exceeded for {self.__class__.__name__}",
                        service_name=self.__class__.__name__,
                    )

                if response.status >= 400:
                    error_text = await response.text()
                    logger.error(
                        f"API error {response.status}",
                        extra={
                            "url": url,
                            "status": response.status,
                            "response": error_text[:500],
                        },
                    )
                    raise ExternalAPIError(
                        f"API returned {response.status}: {error_text[:200]}",
                        status_code=response.status,
                        service_name=self.__class__.__name__,
                        response_body=error_text,
                    )

                content_type = response.headers.get("Content-Type", "")

                if "application/json" in content_type:
                    data = await response.json()
                elif "text/" in content_type or "csv" in content_type:
                    data = await response.text()
                else:
                    data = await response.read()

                logger.info(
                    f"Request successful: {method} {url}",
                    extra={
                        "status": response.status,
                        "content_type": content_type,
                    },
                )

                if cache_key:
                    self._set_cache(cache_key, data)

                return data

        except asyncio.TimeoutError as e:
            logger.error(f"Request timeout: {url}", extra={"timeout": self.timeout.total})
            raise APITimeoutError(
                f"Request to {url} timed out after {self.timeout.total}s",
                service_name=self.__class__.__name__,
            ) from e

        except aiohttp.ClientError as e:
            logger.error(
                f"HTTP client error: {url}",
                extra={"error": str(e)},
            )
            raise ExternalAPIError(
                f"HTTP client error: {str(e)}",
                service_name=self.__class__.__name__,
            ) from e

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        use_cache: bool = True,
    ) -> Union[Dict, str, bytes]:
        """Make GET request."""
        return await self._make_request("GET", endpoint, params=params, use_cache=use_cache)

    async def post(
        self,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Union[Dict, str, bytes]:
        """Make POST request."""
        return await self._make_request("POST", endpoint, params=params, json_data=json_data)

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the external service is available.
        
        Returns:
            True if service is healthy, False otherwise
        """
        pass