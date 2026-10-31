# AlgoAgentX Deploy Commands

# 2. Production commands
## 2.1 Start all production services
docker compose --env-file .env.prod -f docker-compose.yml up -d

## 2.2 Stop all production services
docker compose --env-file .env.prod -f docker-compose.yml stop
---

## 2.3 Stop and remove all production services
docker compose --env-file .env.prod -f docker-compose.yml down -v

# 3. Production API/Web deploy and rebuild
# all service build of prod
docker compose --env-file .env.prod -f docker-compose.yml up -d --build

# below is only for updated file restart
docker compose --env-file .env.prod -f docker-compose.yml up -d --build --force-recreate api live_history_worker

# below command live 100 logs watch
docker compose --env-file .env.prod logs -f api web live_market_worker live_strategy_worker live_reconcile_worker live_position_manager_worker live_history_worker redis postgres_prod live_legacy_runner_worker live_tradelocker_candle_worker

docker compose --env-file .env.prod logs -f --tail=100 api live_legacy_runner_worker live_history_worker

```powershell
cd D:\Stock_market\algoagentx
docker compose --env-file .env.prod stop api web          # stop only app or api
docker compose --env-file .env.prod up -d api web         # only up app or api
docker compose --env-file .env.prod up -d --build api web # if changes app or api then build again
```

# if backtest is stuck then need to start celery worker
docker compose --env-file .env.prod -f docker-compose.yml --profile worker up -d --build
docker compose --env-file .env.prod -f docker-compose.yml --profile worker up -d celery_worker

Use this especially when:
1. API logs — last 2 hours
docker compose --env-file .env.prod logs --since=2h --tail=2000 api

2. Identify CPU-consuming processes
ps -eo pid,ppid,pcpu,pmem,stat,etime,args --sort=-pcpu

3. Check processes inside API container
docker top algoagentx_api -eo pid,ppid,pcpu,pmem,stat,args

4. Live market worker
docker compose --env-file .env.prod logs --since=2h --tail=1000 live_market_worker

5. Live strategy worker
docker compose --env-file .env.prod logs --since=2h --tail=1000 live_strategy_worker

6. History warmup worker
docker compose --env-file .env.prod logs --since=2h --tail=500 live_history_worker

7. Reconcile and position workers
docker compose --env-file .env.prod logs --since=2h --tail=1000 live_reconcile_worker live_position_manager_worker

8. Next.js frontend errors
docker compose --env-file .env.prod logs --since=2h --tail=1000 web

9. Celery main worker
docker compose --env-file .env.prod logs --since=2h --tail=500 celery_worker

10. Container CPU and RAM snapshot
docker stats --no-stream

11. Current Docker service settings
docker compose --env-file .env.prod ps -a