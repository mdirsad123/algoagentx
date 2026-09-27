@echo off
setlocal

title AlgoAgentX - Download ENV Files from Oracle

set "BACKUP=D:\Stock_market\bakup_env"
set "KEY=D:\Stock_market\algoagentx\docs\oracle_cloud_keys\ssh-key-private.key"
set "SERVER=ubuntu@130.210.58.143"
set "REMOTE=/home/ubuntu/stock_market/algoagentx"

echo ==========================================
echo    AlgoAgentX ENV Download from Oracle
echo ==========================================
echo.
echo Server : %SERVER%
echo Backup : %BACKUP%
echo.

rem Create backup folder if it does not exist
if not exist "%BACKUP%" (
    echo Creating backup folder...
    mkdir "%BACKUP%"
    if errorlevel 1 goto ERROR
)

echo [1/4] Downloading root .env.dev...
scp -i "%KEY%" "%SERVER%:%REMOTE%/.env.dev" "%BACKUP%\.env.dev"
if errorlevel 1 goto ERROR

echo.
echo [2/4] Downloading root .env.prod...
scp -i "%KEY%" "%SERVER%:%REMOTE%/.env.prod" "%BACKUP%\.env.prod"
if errorlevel 1 goto ERROR

echo.
echo [3/4] Downloading AlgoAgentXAPI/.env...
scp -i "%KEY%" "%SERVER%:%REMOTE%/AlgoAgentXAPI/.env" "%BACKUP%\.env"
if errorlevel 1 goto ERROR

echo.
echo [4/4] Downloading AlgoAgentXApp/.env.local...
scp -i "%KEY%" "%SERVER%:%REMOTE%/AlgoAgentXApp/.env.local" "%BACKUP%\.env.local"
if errorlevel 1 goto ERROR

echo.
echo ==========================================
echo SUCCESS - All 4 ENV files downloaded.
echo ==========================================
echo.
echo Saved in:
echo   %BACKUP%
echo.
echo Files:
echo   .env.dev       ^<- project root .env.dev
echo   .env.prod      ^<- project root .env.prod
echo   .env           ^<- AlgoAgentXAPI\.env
echo   .env.local     ^<- AlgoAgentXApp\.env.local
echo.
echo You can now review them manually before copying them back into the project.
echo.
pause
exit /b 0

:ERROR
echo.
echo ==========================================
echo ERROR - ENV download failed.
echo ==========================================
echo.
echo Check:
echo   1. Internet connection
echo   2. Oracle Ubuntu server is running
echo   3. SSH private key path is correct
echo   4. Remote ENV file exists
echo   5. Windows OpenSSH/scp is installed
echo   6. You have permission to write to %BACKUP%
echo.
pause
exit /b 1
