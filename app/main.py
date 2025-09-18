import logging
import sys
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings
from app.api.v1 import auth, meters, readings, photos, export, tasks, websocket, user, apk
from app.middleware.api_key import APIKeyMiddleware
from app.middleware.logging import LoggingMiddleware
from app.middleware.monitoring import MonitoringMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.security import SecurityHeadersMiddleware
from app.monitoring import metrics

# Configure logging
# logging.basicConfig(
#     level=logging.INFO if not settings.DEBUG else logging.DEBUG,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.StreamHandler(sys.stdout),
#         logging.FileHandler('logs/api.log') if not settings.DEBUG else logging.StreamHandler()
#     ]
# )

logger = logging.getLogger(__name__)

app = FastAPI(
    title="MeterSync API",
    description="""
    🚀 **MeterSync API** - Professional Meter Reading Management System

    ## Features
		* 🔐 **JWT Authentication** with role-based access control
		* 📊 **Offline-First Sync** with conflict resolution
		* 📸 **Photo Management** with S3 storage
		* 📈 **Real-time Updates** via WebSocket
		* 🔄 **Background Tasks** with Celery
		* 📝 **Excel Import/Export** with validation
		* 🌍 **Multi-language Support**
		* 📱 **Mobile-Optimized** endpoints

    ## Documentation
		* [Interactive API Docs](/docs)
		* [Alternative Docs](/redoc)
		* [Health Check](/health)
		* [Metrics](/metrics)

    ## Support
		* Email: support@metersync.com
		* Documentation: https://docs.metersync.com
    """,
    version="1.0.0",
    terms_of_service="https://metersync.com/terms",
    contact={
        "name": "MeterSync Support",
        "url": "https://metersync.com/support",
        "email": "support@metersync.com",
    },
    license_info={
        "name": "Commercial License",
        "url": "https://metersync.com/license",
    },
    openapi_tags=[
        {"name": "auth", "description": "Authentication operations"},
        {"name": "meters", "description": "Meter management"},
        {"name": "readings", "description": "Reading operations"},
        {"name": "photos", "description": "Photo management"},
        {"name": "export", "description": "Data export operations"},
        {"name": "tasks", "description": "Background task management"},
        {"name": "websocket", "description": "Real-time WebSocket connections"},
        {"name": "monitoring", "description": "System monitoring"},
    ],
    docs_url="/docs",
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else "/api/openapi.json",
)

# =====================================
# Request ID Middleware
# =====================================
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to track requests"""
    import uuid

    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    return response


# =====================================
# Process Time Middleware
# =====================================
@app.middleware("http")
async def add_process_time(request: Request, call_next):
    """Add request processing time to response headers"""
    import time

    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    response.headers["X-Process-Time"] = f"{process_time:.3f}s"

    return response


# =====================================
# Configure Middleware Stack
# =====================================

# GZIP Compression (minimum 1KB)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Session support
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.JWT_SECRET,
    https_only=not settings.DEBUG,
    same_site="strict"
)

# Trusted Host validation (production only)
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins= ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=[
        "X-Request-ID",
        "X-Process-Time",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "X-API-Version",
    ],
    max_age=3600,
)

# Custom middleware
app.add_middleware(MonitoringMiddleware)
# app.add_middleware(RateLimitMiddleware, calls=settings.RATE_LIMIT_PER_MINUTE, period=60)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)

# API Key middleware for specific endpoints (optional)
if settings.REQUIRE_API_KEY:
    app.add_middleware(APIKeyMiddleware, exclude_paths=["/docs", "/redoc", "/openapi.json"])

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["auth"])
app.include_router(user.router, prefix=f"{settings.API_V1_PREFIX}/user", tags=["users"])
app.include_router(meters.router, prefix=f"{settings.API_V1_PREFIX}/meters", tags=["meters"])
app.include_router(readings.router, prefix=f"{settings.API_V1_PREFIX}/readings", tags=["readings"])
app.include_router(photos.router, prefix=f"{settings.API_V1_PREFIX}/photos", tags=["photos"])
app.include_router(export.router, prefix=f"{settings.API_V1_PREFIX}/export", tags=["export"])
app.include_router(tasks.router, prefix=f"{settings.API_V1_PREFIX}/tasks", tags=["tasks"])
app.include_router(apk.router, prefix=f"{settings.API_V1_PREFIX}/apk", tags=["apk"])
app.include_router(websocket.router, prefix=f"{settings.API_V1_PREFIX}/ws", tags=["websocket"])
# app.include_router(metrics.router, tags=["monitoring"])

# Monitoring endpoints (internal use)
if settings.EXPOSE_METRICS:
    app.include_router(
        metrics.router,
        prefix="/internal",
        tags=["monitoring"]
    )

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }