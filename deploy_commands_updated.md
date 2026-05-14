# AlgoAgentX Docker Restart Commands

Use these commands from the project root:

```bash
cd D:\Stock_market\algoagentx
```

## 1. Restart API only

Use this when you changed only backend/API code or API `.env.prod` values.

```bash
docker compose --env-file .env.prod up -d --build api
```

Check API status:

```bash
docker compose --env-file .env.prod ps
curl http://localhost:8000/health
```

Check API logs:

```bash
docker compose --env-file .env.prod logs -f api
```

## 2. Restart Web/App only

Use this when you changed only frontend/app code or `NEXT_PUBLIC_*` values.

```bash
docker compose --env-file .env.prod up -d --build web
```

Check web status:

```bash
docker compose --env-file .env.prod ps
curl http://localhost:3000
```

Check web logs:

```bash
docker compose --env-file .env.prod logs -f web
```

## 3. Restart API and Web together

Use this when both backend and frontend changed.

```bash
docker compose --env-file .env.prod up -d --build api web
```

Check all running services:

```bash
docker compose --env-file .env.prod ps
```

## 4. Restart without rebuild

Use this when code did not change and you only want to restart running containers.

```bash
docker compose --env-file .env.prod restart api web
```

## 5. Run DB migrations only when needed

Use this only after backend migration files changed or database schema needs updating.

```bash
docker compose --env-file .env.prod exec api alembic upgrade head
```

## 6. Full app status check

```bash
docker compose --env-file .env.prod ps
curl http://localhost:8000/health
curl http://localhost:3000
```

## 7. stop both 
docker compose --env-file .env.prod stop api web

# To start again:
docker compose --env-file .env.prod up -d api web

# To remove only API + Web containers but keep Postgres/Redis running:
docker compose --env-file .env.prod rm -sf api web

# To stop everything: API, Web, Postgres, Redis:
docker compose --env-file .env.prod down

## Restart only API + Web after .env.prod change

cd D:\Stock_market\algoagentx

docker compose --env-file .env.prod stop api web
docker compose --env-file .env.prod rm -sf api web
docker compose --env-file .env.prod up -d api web

# if you want to start dev database
docker stop algoagentx_postgres
docker start algoagentx_postgres

## If .env.prod changed NEXT_PUBLIC_* frontend values and also if changes in code page or api
# Use build for web, because Next.js frontend env is baked during build:

cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod stop api web
docker compose --env-file .env.prod rm -sf api web
docker compose --env-file .env.prod up -d --build api web