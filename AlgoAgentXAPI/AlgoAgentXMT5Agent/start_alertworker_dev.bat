@echo off
title Alert Worker

:: Navigate to project root
cd /d "D:\Stock_market\algoagentx\AlgoAgentXAPI"

:: Set Python
set PYTHONPATH=%CD%
if "%LOG_LEVEL%"=="" set LOG_LEVEL=ERROR

:: Activate shared virtual environment
call "D:\Stock_market\algoagentx\AlgoAgentXAPI\.venv\Scripts\activate.bat"
echo.

python -m app.services.alerts.worker

pause
