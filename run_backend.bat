@echo off
title The Code Factory - Backend Server
echo ==========================================
echo Starting The Code Factory Verification Backend
echo ==========================================
cd /d "%~dp0\backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
