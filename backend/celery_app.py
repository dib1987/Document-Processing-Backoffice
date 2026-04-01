from celery import Celery

from config import get_settings

settings = get_settings()

celery_app = Celery(
    "docflow",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["tasks.processing_pipeline"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,           # Re-queue if worker crashes mid-task
    worker_prefetch_multiplier=1,  # One task per worker at a time (document processing is heavy)
    task_routes={
        "tasks.processing_pipeline.process_document": {"queue": "documents"},
    },
)
