# AlgoAgentX Deploy Commands

# 2. Production commands

## 2.1 Start all production services

Use this when you want to start production API, web, postgres, redis, and other services defined in `docker-compose.yml`.

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod -f docker-compose.yml up -d
```

Check status:

```powershell
docker compose --env-file .env.prod -f docker-compose.yml ps
```

---

## 2.2 Stop all production services

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod -f docker-compose.yml stop
```

---

## 2.3 Stop and remove all production services

This stops and removes containers, but keeps Docker volumes unless you add `-v`.

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod -f docker-compose.yml down -v
```

Do **not** use `down -v` unless you intentionally want to delete database volume data.

---

# 3. Production API/Web deploy and rebuild

## 3.1 Production rebuild/deploy API + Web

Use this when code changed in backend/API or frontend/Web.

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod stop api web
docker compose --env-file .env.prod rm -sf api web
docker compose --env-file .env.prod up -d --build api web
```

Use this especially when:

```txt
Backend code changed
Frontend code changed
NEXT_PUBLIC_* frontend env changed
Dockerfile changed
Package dependencies changed
```

---

## 3.2 Production restart API + Web without rebuild

Use this when code did not change and you only want to restart containers.

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod stop api web
docker compose --env-file .env.prod rm -sf api web
docker compose --env-file .env.prod up -d api web
```

Use this when:

```txt
Only runtime env changed
Container needs clean restart
API/Web got stuck
```

---

## 3.3 Production rebuild API only

Use this when only backend/API code changed.

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod up -d --build api
```

Check API:

```powershell
docker compose --env-file .env.prod ps api
curl http://localhost:8000/health
```

View API logs:

```powershell
docker compose --env-file .env.prod logs -f api
```

---

## 3.4 Production rebuild Web only

Use this when only frontend/App code changed.

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod up -d --build web
```

Check Web:

```powershell
docker compose --env-file .env.prod ps web
curl http://localhost:3000
```

View Web logs:

```powershell
docker compose --env-file .env.prod logs -f web
```

---

## 3.5 Production restart API/Web only

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod restart api web
```

---

# 4. Production logs

## 4.1 API logs

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod logs -f api
```

## 4.2 Web logs

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod logs -f web
```

## 4.3 Postgres logs

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod logs -f postgres
```

## 4.4 Redis logs

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod logs -f redis
```

## 4.5 All production logs

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod logs -f
```

---

# 5. Production health checks

## 5.1 Check running containers

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod ps
```

## 5.2 Check API health

```powershell
curl http://localhost:8000/health
```

## 5.3 Check Web

```powershell
curl http://localhost:3000
```

# 8. Development database commands

## 8.1 Start DEV PostgreSQL only

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.dev -f docker-compose.dev.yml up -d postgres_dev
```

## 8.2 Stop DEV PostgreSQL only

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.dev -f docker-compose.dev.yml stop postgres_dev
```

## 8.3 Restart DEV PostgreSQL only

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.dev -f docker-compose.dev.yml restart postgres_dev
```

## 8.4 Remove DEV PostgreSQL container but keep volume

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.dev -f docker-compose.dev.yml rm -sf postgres_dev
```

## 8.5 Start DEV PostgreSQL again after remove

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.dev -f docker-compose.dev.yml up -d postgres_dev
```

## 8.6 Check DEV PostgreSQL status

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.dev -f docker-compose.dev.yml ps
```

## 8.7 Check DEV PostgreSQL logs

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.dev -f docker-compose.dev.yml logs -f postgres
```

## 8.8 Connect DEV PostgreSQL from terminal

```powershell
docker exec -it algoagentx_postgres_dev psql -U algoagentx_user -d algoagentx_dev
```

## 8.9 Check DEV PostgreSQL version

```powershell
docker exec -it algoagentx_postgres_dev psql -U algoagentx_user -d algoagentx_dev -c "SELECT version();"
```

## 8.10 List DEV database tables

```powershell
docker exec -it algoagentx_postgres_dev psql -U algoagentx_user -d algoagentx_dev -c "\dt"
```

---

# 9. Restore production backup into development database

## 9.1 Start dev database

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.dev -f docker-compose.dev.yml up -d postgres
```

## 9.2 Copy production backup into dev container

```powershell
docker cp D:\Stock_market\algoagentx\AlgoAgentXAPI\backup_db\algoagentx_prod_backup_15_may.dump algoagentx_postgres_dev:/tmp/algoagentx_prod_backup_15_may.dump
```

## 9.3 Restore backup into dev database

```powershell
docker exec -it algoagentx_postgres_dev pg_restore -U algoagentx_user -d algoagentx_dev --clean --if-exists --no-owner --no-privileges -v /tmp/algoagentx_prod_backup_15_may.dump
```

## 9.4 Verify restore

```powershell
docker exec -it algoagentx_postgres_dev psql -U algoagentx_user -d algoagentx_dev -c "\dt"
```

Optional counts:

```powershell
docker exec -it algoagentx_postgres_dev psql -U algoagentx_user -d algoagentx_dev -c "SELECT COUNT(*) FROM users;"
docker exec -it algoagentx_postgres_dev psql -U algoagentx_user -d algoagentx_dev -c "SELECT COUNT(*) FROM strategies;"
docker exec -it algoagentx_postgres_dev psql -U algoagentx_user -d algoagentx_dev -c "SELECT COUNT(*) FROM backtest_results;"
```

If a table name does not exist, use your actual table name.

---

# 10. Development API local run

Use this when running FastAPI from Windows, not Docker.

## 10.1 API `.env` should point to dev DB

File:

```txt
D:\Stock_market\algoagentx\AlgoAgentXAPI\.env
```

Database URL:

```env
DATABASE_URL=postgresql+asyncpg://algoagentx_user:YOUR_DEV_PASSWORD@localhost:5433/algoagentx_dev
```

## 10.2 Run API locally

```powershell
cd D:\Stock_market\algoagentx\AlgoAgentXAPI
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or if venv is already active:

```powershell
cd D:\Stock_market\algoagentx\AlgoAgentXAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

# 11. Development Web local run

```powershell
cd D:\Stock_market\algoagentx\AlgoAgentXApp
npm install
npm run dev
```

If port 3000 is busy:

```powershell
npm run dev -- -p 3001
```

---

# 12. DBeaver connections

## 12.1 Production DBeaver

```txt
Name     : AlgoAgentX PROD
Host     : localhost
Port     : 5432
Database : algoagentx_prod
Username : algoagentx_user
Password : YOUR_PROD_PASSWORD
```

## 12.2 Development DBeaver

```txt
Name     : AlgoAgentX DEV
Host     : localhost
Port     : 5433
Database : algoagentx_dev
Username : algoagentx_user
Password : YOUR_DEV_PASSWORD
```

---

# 13. Common Docker checks

## 13.1 See running containers

```powershell
docker ps
```

## 13.2 See all containers

```powershell
docker ps -a
```

## 13.3 See Docker volumes

```powershell
docker volume ls
```

## 13.4 Inspect container port mapping

```powershell
docker port algoagentx_postgres
docker port algoagentx_postgres_dev
```

---

# 14. Important safety notes

## 14.1 Do not delete DB volume accidentally

Avoid this command unless you intentionally want to delete database data:

```powershell
docker compose --env-file .env.prod -f docker-compose.yml down -v
```

Also avoid this for dev unless you intentionally want to wipe dev DB:

```powershell
docker compose --env-file .env.dev -f docker-compose.dev.yml down -v
```

## 14.2 Correct port usage

```txt
Production DB from Windows/DBeaver : localhost:5432
Development DB from Windows/DBeaver: localhost:5433
Inside Docker Compose network      : postgres:5432
```

## 14.3 Correct database names

```txt
Production DB: algoagentx_prod
Development DB: algoagentx_dev
Old DB name   : algo_db
```

Avoid using `algo_db` going forward to prevent confusion.

---

# 15. Quick daily workflow

## Start production

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod -f docker-compose.yml up -d
```

## Start dev database

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.dev -f docker-compose.dev.yml up -d postgres
```

## Run API locally

```powershell
cd D:\Stock_market\algoagentx\AlgoAgentXAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Run Web locally

```powershell
cd D:\Stock_market\algoagentx\AlgoAgentXApp
npm run dev
```

---

# 16. Most used production commands

## Rebuild/deploy production API + Web

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod stop api web
docker compose --env-file .env.prod rm -sf api web
docker compose --env-file .env.prod up -d --build api web
```

## Restart production API + Web without rebuild

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod stop api web
docker compose --env-file .env.prod rm -sf api web
docker compose --env-file .env.prod up -d api web
```

## Check production

```powershell
docker compose --env-file .env.prod ps
curl http://localhost:8000/health
curl http://localhost:3000
```

## Check dev database

```powershell
docker compose --env-file .env.dev -f docker-compose.dev.yml ps
docker exec -it algoagentx_postgres_dev psql -U algoagentx_user -d algoagentx_dev -c "SELECT version();"
```

docker compose --env-file .env.prod stop api web
docker compose --env-file .env.prod rm -sf api web
docker compose --env-file .env.prod up -d --build api web