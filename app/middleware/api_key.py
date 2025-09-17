from datetime import datetime

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, status
from fastapi.responses import JSONResponse
from typing import List
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class APIKeyMiddleware(BaseHTTPMiddleware):
	"""API Key authentication middleware for B2B access"""

	def __init__(self, app, exclude_paths: List[str] = None):
		super().__init__(app)
		self.exclude_paths = exclude_paths or []

	async def dispatch(self, request: Request, call_next):
		# Skip for excluded paths
		path = request.url.path
		if any(path.startswith(excluded) for excluded in self.exclude_paths):
			return await call_next(request)

		# Skip for health check endpoints
		if path in ["/health", "/ready", "/live", "/"]:
			return await call_next(request)

		# Check for API key
		api_key = request.headers.get("X-API-Key")
		if not api_key:
			api_key = request.query_params.get("api_key")

		# Validate API key
		if not api_key or not await self.validate_api_key(api_key):
			logger.warning(f"Invalid API key attempt from {request.client.host if request.client else 'unknown'}")
			return JSONResponse(
				status_code=status.HTTP_401_UNAUTHORIZED,
				content={
					"error": "Unauthorized",
					"message": "Invalid or missing API key",
					"timestamp": datetime.utcnow().isoformat()
				},
				headers={"WWW-Authenticate": 'ApiKey realm="API"'}
			)

		# Store API key info in request state
		request.state.api_key = api_key

		return await call_next(request)

	async def validate_api_key(self, api_key: str) -> bool:
		"""Validate API key against database or cache"""
		from app.services.api_key_service import validate_api_key
		return await validate_api_key(api_key)