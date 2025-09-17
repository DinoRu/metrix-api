import redis.asyncio as redis
from typing import Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)

redis_pool: Optional[redis.ConnectionPool] = None
redis_client: Optional[redis.Redis] = None


async def init_redis():
	"""Initialize Redis connection pool"""
	global redis_pool, redis_client

	try:
		redis_pool = redis.ConnectionPool.from_url(
			settings.REDIS_URL,
			max_connections=settings.REDIS_POOL_SIZE,
			decode_responses=True,
			health_check_interval=30
		)

		redis_client = redis.Redis(connection_pool=redis_pool)

		# Test connection
		await redis_client.ping()
		logger.info("✅ Redis connection pool initialized")

	except Exception as e:
		logger.error(f"❌ Failed to initialize Redis: {e}")
		raise


async def get_redis() -> redis.Redis:
	"""Get Redis client"""
	if not redis_client:
		await init_redis()
	return redis_client


async def close_redis():
	"""Close Redis connections"""
	global redis_pool, redis_client

	if redis_client:
		await redis_client.close()
		redis_client = None

	if redis_pool:
		await redis_pool.disconnect()
		redis_pool = None

	logger.info("Redis connections closed")


async def check_redis_connection() -> bool:
	"""Check if Redis is healthy"""
	try:
		client = await get_redis()
		await client.ping()
		return True
	except Exception as e:
		logger.error(f"Redis health check failed: {e}")
		return False