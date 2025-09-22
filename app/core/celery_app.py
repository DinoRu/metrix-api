# app/core/celery_app.py
from celery import Celery
from app.config import settings

celery_app = Celery(
    "metersync",
    broker=settings.REDIS_URL if settings.DEBUG else settings.PRO_REDIS_URL,
    backend=settings.REDIS_URL if settings.DEBUG else settings.PRO_REDIS_URL,
)

# Bonnes pratiques Celery
celery_app.conf.update(
    task_time_limit=60*30,          # 30 min hard limit
    task_soft_time_limit=60*25,     # soft limit
    worker_max_tasks_per_child=100, # recycle pour éviter leaks
    worker_prefetch_multiplier=1,   # pas de sur-prélecture
    result_expires=3600,            # 1h
    task_track_started=True,
    include=["app.tasks.meter_import"],
)

celery_app.autodiscover_tasks(["celery_app"])
