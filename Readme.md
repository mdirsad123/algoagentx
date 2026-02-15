uvicorn app.main:app --reload --host 0.0.0.0 --port 8000


docker run -d -p 6379:6379 --name algoagentx-redis redis:alpine

The API is now running successfully! You can access it at:

Root endpoint: http://localhost:8000/
Health check: http://localhost:8000/health
API docs: http://localhost:8000/docs

alembic revision --autogenerate -m "Initial migration"

test login:
test@example.com
password123