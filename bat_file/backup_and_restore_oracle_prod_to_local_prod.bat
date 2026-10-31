@echo off
setlocal EnableExtensions EnableDelayedExpansion

title AlgoAgentX - ORACLE PROD to LOCAL PROD Database Restore

:: ============================================================
:: AlgoAgentX ORACLE PROD Backup + LOCAL PROD Restore
:: Reverse of backup_and_restore_local_prod_to_oracle_prod.bat
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
:: Go to local project root and check SSH key
:: ============================================================

cd /d "%PROJECT%"
if errorlevel 1 (
    echo.
    echo ERROR: Could not open project folder: %PROJECT%
    goto ERROR
)

if not exist "%KEY%" (
    echo.
    echo ERROR: SSH private key not found: %KEY%
    goto ERROR
)


:: ============================================================
:: Generate suggested backup name
:: ============================================================

for /f %%I in ('powershell -NoProfile -Command "(Get-Date -Format 'dd_MMM').ToLower()"') do set "TODAY=%%I"
if not defined TODAY goto ERROR

set "DEFAULT_NAME=algoagentx_prod_!TODAY!_backup"

if not exist "%BACKUP_DIR%" (
    echo Creating Windows backup directory...
    mkdir "%BACKUP_DIR%"
    if errorlevel 1 goto ERROR
)

:ASK_BACKUP_NAME
set "BACKUP_NAME="
echo ============================================================
echo       AlgoAgentX ORACLE PROD Backup to LOCAL PROD
echo ============================================================
echo.
echo Oracle source: %SERVER% / %REMOTE_CONTAINER% / %DB_NAME%
echo Local target : %LOCAL_CONTAINER% / %DB_NAME%
echo.
echo Enter backup name WITHOUT .dump
echo Example: !DEFAULT_NAME!
echo.
set /p "BACKUP_NAME=Backup name [!DEFAULT_NAME!]: "
if not defined BACKUP_NAME set "BACKUP_NAME=!DEFAULT_NAME!"

:: Remove optional .dump suffix, as in original script.
if /I "!BACKUP_NAME:~-5!"==".dump" set "BACKUP_NAME=!BACKUP_NAME:~0,-5!"

:: Limit name to safe filename characters because it is used in SSH commands.
powershell -NoProfile -Command "if ($env:BACKUP_NAME -cmatch '^[A-Za-z0-9_-]+$') { exit 0 } else { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Use only letters, numbers, underscores, or hyphens.
    echo.
    goto ASK_BACKUP_NAME
)

set "BACKUP_FILE=!BACKUP_NAME!.dump"
set "LOCAL_BACKUP=%BACKUP_DIR%\!BACKUP_FILE!"
set "REMOTE_BACKUP=%REMOTE_BACKUP_DIR%/!BACKUP_FILE!"

:: Do not silently overwrite an existing Windows backup.
if exist "!LOCAL_BACKUP!" (
    echo.
    echo ERROR: Windows backup already exists: !LOCAL_BACKUP!
    echo Please choose a different backup name.
    echo.
    goto ASK_BACKUP_NAME
)

echo.
echo ============================================================
echo Backup Information
echo ============================================================
echo.
echo Backup Name : !BACKUP_FILE!
echo Oracle Source: %SERVER%
echo Oracle Backup: !REMOTE_BACKUP!
echo Windows Copy: !LOCAL_BACKUP!
echo Local Target: %LOCAL_CONTAINER% / %DB_NAME%
echo.
echo WARNING: This RESTORES Oracle PROD data into LOCAL PROD.
echo Existing LOCAL PROD objects/data can be replaced.
echo Stop applications writing to LOCAL PROD before restoring.
echo Take a separate backup of LOCAL PROD first if it must be kept.
echo.
choice /C YN /M "Continue with Oracle backup and LOCAL PROD restore"
if errorlevel 2 (
    echo.
    echo Operation cancelled.
    pause
    exit /b 0
)


:: ============================================================
:: [1/6] Connect to Oracle Ubuntu and prepare backup folder
:: ============================================================

echo.
echo [1/6] Connecting to Oracle Ubuntu and preparing backup folder...
ssh -i "%KEY%" %SERVER% "mkdir -p '%REMOTE_BACKUP_DIR%' && cd '%REMOTE_PROJECT%' && echo Connected to Oracle Ubuntu && pwd"
if errorlevel 1 goto ERROR


:: ============================================================
:: [2/6] Take backup FROM ORACLE PROD PostgreSQL Docker
:: ============================================================

echo.
echo [2/6] Taking backup from ORACLE PROD database...
ssh -i "%KEY%" %SERVER% "cd '%REMOTE_PROJECT%' && docker exec %REMOTE_CONTAINER% pg_dump -U %DB_USER% -d %DB_NAME% -F c -b -v -f '/tmp/!BACKUP_FILE!'"
if errorlevel 1 goto ERROR


:: ============================================================
:: [3/6] Copy Oracle Docker dump to Oracle Ubuntu backup folder
:: ============================================================

echo.
echo [3/6] Copying ORACLE Docker backup to Oracle Ubuntu folder...
ssh -i "%KEY%" %SERVER% "cd '%REMOTE_PROJECT%' && docker cp '%REMOTE_CONTAINER%:/tmp/!BACKUP_FILE!' '!REMOTE_BACKUP!'"
if errorlevel 1 goto ERROR


:: ============================================================
:: [4/6] Download Oracle backup to local Windows backup folder
:: ============================================================

echo.
echo [4/6] Downloading ORACLE backup to Windows...
scp -i "%KEY%" "%SERVER%:!REMOTE_BACKUP!" "!LOCAL_BACKUP!"
if errorlevel 1 goto ERROR

if not exist "!LOCAL_BACKUP!" (
    echo ERROR: Downloaded backup file is missing.
    goto ERROR
)
for %%F in ("!LOCAL_BACKUP!") do if %%~zF EQU 0 (
    echo ERROR: Downloaded backup file is empty.
    goto ERROR
)


:: ============================================================
:: [5/6] Copy Windows backup into LOCAL PROD Docker container
:: ============================================================

echo.
echo [5/6] Copying Windows backup into LOCAL PROD Docker container...
docker cp "!LOCAL_BACKUP!" "%LOCAL_CONTAINER%:/tmp/!BACKUP_FILE!"
if errorlevel 1 goto ERROR


:: ============================================================
:: [6/6] Restore Oracle backup INTO LOCAL PROD PostgreSQL
:: ============================================================

echo.
echo [6/6] Restoring Oracle data into LOCAL PROD database...
docker exec -i %LOCAL_CONTAINER% pg_restore -U %DB_USER% -d %DB_NAME% --clean --if-exists --no-owner --no-privileges -v "/tmp/!BACKUP_FILE!"
if errorlevel 1 goto ERROR


echo.
echo ============================================================
echo                      SUCCESS
echo ============================================================
echo.
echo Oracle PROD backup and LOCAL PROD restore completed.
echo Backup Name  : !BACKUP_FILE!
echo Windows Copy : !LOCAL_BACKUP!
echo Oracle Backup: !REMOTE_BACKUP!
echo Restored Into: %LOCAL_CONTAINER% / %DB_NAME%
echo ============================================================
echo.
pause
exit /b 0


:ERROR
echo.
echo ============================================================
echo                       ERROR
echo ============================================================
echo.
echo Process failed. Check the command output above.
echo Backup file: !BACKUP_FILE!
echo.
echo Possible reasons:
echo 1. Oracle SSH connection, private key, or server unavailable
echo 2. Oracle PostgreSQL Docker container not running
echo 3. Windows download directory or SCP issue
echo 4. Local Docker container not running
echo 5. PostgreSQL pg_dump or pg_restore failed
echo 6. Local PROD contains locks or incompatible database objects
echo.
echo NOTE: If pg_restore failed after starting, LOCAL PROD may be
echo partially modified. Review restore output before retrying.
echo ============================================================
echo.
pause
exit /b 1
