"""
Celery configuration for order processing tasks
Redis broker: Local development uses redis://localhost:6379
Production will use Azure Redis Cache
"""

import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Initialize Celery app
celery_app = Celery(
    'order_processing',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0')
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task

    # Resilience settings - ensure tasks survive worker restarts
    task_acks_late=True,  # Acknowledge task AFTER completion, not before
    task_reject_on_worker_lost=True,  # Re-queue task if worker dies unexpectedly
    worker_prefetch_multiplier=1,  # Only fetch 1 task at a time (prevents task loss)
    broker_transport_options={
        'visibility_timeout': 7200,  # 2 hours - must be > task_time_limit
    },
)

# Import task modules to register them with Celery (avoids circular import)
from backend.tasks import task_fetch_emails, task_extract_emails, task_extract_data, task_tidy_emails

