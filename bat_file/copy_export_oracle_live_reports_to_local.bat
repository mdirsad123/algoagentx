@echo off
setlocal EnableExtensions

title AlgoAgentX - Export Live Deployment Reports

rem ============================================================
rem CONFIG
rem ============================================================
set "BACKUP=D:\Stock_market\bakup_env"
set "KEY=D:\Stock_market\algoagentx\docs\oracle_cloud_keys\ssh-key-private.key"
set "SERVER=ubuntu@130.210.58.143"

set "PG_CONTAINER=algoagentx_postgres_prod"
set "DB_USER=algoagentx_user"
set "DB_NAME=algoagentx_prod"

set "REMOTE_EXPORT=/home/ubuntu/algoagentx_live_export"

echo ============================================================
echo        AlgoAgentX Live Deployment Report Export
echo ============================================================
echo.
echo Server        : %SERVER%
echo PostgreSQL    : %PG_CONTAINER%
echo Local backup  : %BACKUP%
echo.

rem ============================================================
rem 1. ASK FOR DEPLOYMENT UUID
rem ============================================================
set "DEPLOYMENT_ID="
set /p "DEPLOYMENT_ID=Enter deployment UUID: "

if not defined DEPLOYMENT_ID (
    echo.
    echo ERROR: Deployment UUID cannot be empty.
    goto ERROR
)

rem Basic UUID format validation
powershell -NoProfile -Command ^
  "if ('%DEPLOYMENT_ID%' -match '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$') { exit 0 } else { exit 1 }"

if errorlevel 1 (
    echo.
    echo ERROR: Invalid deployment UUID format:
    echo   %DEPLOYMENT_ID%
    goto ERROR
)

rem ============================================================
rem 2. VERIFY LOCAL REQUIREMENTS
rem ============================================================
if not exist "%KEY%" (
    echo.
    echo ERROR: SSH private key not found:
    echo   %KEY%
    goto ERROR
)

if not exist "%BACKUP%" (
    echo Creating local backup folder...
    mkdir "%BACKUP%"
    if errorlevel 1 goto ERROR
)

rem Use a separate folder per deployment so old exports are not overwritten
set "LOCAL_EXPORT=%BACKUP%\live_report_%DEPLOYMENT_ID%"

if not exist "%LOCAL_EXPORT%" (
    mkdir "%LOCAL_EXPORT%"
    if errorlevel 1 goto ERROR
)

echo.
echo Deployment ID :
echo   %DEPLOYMENT_ID%
echo.
echo Reports will be saved to:
echo   %LOCAL_EXPORT%
echo.

rem ============================================================
rem 3. PREPARE REMOTE EXPORT FOLDER
rem ============================================================
echo [1/8] Preparing Oracle Ubuntu export folder...

ssh -i "%KEY%" "%SERVER%" "mkdir -p %REMOTE_EXPORT% && rm -f %REMOTE_EXPORT%/deployment_info.csv %REMOTE_EXPORT%/live_signals.csv %REMOTE_EXPORT%/primary_live_orders.csv %REMOTE_EXPORT%/all_live_orders_with_copies.csv"

if errorlevel 1 goto ERROR

rem ============================================================
rem 4. EXPORT DEPLOYMENT INFO
rem ============================================================
echo.
echo [2/8] Exporting deployment_info.csv...

ssh -i "%KEY%" "%SERVER%" "docker exec -i %PG_CONTAINER% psql -v ON_ERROR_STOP=1 -U %DB_USER% -d %DB_NAME% -c \"\copy (SELECT * FROM strategy_deployments WHERE id = '%DEPLOYMENT_ID%') TO '/tmp/deployment_info.csv' CSV HEADER\""

if errorlevel 1 goto ERROR

rem ============================================================
rem 5. EXPORT LIVE SIGNALS
rem ============================================================
echo.
echo [3/8] Exporting live_signals.csv...

ssh -i "%KEY%" "%SERVER%" "docker exec -i %PG_CONTAINER% psql -v ON_ERROR_STOP=1 -U %DB_USER% -d %DB_NAME% -c \"\copy (SELECT * FROM live_signals WHERE deployment_id = '%DEPLOYMENT_ID%' ORDER BY created_at ASC) TO '/tmp/live_signals.csv' CSV HEADER\""

if errorlevel 1 goto ERROR

rem ============================================================
rem 6. EXPORT PRIMARY ACCOUNT ORDERS ONLY
rem ============================================================
echo.
echo [4/8] Exporting primary_live_orders.csv...

ssh -i "%KEY%" "%SERVER%" "docker exec -i %PG_CONTAINER% psql -v ON_ERROR_STOP=1 -U %DB_USER% -d %DB_NAME% -c \"\copy (SELECT o.* FROM live_orders o JOIN strategy_deployments d ON d.id = o.deployment_id WHERE o.deployment_id = '%DEPLOYMENT_ID%' AND o.broker_account_id = d.broker_account_id ORDER BY o.created_at ASC) TO '/tmp/primary_live_orders.csv' CSV HEADER\""

if errorlevel 1 goto ERROR

rem ============================================================
rem 7. EXPORT ALL ORDERS INCLUDING COPY TRADING
rem ============================================================
echo.
echo [5/8] Exporting all_live_orders_with_copies.csv...

ssh -i "%KEY%" "%SERVER%" "docker exec -i %PG_CONTAINER% psql -v ON_ERROR_STOP=1 -U %DB_USER% -d %DB_NAME% -c \"\copy (SELECT * FROM live_orders WHERE deployment_id = '%DEPLOYMENT_ID%' ORDER BY created_at ASC) TO '/tmp/all_live_orders_with_copies.csv' CSV HEADER\""

if errorlevel 1 goto ERROR

rem ============================================================
rem 8. COPY FILES FROM POSTGRES CONTAINER TO UBUNTU HOST
rem ============================================================
echo.
echo [6/8] Copying reports from PostgreSQL container to Ubuntu...

ssh -i "%KEY%" "%SERVER%" "docker cp %PG_CONTAINER%:/tmp/deployment_info.csv %REMOTE_EXPORT%/deployment_info.csv && docker cp %PG_CONTAINER%:/tmp/live_signals.csv %REMOTE_EXPORT%/live_signals.csv && docker cp %PG_CONTAINER%:/tmp/primary_live_orders.csv %REMOTE_EXPORT%/primary_live_orders.csv && docker cp %PG_CONTAINER%:/tmp/all_live_orders_with_copies.csv %REMOTE_EXPORT%/all_live_orders_with_copies.csv && chmod 644 %REMOTE_EXPORT%/*.csv"

if errorlevel 1 goto ERROR

rem ============================================================
rem 9. DOWNLOAD REPORTS TO WINDOWS
rem ============================================================
echo.
echo [7/8] Downloading reports from Oracle Ubuntu to Windows...

scp -i "%KEY%" "%SERVER%:%REMOTE_EXPORT%/deployment_info.csv" "%LOCAL_EXPORT%\deployment_info.csv"
if errorlevel 1 goto ERROR

scp -i "%KEY%" "%SERVER%:%REMOTE_EXPORT%/live_signals.csv" "%LOCAL_EXPORT%\live_signals.csv"
if errorlevel 1 goto ERROR

scp -i "%KEY%" "%SERVER%:%REMOTE_EXPORT%/primary_live_orders.csv" "%LOCAL_EXPORT%\primary_live_orders.csv"
if errorlevel 1 goto ERROR

scp -i "%KEY%" "%SERVER%:%REMOTE_EXPORT%/all_live_orders_with_copies.csv" "%LOCAL_EXPORT%\all_live_orders_with_copies.csv"
if errorlevel 1 goto ERROR

rem ============================================================
rem 10. VERIFY
rem ============================================================
echo.
echo [8/8] Verifying downloaded files...
echo.

dir "%LOCAL_EXPORT%\*.csv"

echo.
echo ============================================================
echo SUCCESS - AlgoAgentX live reports downloaded
echo ============================================================
echo.
echo Deployment:
echo   %DEPLOYMENT_ID%
echo.
echo Saved in:
echo   %LOCAL_EXPORT%
echo.
echo Files:
echo   deployment_info.csv
echo   live_signals.csv
echo   primary_live_orders.csv
echo   all_live_orders_with_copies.csv
echo.
echo Opening export folder...
start "" "%LOCAL_EXPORT%"
echo.
pause
exit /b 0

:ERROR
echo.
echo ============================================================
echo ERROR - Live deployment report export failed
echo ============================================================
echo.
echo Check:
echo   1. Oracle Ubuntu server is running
echo   2. Internet connection is working
echo   3. SSH key path is correct:
echo      %KEY%
echo   4. PostgreSQL container is running:
echo      %PG_CONTAINER%
echo   5. Deployment UUID exists in strategy_deployments
echo   6. Windows OpenSSH ssh/scp is installed
echo.
echo Deployment entered:
echo   %DEPLOYMENT_ID%
echo.
pause
exit /b 1
