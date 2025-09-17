from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
import uuid
import contextvars
import logging

# Context variable to store request ID
request_id_context = contextvars.ContextVar("request_id", default=None)

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
	"""Generate and track unique request IDs"""

	async def dispatch(self, request: Request, call_next):
		# Get or generate request ID
		request_id = request.headers.get("X-Request-ID")
		if not request_id:
			request_id = str(uuid.uuid4())

		# Store in request state and context
		request.state.request_id = request_id
		request_id_context.set(request_id)

		# Add to logging context
		logger.info(f"Request started: {request.method} {request.url.path} [{request_id}]")

		# Process request
		response = await call_next(request)

		# Add request ID to response headers
		response.headers["X-Request-ID"] = request_id
		response.headers["X-Correlation-ID"] = request_id

		logger.info(f"Request completed: {request.method} {request.url.path} [{request_id}] - {response.status_code}")

		return response


def get_request_id() -> str:
	"""Get current request ID from context"""
	return request_id_context.get() or "unknown"