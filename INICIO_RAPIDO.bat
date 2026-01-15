@echo off
cls
echo ========================================
echo Portfolio Dashboard - Sol de Mayo
echo ========================================
echo.
echo Este script va a:
echo 1. Verificar autenticacion con Google Sheets
echo 2. Iniciar el portal web en http://localhost:8501
echo.
echo IMPORTANTE: NO cierres esta ventana mientras uses el portal
echo.
pause

cd /d "%~dp0"

REM Verificar si existe token
if not exist "token.json" (
    echo.
    echo [!] No se encontro token de autenticacion
    echo [!] Ejecutando autenticacion...
    echo.
    python authenticate.py
    echo.
    if not exist "token.json" (
        echo [X] ERROR: La autenticacion fallo
        pause
        exit /b 1
    )
)

echo.
echo [OK] Token de autenticacion encontrado
echo [OK] Iniciando portal web...
echo.
echo ========================================
echo   PORTAL DISPONIBLE EN:
echo   http://localhost:8501
echo ========================================
echo.

python -m streamlit run app.py

pause
