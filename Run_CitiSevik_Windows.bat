@echo off
cd /d "%~dp0app\backend"
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
pause
