#!/bin/bash

# Script to run Celery worker for background tasks.
# Keep production quiet by default; set CELERY_LOG_LEVEL=debug when diagnosing.

export PYTHONPATH="${PYTHONPATH}:$(pwd)"

celery -A app.celery_app worker --loglevel="${CELERY_LOG_LEVEL:-error}" --concurrency=2
