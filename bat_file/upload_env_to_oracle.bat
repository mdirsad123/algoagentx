@echo off
title AlgoAgentX - Upload ENV Files to Oracle

set "PROJECT=D:\Stock_market\algoagentx"
set "KEY=D:\Stock_market\algoagentx\docs\oracle_cloud_keys\ssh-key-private.key"
set "SERVER=ubuntu@130.210.58.143"
set "REMOTE=/home/ubuntu/stock_market/algoagentx"

echo ==========================================
echo      AlgoAgentX ENV Upload to Oracle
echo ==========================================
echo.
echo Server : %SERVER%
echo Project: %PROJECT%
echo.

echo [1/4] Uploading .env.dev...
scp -i "%KEY%" "%PROJECT%\.env.dev" "%SERVER%:%REMOTE%/.env.dev"
if errorlevel 1 goto ERROR

echo.
echo [2/4] Uploading .env.prod...
scp -i "%KEY%" "%PROJECT%\.env.prod" "%SERVER%:%REMOTE%/.env.prod"
if errorlevel 1 goto ERROR

echo.
echo [3/4] Uploading AlgoAgentXAPI\.env...
scp -i "%KEY%" "%PROJECT%\AlgoAgentXAPI\.env" "%SERVER%:%REMOTE%/AlgoAgentXAPI/.env"
if errorlevel 1 goto ERROR

echo.
echo [4/4] Uploading AlgoAgentXApp\.env.local...
scp -i "%KEY%" "%PROJECT%\AlgoAgentXApp\.env.local" "%SERVER%:%REMOTE%/AlgoAgentXApp/.env.local"
if errorlevel 1 goto ERROR

echo.
echo ==========================================
echo SUCCESS - All ENV files uploaded.
echo ==========================================
echo.
echo Uploaded:
echo   .env.dev
echo   .env.prod
echo   AlgoAgentXAPI/.env
echo   AlgoAgentXApp/.env.local
echo.
pause
exit /b 0


:ERROR
echo.
echo ==========================================
echo ERROR - ENV upload failed.
echo ==========================================
echo.
echo Check:
echo   1. Internet connection
echo   2. Oracle Ubuntu server is running
echo   3. Private key permissions
echo   4. Local ENV file exists
echo   5. Remote folder exists
echo.
pause
exit /b 1