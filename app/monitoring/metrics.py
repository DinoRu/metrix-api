from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

import redis

from app.config import settings

r = redis.Redis.from_url(settings.REDIS_URL)

router = APIRouter()

# Define metrics
request_count = Counter(
	'http_requests_total',
	'Total HTTP requests',
	['method', 'endpoint', 'status']
)

request_duration = Histogram(
	'http_request_duration_seconds',
	'HTTP request duration',
	['method', 'endpoint'],
	buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

active_requests = Gauge(
	'http_requests_active',
	'Number of active HTTP requests'
)

active_users = Gauge(
	'active_users',
	'Number of active users'
)

task_queue_size = Gauge(
	'celery_task_queue_size',
	'Size of Celery task queue',
	['queue_name']
)

sync_operations = Counter(
	'sync_operations_total',
	'Total sync operations',
	['status']
)

database_connections = Gauge(
	'database_connections_active',
	'Active database connections'
)

redis_connections = Gauge(
	'redis_connections_active',
	'Active Redis connections'
)


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics():
	"""Prometheus metrics endpoint"""
	# Update dynamic metrics
	try:
		from app.core.celery_app import celery_app
		inspector = celery_app.control.inspect()
		stats = inspector.stats()

		if stats:
			for worker, info in stats.items():
				if 'total' in info:
					task_queue_size.labels(queue_name='default').set(info.get('total', 0))
	except:
		pass

	return generate_latest()