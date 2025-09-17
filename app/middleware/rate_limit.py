import logging
import time
import redis.asyncio as redis

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis"""

    def __init__(self, app, calls: int = 60, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.redis_client = None

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for internal endpoints
        if request.url.path.startswith("/internal"):
            return await call_next(request)

        try:
            # Init Redis client
            if not self.redis_client:
                self.redis_client = await redis.from_url(settings.REDIS_URL)

            # Identifier client
            client_id = request.client.host if request.client else "unknown"

            # Rate limit key
            key = f"rate_limit:{client_id}:{request.url.path}"

            # Redis pipeline
            pipe = self.redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, self.period)
            result = await pipe.execute()
            request_count = result[0]

            # Trop de requêtes ?
            if request_count > self.calls:
                retry_after = await self.redis_client.ttl(key)
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Retry after {retry_after} seconds",
                        "retry_after": retry_after,
                    },
                    headers={
                        "X-RateLimit-Limit": str(self.calls),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(time.time()) + retry_after),
                        "Retry-After": str(retry_after),
                    }
                )

            # Sinon → passer la requête
            response = await call_next(request)

            # Ajouter headers
            remaining = max(0, self.calls - request_count)
            response.headers["X-RateLimit-Limit"] = str(self.calls)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.period)

            return response

        except Exception as e:
            logger.error(f"Rate limit middleware error: {e}")
            # Toujours renvoyer une réponse HTTP valide
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Internal server error (rate limit)"}
            )
