# app/middleware/security.py
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
import logging
from app.config import settings

logger = logging.getLogger(__name__)

DOC_PATHS = {"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"}

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add comprehensive security headers to all responses, with relaxed CSP on docs."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        path = request.url.path

        # Commun headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        # Obsolète mais safe pour vieux navigateurs
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), "
            "microphone=(), payment=(), usb=()"
        )
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response.headers["Pragma"] = "no-cache"

        # HSTS uniquement en prod / HTTPS
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # CSP : relax pour la doc, strict ailleurs
        if path in DOC_PATHS:
            # Swagger/Redoc ont besoin de jsdelivr + fonts + inline styles
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com data:; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https: wss:; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "frame-ancestors 'none'"
            )
        else:
            # Politique plus stricte pour l’API
            csp = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self'; "
                "font-src 'self' data:; "
                "img-src 'self' data:; "
                "connect-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "frame-ancestors 'none'"
            )

        response.headers["Content-Security-Policy"] = csp

        return response
