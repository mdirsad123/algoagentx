# AlgoAgentX Database Backup & Restore Steps

Use this file for **safe database backup and restore** between:

```txt
PROD database : algoagentx_prod
PROD container: algoagentx_postgres_prod
PROD port     : localhost:5432

DEV database  : algoagentx_dev
DEV container : algoagentx_postgres_dev
DEV port      : localhost:5433
```

# 1. Start required containers

## 1.1 Start production, development PostgreSQL

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod -f docker-compose.yml up -d postgres_prod
docker compose --env-file .env.dev -f docker-compose.dev.yml up -d postgres_dev
```
----------------------------------------------------------------------------------------------------------------------------------------
## 3. step to take backup from dev database to prod database

# 3.1 Take backup from DEV database
docker exec -t algoagentx_postgres_dev pg_dump -U algoagentx_user -d algoagentx_dev -F c -b -v -f /tmp/algoagentx_dev_18_may_backup.dump

# 3.2 Copy DEV backup to Windows
docker cp algoagentx_postgres_dev:/tmp/algoagentx_dev_18_may_backup.dump D:\Stock_market\algoagentx\AlgoAgentXAPI\backup_db\algoagentx_dev_18_may_backup.dump

# 3.3 Copy Dev backup into PROD container
docker cp D:\Stock_market\algoagentx\AlgoAgentXAPI\backup_db\algoagentx_dev_18_may_backup.dump algoagentx_postgres_prod:/tmp/algoagentx_dev_18_may_backup.dump

# 3.4. Restore DEV backup into PROD database
docker exec -it algoagentx_postgres_prod pg_restore -U algoagentx_user -d algoagentx_prod --clean --if-exists --no-owner --no-privileges -v /tmp/algoagentx_dev_18_may_backup.dump

-------------------------------------------------------------------------------------------------------------------------------------------
## 4. step to take backup from prod database to dev database

# 4.1 Take backup from PROD database
docker exec -t algoagentx_postgres_prod pg_dump -U algoagentx_user -d algoagentx_prod -F c -b -v -f /tmp/algoagentx_prod_15_may_backup.dump

# 4.2 Copy PROD backup to Windows
docker cp algoagentx_postgres_prod:/tmp/algoagentx_prod_15_may_backup.dump D:\Stock_market\algoagentx\AlgoAgentXAPI\backup_db\algoagentx_prod_15_may_backup.dump

# 4.3 Copy Prod backup into Dev container
docker cp D:\Stock_market\algoagentx\AlgoAgentXAPI\backup_db\algoagentx_prod_15_may_backup.dump algoagentx_postgres_dev:/tmp/algoagentx_prod_15_may_backup.dump

# 4.4 Restore PROD backup into DEV database
docker exec -it algoagentx_postgres_dev pg_restore -U algoagentx_user -d algoagentx_dev --clean --if-exists --no-owner --no-privileges -v /tmp/algoagentx_prod_15_may_backup.dump
-------------------------------------------------------------------------------------------------------------------------------------------
