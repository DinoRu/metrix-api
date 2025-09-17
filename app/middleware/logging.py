from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
import logging
import json
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
	"""Structured logging middleware for all requests"""

	async def dispatch(self, request: Request, call_next):
		# Start timer
		start_time = time.time()

		# Get request details
		request_body = None
		if request.method in ["POST", "PUT", "PATCH"]:
			try:
				request_body = await request.body()
				# Recreate request with body for downstream processing
				from starlette.requests import Request as StarletteRequest
				request = StarletteRequest(request.scope, receive=request._receive)
				request._body = request_body
			except:
				pass

		# Process request
		response = await call_next(request)

		# Calculate duration
		duration = time.time() - start_time

		# Create structured log
		log_dict = {
			"timestamp": datetime.utcnow().isoformat(),
			"level": "INFO",
			"request_id": getattr(request.state, "request_id", None),
			"method": request.method,
			"path": request.url.path,
			"query_params": dict(request.query_params),
			"client_host": request.client.host if request.client else None,
			"user_agent": request.headers.get("user-agent"),
			"status_code": response.status_code,
			"duration_seconds": round(duration, 3),
		}

		# Add user info if authenticated
		if hasattr(request.state, "user_id"):
			log_dict["user_id"] = request.state.user_id

		# Add error info for 4xx/5xx responses
		if response.status_code >= 400:
			log_dict["level"] = "WARNING" if response.status_code < 500 else "ERROR"

		# Log as JSON for structured logging systems
		logger.info(json.dumps(log_dict))

		# Add performance warning for slow requests
		if duration > 1.0:
			logger.warning(f"Slow request detected: {request.method} {request.url.path} took {duration:.2f}s")

		return response