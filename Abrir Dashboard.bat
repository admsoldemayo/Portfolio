@echo off
title Portfolio Dashboard - Sol de Mayo
cd /d "%~dp0"
echo.
echo ====================================
echo   Portfolio Dashboard - Sol de Mayo
echo ====================================
echo.
echo Iniciando servidor...
start "" "http://localhost:8501"
python -m streamlit run app.py --server.headless true
pause
