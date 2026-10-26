@echo off
setlocal EnableExtensions DisableDelayedExpansion
title AlgoAgentX - Oracle SSH Log Collector

rem Reused from your existing report-export BAT.
set "KEY=D:\Stock_market\algoagentx\docs\oracle_cloud_keys\ssh-key-private.key"
set "SERVER=ubuntu@130.210.58.143"
set "BACKUP=D:\Stock_market\bakup_env"
set "REMOTE_DIR=/home/ubuntu/stock_market/algoagentx"
rem Every remote command is bounded to avoid indefinite docker logs -f captures.
set "TIME_LIMIT=60"

if not exist "%KEY%" (
    echo ERROR: SSH key not found: "%KEY%"
    goto :ERROR
)
if not exist "%BACKUP%" mkdir "%BACKUP%"
if errorlevel 1 goto :ERROR
set "OUTDIR=%BACKUP%\algoagentx_diagnostics"
if not exist "%OUTDIR%" mkdir "%OUTDIR%"
if errorlevel 1 goto :ERROR

:MENU
cls
echo ================================================================
echo  AlgoAgentX Oracle Log Collector - READ ONLY commands recommended
echo ================================================================
echo Server: %SERVER%
echo Local : %OUTDIR%
echo Timeout: %TIME_LIMIT% seconds per command
echo.
echo Paste ONE Ubuntu command, e.g.:
echo docker compose --env-file .env.prod logs -f --tail=100 postgres_prod
echo.
echo NOTE: logs -f stops automatically after %TIME_LIMIT% seconds.
echo NOTE: Do not paste passwords, tokens, or destructive commands.
echo Type EXIT to quit.
echo.
set "USER_CMD="
set /p "USER_CMD=Ubuntu command ^> "
if not defined USER_CMD goto :MENU
if /I "%USER_CMD%"=="EXIT" goto :DONE

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss_fff"') do set "STAMP=%%I"
set "OUTFILE=%OUTDIR%\oracle_capture_%STAMP%.txt"

echo.
echo Capturing remote output to:
echo %OUTFILE%
echo.
rem SSH stdout and stderr are redirected directly into Windows local file.
rem The remote process is limited to %TIME_LIMIT%s; exit 124 means timed out.
rem No --tty is used so logs are plain text.
(
 echo AlgoAgentX diagnostics
 echo Timestamp: %STAMP%
 echo Server: %SERVER%
 echo Command: %USER_CMD%
 echo Timeout: %TIME_LIMIT% seconds
 echo ================================================================
) > "%OUTFILE%"
ssh -o BatchMode=yes -o ConnectTimeout=12 -i "%KEY%" "%SERVER%" "cd %REMOTE_DIR% && timeout --signal=INT %TIME_LIMIT%s %USER_CMD%" >> "%OUTFILE%" 2>&1
set "RESULT=%ERRORLEVEL%"
echo.>> "%OUTFILE%"
echo SSH exit code: %RESULT%>> "%OUTFILE%"
if "%RESULT%"=="124" (
  echo Capture stopped at the safety time limit - normal for logs -f.
) else if not "%RESULT%"=="0" (
  echo WARNING: Remote command returned exit code %RESULT%. Check saved file.
) else (
  echo Command finished successfully.
)
echo Saved: %OUTFILE%
start "" notepad.exe "%OUTFILE%"
echo.
pause
goto :MENU

:DONE
echo Opening diagnostics directory...
start "" "%OUTDIR%"
exit /b 0
:ERROR
echo Please verify the SSH key and destination folder paths in this BAT file.
pause
exit /b 1
