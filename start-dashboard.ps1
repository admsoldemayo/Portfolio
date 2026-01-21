# Portfolio Dashboard Launcher
# ============================
# Inicia el servidor Streamlit y abre el navegador

$ErrorActionPreference = "Stop"
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "  Portfolio Dashboard - Sol de Mayo" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Cambiar al directorio del proyecto
Set-Location $scriptPath

# Verificar que streamlit existe
try {
    $streamlitVersion = streamlit --version 2>$null
    Write-Host "Streamlit: $streamlitVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Streamlit no encontrado. Instalando..." -ForegroundColor Red
    pip install streamlit
}

Write-Host ""
Write-Host "Iniciando servidor en http://localhost:8501" -ForegroundColor Yellow
Write-Host "Presiona Ctrl+C para detener el servidor" -ForegroundColor Gray
Write-Host ""

# Abrir navegador despues de 2 segundos
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:8501"
} | Out-Null

# Iniciar streamlit
streamlit run app.py --server.headless true
