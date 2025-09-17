from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.core.redis import get_redis
from app.database import get_session
from sqlalchemy import select
import hashlib
import secrets
import logging

logger = logging.getLogger(__name__)


class APIKeyService:
	"""Service for managing API keys"""

	@staticmethod
	async def generate_api_key() -> str:
		"""Generate a new API key"""
		return f"msk_{secrets.token_urlsafe(32)}"

	@staticmethod
	async def hash_api_key(api_key: str) -> str:
		"""Hash API key for storage"""
		return hashlib.sha256(api_key.encode()).hexdigest()

	@staticmethod
	async def validate_api_key(api_key: str) -> bool:
		"""Validate an API key"""
		if not api_key or not api_key.startswith("msk_"):
			return False

		# Check cache first
		redis_client = await get_redis()
		cache_key = f"api_key:valid:{api_key[:8]}"  # Use prefix for privacy

		cached = await redis_client.get(cache_key)
		if cached is not None:
			return cached == "1"

		# Check database
		# This is a placeholder - implement based on your API key storage
		# For now, accept a test key in development
		from app.config import settings
		if settings.DEBUG and api_key == "msk_test_key_development_only":
			await redis_client.setex(cache_key, 300, "1")  # Cache for 5 minutes
			return True

		# In production, check against database
		# hashed_key = await APIKeyService.hash_api_key(api_key)
		# result = await db.execute(
		#     select(APIKey).where(APIKey.hashed_key == hashed_key, APIKey.is_active == True)
		# )
		# if result.scalar_one_or_none():
		#     await redis_client.setex(cache_key, 300, "1")
		#     return True

		await redis_client.setex(cache_key, 60, "0")  # Cache negative result for 1 minute
		return False


# Global instance
api_key_service = APIKeyService()


async def validate_api_key(api_key: str) -> bool:
	"""Global function for API key validation"""
	return await api_key_service.validate_api_key(api_key)