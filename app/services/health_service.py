# app/services/health_service.py
from typing import Dict, Any
from datetime import datetime, timezone
import psutil
import platform
from app.database import check_db_connection
from app.core.redis import check_redis_connection
from app.services.storage_service import storage_service
from app.core.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)

async def get_detailed_health() -> Dict[str, Any]:
    """Get detailed health status of all services"""
    health_status = {
        "services": {},
        "system": {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # DB
    try:
        db_healthy = await check_db_connection()
        health_status["services"]["database"] = {
            "healthy": db_healthy,
            "type": "PostgreSQL",
            "status": "connected" if db_healthy else "disconnected",
        }
    except Exception as e:
        health_status["services"]["database"] = {"healthy": False, "error": str(e)}

    # Redis
    try:
        redis_healthy = await check_redis_connection()
        health_status["services"]["redis"] = {
            "healthy": redis_healthy,
            "type": "Redis",
            "status": "connected" if redis_healthy else "disconnected",
        }
    except Exception as e:
        health_status["services"]["redis"] = {"healthy": False, "error": str(e)}

    # S3
    try:
        s3_healthy = await storage_service.check_connection()
        health_status["services"]["s3"] = {
            "healthy": s3_healthy,
            "type": "S3-compatible",
            "bucket": storage_service.bucket,
            "status": "connected" if s3_healthy else "disconnected",
        }
    except Exception as e:
        health_status["services"]["s3"] = {"healthy": False, "error": str(e)}

    # Celery
    try:
        inspector = celery_app.control.inspect()
        stats = inspector.stats() if inspector else None
        active_workers = list(stats.keys()) if stats else []
        health_status["services"]["celery"] = {
            "healthy": bool(active_workers),
            "workers": active_workers,
            "count": len(active_workers),
        }
    except Exception as e:
        health_status["services"]["celery"] = {"healthy": False, "error": str(e)}

    # System
    try:
        health_status["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "uptime_seconds": datetime.now(timezone.utc).timestamp() - psutil.boot_time(),
        }
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")

    # Overall
    all_services_healthy = all(s.get("healthy", False) for s in health_status["services"].values())
    health_status["overall_health"] = "healthy" if all_services_healthy else "degraded"

    return health_status
