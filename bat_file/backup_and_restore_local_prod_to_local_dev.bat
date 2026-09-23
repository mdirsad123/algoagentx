@echo off
setlocal EnableExtensions EnableDelayedExpansion

title AlgoAgentX - LOCAL PROD to DEV Database Restore

:: ============================================================
:: Configuration
:: ============================================================

set "PROJECT=D:\Stock_market\algoagentx"
set "BACKUP_DIR=%PROJECT%\AlgoAgentXAPI\backup_db"

set "PROD_CONTAINER=algoagentx_postgres_prod"
set "DEV_CONTAINER=algoagentx_postgres_dev"

set "DB_USER=algoagentx_user"

set "PROD_DB=algoagentx_prod"
set "DEV_DB=algoagentx_dev"

:: ============================================================
:: Go to project root
:: ============================================================

cd /d "%PROJECT%"

if errorlevel 1 (
    echo.
    echo ERROR: Could not open project folder:
    echo %PROJECT%
    echo.
    pause
    exit /b 1
)


:: ============================================================
:: Generate today's default backup name
:: Example:
:: algoagentx_prod_23_sep_backup
:: ============================================================

for /f %%I in ('powershell -NoProfile -Command "(Get-Date -Format 'dd_MMM').ToLower()"') do set "TODAY=%%I"

set "DEFAULT_NAME=algoagentx_prod_!TODAY!_backup"


echo ============================================================
echo       AlgoAgentX LOCAL PROD to DEV Database Restore
echo ============================================================
echo.
echo Source:
echo   Container : %PROD_CONTAINER%
echo   Database  : %PROD_DB%
echo.
echo Destination:
echo   Container : %DEV_CONTAINER%
echo   Database  : %DEV_DB%
echo.
echo ------------------------------------------------------------
echo Enter backup name WITHOUT .dump
echo.
echo Example:
echo %DEFAULT_NAME%
echo ------------------------------------------------------------
echo.

set /p "BACKUP_NAME=Backup name [%DEFAULT_NAME%]: "

:: If user presses ENTER
if not defined BACKUP_NAME (
    set "BACKUP_NAME=%DEFAULT_NAME%"
)

:: Remove .dump if user entered it
if /I "!BACKUP_NAME:~-5!"==".dump" (
    set "BACKUP_NAME=!BACKUP_NAME:~0,-5!"
)

set "BACKUP_FILE=!BACKUP_NAME!.dump"
set "LOCAL_BACKUP=%BACKUP_DIR%\!BACKUP_FILE!"


echo.
echo ============================================================
echo Backup Information
echo ============================================================
echo.
echo Backup:
echo   !BACKUP_FILE!
echo.
echo Windows Backup:
echo   !LOCAL_BACKUP!
echo.
echo Source Database:
echo   %PROD_DB%
echo.
echo Destination Database:
echo   %DEV_DB%
echo.
echo ============================================================
echo.
echo WARNING
echo ------------------------------------------------------------
echo This will RESTORE LOCAL PROD database into LOCAL DEV.
echo.
echo Existing DEV database objects/data may be replaced.
echo ------------------------------------------------------------
echo.

choice /C YN /M "Continue with LOCAL PROD to DEV restore"

if errorlevel 2 (
    echo.
    echo Operation cancelled.
    pause
    exit /b 0
)


:: ============================================================
:: Make sure backup directory exists
:: ============================================================

if not exist "%BACKUP_DIR%" (
    echo.
    echo Creating backup directory...
    mkdir "%BACKUP_DIR%"

    if errorlevel 1 goto ERROR
)


:: ============================================================
:: STEP 1
:: Take backup from PROD database
:: ============================================================

echo.
echo ============================================================
echo [1/4] Taking backup from LOCAL PROD database
echo ============================================================
echo.

docker exec -t %PROD_CONTAINER% ^
pg_dump ^
-U %DB_USER% ^
-d %PROD_DB% ^
-F c ^
-b ^
-v ^
-f "/tmp/!BACKUP_FILE!"

if errorlevel 1 goto ERROR


:: ============================================================
:: STEP 2
:: Copy PROD backup to Windows
:: ============================================================

echo.
echo ============================================================
echo [2/4] Copying PROD backup from Docker to Windows
echo ============================================================
echo.

docker cp ^
%PROD_CONTAINER%:/tmp/!BACKUP_FILE! ^
"!LOCAL_BACKUP!"

if errorlevel 1 goto ERROR


:: ============================================================
:: STEP 3
:: Copy PROD backup into DEV container
:: ============================================================

echo.
echo ============================================================
echo [3/4] Copying backup into DEV Docker container
echo ============================================================
echo.

docker cp "!LOCAL_BACKUP!" "%DEV_CONTAINER%:/tmp/!BACKUP_FILE!"

if errorlevel 1 goto ERROR


:: ============================================================
:: STEP 4
:: Restore PROD backup into DEV database
:: ============================================================

echo.
echo ============================================================
echo [4/4] Restoring LOCAL PROD backup into DEV database
echo ============================================================
echo.

docker exec -i %DEV_CONTAINER% pg_restore -U %DB_USER% -d %DEV_DB% --clean --if-exists --no-owner --no-privileges -v "/tmp/!BACKUP_FILE!"

if errorlevel 1 goto ERROR


:: ============================================================
:: SUCCESS
:: ============================================================

echo.
echo ============================================================
echo                     SUCCESS
echo ============================================================
echo.
echo LOCAL PROD database successfully restored into DEV.
echo.
echo Backup:
echo   !BACKUP_FILE!
echo.
echo Windows Backup:
echo   !LOCAL_BACKUP!
echo.
echo Source:
echo   %PROD_DB%
echo.
echo Restored Into:
echo   %DEV_DB%
echo.
echo ============================================================
echo.

pause
exit /b 0


:: ============================================================
:: ERROR
:: ============================================================

:ERROR

echo.
echo ============================================================
echo                      ERROR
echo ============================================================
echo.
echo LOCAL PROD to DEV restore failed.
echo.
echo Backup:
echo   !BACKUP_FILE!
echo.
echo Check the command output above to identify
echo which step failed.
echo.
echo Possible reasons:
echo.
echo 1. PROD Docker container is not running
echo 2. DEV Docker container is not running
echo 3. PROD database is unavailable
echo 4. DEV database is unavailable
echo 5. Backup folder permission issue
echo 6. pg_dump failed
echo 7. pg_restore failed
echo.
echo ============================================================
echo.

pause
exit /b 1