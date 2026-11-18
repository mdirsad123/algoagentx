@echo off
setlocal DisableDelayedExpansion
title Oracle Ubuntu - RustDesk Server Manager (Passwordless)

REM This file requires rustdesk_passwordless_setup.sh beside it for one-time SETUP.
REM After SETUP, ADD/REMOVE/CHECK need no sudo password.
REM Your SSH key continues to authenticate SSH.

set "SSH_KEY=D:\Stock_market\algoagentx\docs\oracle_cloud_keys\ssh-key-private.key"
set "SSH_TARGET=ubuntu@130.210.58.143"
set "SETUP_FILE=%~dp0rustdesk_passwordless_setup.sh"
set "REMOTE_SCRIPT=/usr/local/sbin/rustdesk-server-manager"

if not exist "%SSH_KEY%" (
  echo [ERROR] SSH key not found: %SSH_KEY%
  pause
  exit /b 1
)
where ssh.exe >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Windows OpenSSH client is missing.
  pause
  exit /b 1
)

:MENU
cls
echo ==========================================================
echo      ORACLE UBUNTU - RUSTDESK SERVER MANAGER
echo                  NO PASSWORD EDITION
echo ==========================================================
echo.
echo    1 / ADD     - Configure custom RustDesk server
echo    2 / REMOVE  - Clear all custom server values
echo    3 / CHECK   - Show current RustDesk settings
echo    4 / SETUP   - ONE TIME passwordless-sudo setup
echo    5 / EXIT    - Close program
echo.
echo First time: use option 4 and enter Ubuntu password once.
echo Later: use 1/2/3 WITHOUT a sudo password.
echo ==========================================================
set "ACTION="
set /p "ACTION=Choose (1-5 or ADD/REMOVE/CHECK/SETUP/EXIT): "
if /I "%ACTION%"=="1" goto ADD
if /I "%ACTION%"=="ADD" goto ADD
if /I "%ACTION%"=="2" goto REMOVE
if /I "%ACTION%"=="REMOVE" goto REMOVE
if /I "%ACTION%"=="3" goto CHECK
if /I "%ACTION%"=="CHECK" goto CHECK
if /I "%ACTION%"=="4" goto SETUP
if /I "%ACTION%"=="SETUP" goto SETUP
if /I "%ACTION%"=="5" goto END
if /I "%ACTION%"=="EXIT" goto END
echo [ERROR] Invalid choice.
pause
goto MENU

:SETUP
cls
echo [SETUP] One-time permission setup on Ubuntu.
echo This is the ONLY step that should request your sudo password.
echo.
if not exist "%SETUP_FILE%" (
  echo [ERROR] Setup file missing: %SETUP_FILE%
  echo Extract BOTH files from the ZIP into the same directory.
  pause
  goto MENU
)
where scp.exe >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Windows scp.exe not found.
  pause
  goto MENU
)
echo [1/3] Uploading setup script to the Ubuntu user's home directory...
scp -o ConnectTimeout=12 -o IdentitiesOnly=yes -i "%SSH_KEY%" "%SETUP_FILE%" "%SSH_TARGET%:rustdesk_passwordless_setup.sh"
if errorlevel 1 (
  echo [ERROR] Upload failed.
  pause
  goto MENU
)
echo.
echo [2/3] Installing restricted root-owned RustDesk manager...
ssh -tt -o ConnectTimeout=12 -o ServerAliveInterval=20 -o IdentitiesOnly=yes -i "%SSH_KEY%" %SSH_TARGET% "sudo /bin/bash /home/ubuntu/rustdesk_passwordless_setup.sh"
if errorlevel 1 (
  echo [ERROR] One-time setup failed. Inspect the SSH output above.
  pause
  goto MENU
)
echo.
echo [3/3] Verifying passwordless CHECK (no prompt should appear)...
ssh -T -o ConnectTimeout=12 -o IdentitiesOnly=yes -i "%SSH_KEY%" %SSH_TARGET% "sudo -n /usr/local/sbin/rustdesk-server-manager check"
if errorlevel 1 (
  echo [ERROR] Permission check failed. Review setup output.
) else (
  echo [OK] Setup completed. ADD/REMOVE/CHECK will not ask for sudo password.
)
echo.
echo To remove the installer from Ubuntu after setup, run:
echo   rm -f /home/ubuntu/rustdesk_passwordless_setup.sh
pause
goto MENU

:ADD
cls
echo [ADD] Applying custom RustDesk server configuration...
echo ID Server: 3.7.212.218
echo Relay:     3.7.212.218
echo API:       Empty
echo.
ssh -T -o ConnectTimeout=12 -o ServerAliveInterval=20 -o IdentitiesOnly=yes -i "%SSH_KEY%" %SSH_TARGET% "sudo -n /usr/local/sbin/rustdesk-server-manager add"
if errorlevel 1 (
  echo [ERROR] Could not ADD. First run option 4 SETUP, or check SSH/RustDesk status.
) else (
  echo [OK] RustDesk custom server settings updated.
)
pause
goto MENU

:REMOVE
cls
echo [REMOVE] Clear ALL custom RustDesk server settings and use public servers.
echo Existing RustDesk sessions may disconnect.
echo.
set "CONFIRM="
set /p "CONFIRM=Type YES to continue: "
if /I not "%CONFIRM%"=="YES" goto MENU
ssh -T -o ConnectTimeout=12 -o ServerAliveInterval=20 -o IdentitiesOnly=yes -i "%SSH_KEY%" %SSH_TARGET% "sudo -n /usr/local/sbin/rustdesk-server-manager remove"
if errorlevel 1 (
  echo [ERROR] Could not REMOVE. First run option 4 SETUP, or check SSH/RustDesk status.
) else (
  echo [OK] RustDesk custom server configuration cleared.
)
pause
goto MENU

:CHECK
cls
echo [CHECK] Reading Ubuntu RustDesk settings...
echo.
ssh -T -o ConnectTimeout=12 -o ServerAliveInterval=20 -o IdentitiesOnly=yes -i "%SSH_KEY%" %SSH_TARGET% "sudo -n /usr/local/sbin/rustdesk-server-manager check"
if errorlevel 1 (
  echo [ERROR] CHECK failed. First run option 4 SETUP, or check SSH/RustDesk status.
)
pause
goto MENU

:END
endlocal
exit /b 0
