from celery import Celery
from celery.schedules import crontab
from kombu import Queue, Exchange
from app.core.config import settings

celery = Celery(
    "mpcars2",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Fortaleza",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3000,
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    result_expires=86400,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
    worker_concurrency=4,
)

celery.conf.task_queues = [
    Queue(
        "default",
        Exchange("default"),
        routing_key="default",
        max_priority=10,
    ),
    Queue(
        "high_priority",
        Exchange("high_priority"),
        routing_key="high_priority",
        priority=10,
    ),
    Queue(
        "low_priority",
        Exchange("low_priority"),
        routing_key="low_priority",
        priority=1,
    ),
    Queue(
        "pdf_generation",
        Exchange("pdf_generation"),
        routing_key="pdf_generation",
        priority=5,
    ),
    Queue(
        "email",
        Exchange("email"),
        routing_key="email",
        priority=3,
    ),
    Queue(
        "backup",
        Exchange("backup"),
        routing_key="backup",
        priority=1,
    ),
]

celery.conf.task_routes = {
    "app.tasks.alertas.*": {"queue": "high_priority"},
    "app.tasks.pdf.*": {"queue": "pdf_generation"},
    "app.tasks.email.*": {"queue": "email"},
    "app.tasks.backup.*": {"queue": "low_priority"},
}

celery.conf.beat_schedule = {
    "gerar-alertas-diarios": {
        "task": "app.tasks.alertas.gerar_alertas_diarios",
        "schedule": crontab(hour=7, minute=0),
    },
    "limpar-cache-antigo": {
        "task": "app.tasks.maintenance.limpar_cache",
        "schedule": crontab(hour=3, minute=0),
    },
    "verificar-contratos-expirando": {
        "task": "app.tasks.alertas.verificar_contratos_expirando",
        "schedule": crontab(minute=0, hour="*/1"),
    },
    "backup-diario": {
        "task": "app.tasks.backup.executar_backup",
        "schedule": crontab(hour=2, minute=0),
    },
}

celery.autodiscover_tasks(["app.tasks", "app.tasks.alertas", "app.tasks.maintenance", "app.tasks.backup"])


@celery.task(bind=True, max_retries=3)
def health_check(self):
    """Health check task for monitoring."""
    return {"status": "healthy", "worker": self.request.hostname}
