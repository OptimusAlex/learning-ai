@echo off
rem Starts My AI Cohort and opens it in the browser. Close this window to stop the app.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run: setting up the app...
  python -m venv .venv || goto :fail
  ".venv\Scripts\python.exe" -m pip install -q -r study-app\requirements.txt || goto :fail
)
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://localhost:8000"
echo My AI Cohort is running at http://localhost:8000  (close this window to stop it)
".venv\Scripts\python.exe" -m uvicorn app:app --app-dir study-app --port 8000
goto :eof
:fail
echo Setup failed. Take a screenshot of this window and show it to Claude.
pause
