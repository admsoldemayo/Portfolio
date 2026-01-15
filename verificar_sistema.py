"""
Script de Verificación del Sistema
====================================
Verifica que todo esté configurado correctamente.
"""

import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 70)
print("VERIFICACIÓN DEL SISTEMA - Portfolio Automation")
print("=" * 70)
print()

# 1. Verificar imports
print("1. Verificando imports...")
try:
    import pandas as pd
    import streamlit as st
    import plotly.express as px
    from google.oauth2.credentials import Credentials
    print("   ✅ Todas las dependencias instaladas")
except ImportError as e:
    print(f"   ❌ Error: {e}")
    print("   Ejecuta: pip install streamlit plotly pandas openpyxl google-auth google-auth-oauthlib google-api-python-client")
    sys.exit(1)

# 2. Verificar módulos propios
print()
print("2. Verificando módulos del proyecto...")
try:
    from config import KNOWN_PORTFOLIOS, SPREADSHEET_ID, DEFAULT_PROFILES
    from asset_mapper import classify_asset
    from sheets_manager import get_sheets_manager
    from portfolio_tracker import PortfolioTracker
    from allocation_manager import AllocationManager
    print("   ✅ Todos los módulos del proyecto OK")
except ImportError as e:
    print(f"   ❌ Error importando módulos: {e}")
    sys.exit(1)

# 3. Verificar archivos de configuración
print()
print("3. Verificando archivos de configuración...")

credentials_file = Path(__file__).parent / "credentials.json"
token_file = Path(__file__).parent / "token.json"

if credentials_file.exists():
    print("   ✅ credentials.json existe")
else:
    print("   ❌ credentials.json NO existe")
    print("      Descarga las credenciales de Google Cloud Console")

if token_file.exists():
    print("   ✅ token.json existe (autenticado)")
else:
    print("   ⚠️  token.json NO existe (necesitas autenticar)")
    print("      Ejecuta: python authenticate.py")

# 4. Verificar conexión con Google Sheets
print()
print("4. Verificando conexión con Google Sheets...")

if token_file.exists():
    try:
        sheets = get_sheets_manager()
        print(f"   ✅ Conexión exitosa")
        print(f"   📊 Spreadsheet ID: {SPREADSHEET_ID}")
        print(f"   🔗 URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")

        # Verificar hojas
        df_carteras = sheets.get_carteras_maestro()
        df_perfiles = sheets.get_perfiles_alocacion()

        print(f"   ✅ Carteras configuradas: {len(df_carteras)}")
        print(f"   ✅ Perfiles configurados: {df_perfiles['perfil'].nunique() if not df_perfiles.empty else 0}")

    except Exception as e:
        print(f"   ❌ Error conectando con Google Sheets: {e}")
        print("      Ejecuta: python authenticate.py")
else:
    print("   ⏭️  Saltando (no hay token)")

# 5. Verificar configuración de carteras
print()
print("5. Verificando configuración de carteras...")
print(f"   ✅ {len(KNOWN_PORTFOLIOS)} carteras configuradas:")
for comitente, info in KNOWN_PORTFOLIOS.items():
    print(f"      - {comitente}: {info['nombre']} ({info['perfil']})")

# 6. Verificar perfiles de alocación
print()
print("6. Verificando perfiles de alocación...")
print(f"   ✅ {len(DEFAULT_PROFILES)} perfiles definidos:")
for perfil in DEFAULT_PROFILES.keys():
    print(f"      - {perfil}")

# 7. Verificar clasificador de activos
print()
print("7. Verificando clasificador de activos...")
test_tickers = {
    'SPY': 'SPY',
    'QQQ': 'SPY',
    'YPFD': 'MERV',
    'AL30': 'LETRAS',
    'GLD': 'GLD',
    'USD': 'LIQUIDEZ'
}

errors = []
for ticker, expected_cat in test_tickers.items():
    result = classify_asset(ticker, '')
    if result == expected_cat:
        print(f"   ✅ {ticker} → {result}")
    else:
        print(f"   ❌ {ticker} → {result} (esperado: {expected_cat})")
        errors.append(ticker)

if not errors:
    print("   ✅ Clasificador funcionando correctamente")

# 8. Resumen final
print()
print("=" * 70)
print("RESUMEN DE VERIFICACIÓN")
print("=" * 70)

checks = {
    "Dependencias": credentials_file.exists() or token_file.exists(),
    "Módulos del proyecto": True,
    "Archivos de configuración": credentials_file.exists(),
    "Autenticación": token_file.exists(),
    "Carteras configuradas": len(KNOWN_PORTFOLIOS) == 8,
    "Perfiles configurados": len(DEFAULT_PROFILES) == 3,
}

all_ok = all(checks.values())

for check, status in checks.items():
    symbol = "✅" if status else "❌"
    print(f"{symbol} {check}")

print()
if all_ok and token_file.exists():
    print("🎉 TODO CONFIGURADO CORRECTAMENTE")
    print()
    print("Próximos pasos:")
    print("  1. Ejecuta: streamlit run app.py")
    print("  2. Abre: http://localhost:8501")
    print("  3. Sube un archivo Excel para probar")
elif not token_file.exists():
    print("⚠️  FALTA AUTENTICACIÓN")
    print()
    print("Ejecuta:")
    print("  python authenticate.py")
else:
    print("⚠️  VERIFICACIÓN INCOMPLETA")
    print()
    print("Revisa los errores arriba y corrige la configuración")

print("=" * 70)
