\
@echo off
setlocal
cd /d "%~dp0\.."

where docker >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Docker was not found in PATH.
    echo Install/start Docker Desktop, then run this script again.
    exit /b 1
)

echo Starting AlgoAgentX development PostgreSQL and Redis...
docker compose -f docker-compose.dev.yml up -d
if errorlevel 1 exit /b 1

echo.
echo Waiting for services...
docker compose -f docker-compose.dev.yml ps
echo.
echo PostgreSQL: localhost:5433
echo Redis:      localhost:6380
echo.
echo You can now start FastAPI:
echo   .venv\Scripts\activate
echo   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
endlocal
