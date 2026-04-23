from celery import Celery
from api.config import settings

celery_app = Celery(
    "company_lens",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["workers.tasks.pipeline"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    broker_connection_retry_on_startup=True,
)
