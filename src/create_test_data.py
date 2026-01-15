"""
Genera un archivo Excel de prueba simulando un export de broker.
"""

import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
INPUT_DIR = PROJECT_ROOT / "data" / "input"

# Datos de prueba simulando cartera diversificada
test_data = {
    "Especie": [
        "SPY", "QQQ", "NVDA", "AMZN",           # USA/Tech
        "PAMP", "YPF", "GGAL", "TGS",           # Argentina
        "AL30D", "GD30", "T13F6", "S31E5",      # Renta Fija
        "GLD", "GOLD", "VALE",                   # Oro
        "SLV",                                   # Plata
        "IBIT", "ETHA",                         # Crypto
        "EWZ",                                  # Brasil
        "BHP", "URA",                           # Commodities
        "GAINVEST MM", "USD",                   # Liquidez
        "TICKER_RARO",                          # Sin clasificar
    ],
    "Descripción": [
        "SPDR S&P 500 ETF", "Invesco QQQ", "NVIDIA Corp", "Amazon.com",
        "Pampa Energía", "YPF SA ADR", "Grupo Galicia", "Transp. Gas Sur",
        "Bono AL30 Dólar", "Global 2030", "LECAP Feb 2026", "LECAP Ene 2025",
        "SPDR Gold Shares", "Barrick Gold", "Vale SA",
        "iShares Silver Trust",
        "iShares Bitcoin ETF", "iShares Ethereum ETF",
        "iShares MSCI Brazil",
        "BHP Group", "Global X Uranium ETF",
        "FCI Gainvest Money Market", "Dólares disponibles",
        "Activo desconocido",
    ],
    "Cantidad": [
        50, 30, 100, 25,
        500, 200, 1000, 300,
        10000, 5000, 50000, 100000,
        100, 200, 150,
        50,
        75, 50,
        100,
        80, 60,
        1, 5000,
        100,
    ],
    "Valorización": [
        29500.00, 15300.00, 14500.00, 5200.00,
        2500000.00, 1800000.00, 3500000.00, 900000.00,
        8500000.00, 4200000.00, 4800000.00, 9500000.00,
        24500.00, 4200.00, 2100.00,
        1450.00,
        6750.00, 2150.00,
        3800.00,
        8800.00, 1920.00,
        15000000.00, 5000.00,
        1500.00,
    ],
}

# Crear DataFrame
df = pd.DataFrame(test_data)

# Guardar como Excel
INPUT_DIR.mkdir(parents=True, exist_ok=True)
output_path = INPUT_DIR / "cartera_test_broker.xlsx"
df.to_excel(output_path, index=False, sheet_name="Posiciones")

print(f"Archivo de prueba creado: {output_path}")
print(f"\nDatos generados:")
print(df.to_string())
