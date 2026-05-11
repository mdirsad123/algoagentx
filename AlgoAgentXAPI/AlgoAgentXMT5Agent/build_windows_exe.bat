@echo off
setlocal
cd /d %~dp0
if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
pyinstaller --onefile --name AlgoAgentXMT5Agent main.py
copy config.json.example dist\config.json.example >nul
pause
