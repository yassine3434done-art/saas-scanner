import os
from celery import Celery

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "memory://")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "cache+memory://")
CELERY_EAGER = os.getenv("CELERY_EAGER", "1") == "1"

celery = Celery(
    "scanner",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.scans.tasks"],
)

celery.conf.task_always_eager = CELERY_EAGER
celery.conf.task_eager_propagates = True