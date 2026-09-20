# AlgoAgentX development runtime fix — 2026-09-20

## What the startup log actually means

There are two separate messages:

1. `razorpay/client.py ... pkg_resources is deprecated`
   - This is a dependency warning, not the reason the API database startup check fails.
   - `requirements.txt` previously pinned the very old `razorpay==1.2.0`.
   - It is now updated to `razorpay==2.0.1`, whose current client uses modern package metadata handling.

2. `Connect call failed ('127.0.0.1', 5433)`
   - This is the real runtime problem.
   - `.env` points to PostgreSQL on `localhost:5433`.
   - Nothing was listening on that port.
   - `docker-compose.dev.yml` now provides PostgreSQL 16 on host port 5433 and Redis 7 on host port 6380, matching the existing `.env`.

## First-time / updated setup on Windows

From the API folder:

```bat
.venv\Scripts\activate
python -m pip install -U pip
pip install -r requirements.txt
scripts\start_dev_services.bat
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or start the services directly:

```bat
docker compose -f docker-compose.dev.yml up -d
```

Check them:

```bat
docker compose -f docker-compose.dev.yml ps
```

Expected:
- PostgreSQL container is healthy and maps `5433 -> 5432`.
- Redis container is healthy and maps `6380 -> 6379`.

## Existing local PostgreSQL alternative

If you already run PostgreSQL directly on Windows on port 5432, do not start the Docker PostgreSQL service. Instead change:

```env
DATABASE_URL=postgresql+asyncpg://algoagentx_user:dev_password@localhost:5432/algoagentx_dev
```

and make sure that user/database actually exist.

## Important

The FastAPI code already intentionally continues in development if PostgreSQL is unavailable, but database-backed endpoints will fail. The correct fix is to make the database available at the address configured by `DATABASE_URL`, not to suppress the database error.
