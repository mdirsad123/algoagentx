@echo off
title Connect Ubuntu - AlgoAgentX

cd /d "D:\Stock_market\algoagentx\docs\oracle_cloud_keys"

echo Connecting to Ubuntu Server...
echo.

ssh -i ".\ssh-key-private.key" ubuntu@130.210.58.143

echo.
echo SSH connection closed.
pause