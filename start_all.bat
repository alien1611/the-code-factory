@echo off
echo ===================================================
echo   STARTING THE CODE FACTORY PLATFORM
echo ===================================================

echo [1/2] Launching Backend Server on http://127.0.0.1:8000 ...
start "The Code Factory - Backend API" cmd /k "cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 3 /nobreak >nul

echo [2/2] Launching Frontend Dashboard on http://localhost:5173 ...
start "The Code Factory - Frontend UI" cmd /k "cd frontend && npm run dev"

echo.
echo ===================================================
echo   THE CODE FACTORY IS RUNNING!
echo   Frontend: http://localhost:5173
echo   Backend Docs: http://127.0.0.1:8000/docs
echo ===================================================
