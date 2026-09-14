@echo off
title MT5 Agent - Port 8000

:: Navigate to project root
cd /d "D:\Stock_market\algoagentx\AlgoAgentXAPI\AlgoAgentXMT5Agent"

:: Set Python
set PYTHONPATH=%CD%

:: Activate shared virtual environment
call "D:\Stock_market\algoagentx\AlgoAgentXAPI\.venv\Scripts\activate.bat"
echo.

python main.py

pause
