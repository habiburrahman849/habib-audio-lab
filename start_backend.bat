@echo off
cd /d "d:\Wesite Projects\Ai audio Advanced"
echo Starting Habib Lab's AI Backend (API server on port 5000)...
venv\Scripts\python.exe backend\app.py > backend_log.txt 2>&1
echo Exit code: %errorlevel% >> backend_log.txt
pause