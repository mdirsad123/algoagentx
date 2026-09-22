@echo off
setlocal EnableExtensions EnableDelayedExpansion

title AlgoAgentX - PROD Database Backup to Oracle

:: ============================================================
:: AlgoAgentX PROD Database Backup + Oracle Restore
:: ============================================================

set "PROJECT=D:\Stock_market\algoagentx"
set "BACKUP_DIR=%PROJECT%\AlgoAgentXAPI\backup_db"

set "KEY=%PROJECT%\docs\oracle_cloud_keys\ssh-key-private.key"

set "SERVER=ubuntu@130.210.58.143"

set "LOCAL_CONTAINER=algoagentx_postgres_prod"
set "REMOTE_CONTAINER=algoagentx_postgres_prod"

set "DB_USER=algoagentx_user"
set "DB_NAME=algoagentx_prod"

set "REMOTE_PROJECT=/home/ubuntu/stock_market/algoagentx"
set "REMOTE_BACKUP_DIR=%REMOTE_PROJECT%/AlgoAgentXAPI/backup_db"


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
:: Generate today's suggested backup name
:: Example: algoagentx_prod_23_sep_backup
:: ============================================================

for /f %%I in ('powershell -NoProfile -Command "(Get-Date -Format 'dd_MMM').ToLower()"') do set "TODAY=%%I"

set "DEFAULT_NAME=algoagentx_prod_!TODAY!_backup"


echo ============================================================
echo        AlgoAgentX PROD Database Backup to Oracle
echo ============================================================
echo.
echo Local Project:
echo %PROJECT%
echo.
echo Source Database:
echo %DB_NAME%
echo.
echo Oracle Server:
echo %SERVER%
echo.
echo ------------------------------------------------------------
echo Enter backup name WITHOUT .dump
echo.
echo Example:
echo %DEFAULT_NAME%
echo ------------------------------------------------------------
echo.

set /p "BACKUP_NAME=Backup name [%DEFAULT_NAME%]: "

:: If user just presses ENTER, use today's default name
if not defined BACKUP_NAME (
    set "BACKUP_NAME=%DEFAULT_NAME%"
)

:: Remove .dump if user accidentally entered it
if /I "!BACKUP_NAME:~-5!"==".dump" (
    set "BACKUP_NAME=!BACKUP_NAME:~0,-5!"
)

set "BACKUP_FILE=!BACKUP_NAME!.dump"

set "LOCAL_BACKUP=%BACKUP_DIR%\!BACKUP_FILE!"
set "REMOTE_BACKUP=%REMOTE_BACKUP_DIR%/!BACKUP_FILE!"


echo.
echo ============================================================
echo Backup Information
echo ============================================================
echo.
echo Backup Name:
echo !BACKUP_FILE!
echo.
echo Local:
echo !LOCAL_BACKUP!
echo.
echo Oracle:
echo !REMOTE_BACKUP!
echo.
echo ============================================================
echo.
echo WARNING:
echo This will RESTORE the backup into the Oracle PROD database.
echo Existing PROD database objects/data can be replaced.
echo.

choice /C YN /M "Continue with backup and PROD restore"

if errorlevel 2 (
    echo.
    echo Operation cancelled.
    pause
    exit /b 0
)


:: ============================================================
:: Make sure local backup directory exists
:: ============================================================

if not exist "%BACKUP_DIR%" (
    echo.
    echo Creating local backup directory...
    mkdir "%BACKUP_DIR%"

    if errorlevel 1 goto ERROR
)


echo.
echo ============================================================
echo [1/5] Taking backup from LOCAL PROD database
echo ============================================================
echo.

docker exec -t %LOCAL_CONTAINER% ^
pg_dump ^
-U %DB_USER% ^
-d %DB_NAME% ^
-F c ^
-b ^
-v ^
-f "/tmp/!BACKUP_FILE!"

if errorlevel 1 goto ERROR


echo.
echo ============================================================
echo [2/5] Copying PROD backup from Docker to Windows
echo ============================================================
echo.

docker cp ^
%LOCAL_CONTAINER%:/tmp/!BACKUP_FILE! ^
"!LOCAL_BACKUP!"

if errorlevel 1 goto ERROR


echo.
echo ============================================================
echo [3/5] Uploading Windows backup to Oracle Ubuntu
echo ============================================================
echo.

scp ^
-i "%KEY%" ^
"!LOCAL_BACKUP!" ^
"%SERVER%:!REMOTE_BACKUP!"

if errorlevel 1 goto ERROR


echo.
echo ============================================================
echo [4/5] Copying Oracle backup into PROD Docker container
echo ============================================================
echo.

ssh ^
-i "%KEY%" ^
%SERVER% ^
"docker cp '!REMOTE_BACKUP!' %REMOTE_CONTAINER%:/tmp/!BACKUP_FILE!"

if errorlevel 1 goto ERROR


echo.
echo ============================================================
echo [5/5] Restoring backup into Oracle PROD database
echo ============================================================
echo.

ssh ^
-i "%KEY%" ^
%SERVER% ^
"docker exec -i %REMOTE_CONTAINER% pg_restore -U %DB_USER% -d %DB_NAME% --clean --if-exists --no-owner --no-privileges -v /tmp/!BACKUP_FILE!"

if errorlevel 1 goto ERROR


echo.
echo ============================================================
echo                 SUCCESS
echo ============================================================
echo.
echo PROD database backup and Oracle restore completed.
echo.
echo Backup Name:
echo !BACKUP_FILE!
echo.
echo Windows Backup:
echo !LOCAL_BACKUP!
echo.
echo Oracle Backup:
echo !REMOTE_BACKUP!
echo.
echo Database Restored:
echo %DB_NAME%
echo.
echo ============================================================
echo.

pause
exit /b 0



:ERROR

echo.
echo ============================================================
echo                    ERROR
echo ============================================================
echo.
echo Process failed.
echo.
echo Backup:
echo !BACKUP_FILE!
echo.
echo Check the command output above to identify which step failed.
echo.
echo Possible reasons:
echo.
echo 1. Local Docker container is not running
echo 2. PostgreSQL PROD container is unavailable
echo 3. SSH connection failed
echo 4. Oracle server is offline
echo 5. Private key permission problem
echo 6. Remote backup directory does not exist
echo 7. Database restore failed
echo.
echo ============================================================
echo.

pause
exit /b 1