import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.monitoring.metrics import request_count, request_duration, active_requests
import time

logger = logging.getLogger(__name__)

async def monitoring_middleware(request: Request, call_next):
	"""Track request metrics"""
	start_time = time.time()

	response = await call_next(request)

	duration = time.time() - start_time

	# Record metrics
	request_count.labels(
		method=request.method,
		endpoint=request.url.path,
		status=response.status_code
	).inc()

	request_duration.labels(
		method=request.method,
		endpoint=request.url.path
	).observe(duration)

	return response


class MonitoringMiddleware(BaseHTTPMiddleware):
	"""Track request metrics for Prometheus"""

	async def dispatch(self, request: Request, call_next):
		# Skip metrics endpoint to avoid recursion
		if request.url.path == "/internal/metrics":
			return await call_next(request)

		# Track active requests
		active_requests.inc()

		# Start timer
		start_time = time.time()

		try:
			# Process request
			response = await call_next(request)

			# Record metrics
			duration = time.time() - start_time

			request_count.labels(
				method=request.method,
				endpoint=request.url.path,
				status=response.status_code
			).inc()

			request_duration.labels(
				method=request.method,
				endpoint=request.url.path
			).observe(duration)

			# Log slow requests
			if duration > 1.0:
				logger.warning(
					f"Slow request: {request.method} {request.url.path} "
					f"took {duration:.2f}s"
				)

			return response

		finally:
			active_requests.dec()