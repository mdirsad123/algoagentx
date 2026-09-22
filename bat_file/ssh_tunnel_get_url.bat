@echo off
title AlgoAgentX - SSH Tunnel

cd /d "D:\Stock_market\algoagentx\docs\oracle_cloud_keys"

echo ========================================
echo Starting AlgoAgentX SSH Tunnel
echo ========================================
echo.
echo Frontend: http://localhost:3000
echo API:      http://localhost:8000
echo.
echo Keep this window OPEN while using AlgoAgentX.
echo Press Ctrl+C to stop the tunnel.
echo.

ssh -N ^
  -o ServerAliveInterval=60 ^
  -o ServerAliveCountMax=3 ^
  -i ".\ssh-key-private.key" ^
  -L 3000:127.0.0.1:3000 ^
  -L 8000:127.0.0.1:8000 ^
  ubuntu@130.210.58.143

echo.
echo SSH tunnel disconnected.
pause