@echo off
echo ========================================
echo Iniciando Portfolio Dashboard
echo ========================================
echo.
cd /d "%~dp0"
python -m streamlit run app.py
pause
