"""Celery minimo del encargo 0.3: solo existe para que el worker arranque y responda ping.

Las tres colas separadas (interactiva, ingesta, evals) con sus prioridades son el encargo 2.3.
Aqui no hay ninguna: un broker, una tarea de humo y nada mas.
"""
import os

from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery("veridica", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(
    task_default_queue="interactiva",
    broker_connection_retry_on_startup=True,
    worker_send_task_events=False,
)


@celery_app.task(name="veridica.ping")
def ping() -> str:
    return "pong"
