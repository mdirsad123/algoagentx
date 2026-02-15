#!/bin/bash

# Script to run Celery worker for background tasks

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Run Celery worker
celery -A app.celery_app worker --loglevel=info --concurrency=2
