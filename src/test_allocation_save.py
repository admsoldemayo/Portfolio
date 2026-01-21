"""
Test de guardado de alocación custom
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sheets_manager import get_sheets_manager, SHEET_CUSTOM

def test_save():
    print("Conectando a Google Sheets...")
    sheets = get_sheets_manager()

    comitente = "34455"

    # 1. Verificar estructura de la hoja alocacion_custom
    print(f"\n1. Verificando hoja '{SHEET_CUSTOM}'...")

    try:
        result = sheets.sheets_service.spreadsheets().values().get(
            spreadsheetId=sheets.spreadsheet_id,
            range=f"{SHEET_CUSTOM}!A1:C10"
        ).execute()

        values = result.get('values', [])
        print(f"   Filas encontradas: {len(values)}")
        for i, row in enumerate(values[:5]):
            print(f"   Fila {i}: {row}")
    except Exception as e:
        print(f"   ERROR leyendo hoja: {e}")
        return

    # 2. Leer alocación actual del comitente
    print(f"\n2. Alocación actual para comitente {comitente}:")
    current = sheets.get_target_allocation(comitente)
    for cat, pct in current.items():
        if pct > 0:
            print(f"   {cat}: {pct}%")

    # 3. Test de guardado BATCH
    print(f"\n3. Guardando alocacion completa (batch)...")
    test_allocation = {
        "SPY": 25.0,
        "MERV": 20.0,
        "BONOS_SOBERANOS_USD": 0.0,
        "LETRAS": 25.0,
        "GLD": 15.0,
        "SLV": 0.0,
        "CRYPTO_BTC": 0.0,
        "CRYPTO_ETH": 0.0,
        "BRASIL": 0.0,
        "EXTRAS_COBRE": 0.0,
        "LIQUIDEZ": 15.0,
        "OTROS": 0.0
    }
    try:
        sheets.set_custom_allocation_batch(comitente, test_allocation)
        print("   OK - Guardado batch exitoso")
    except Exception as e:
        print(f"   ERROR: {e}")
        return

    # 4. Verificar que se guardó
    print(f"\n4. Verificando guardado...")
    result = sheets.sheets_service.spreadsheets().values().get(
        spreadsheetId=sheets.spreadsheet_id,
        range=f"{SHEET_CUSTOM}!A:C"
    ).execute()

    values = result.get('values', [])
    print(f"   Filas totales: {len(values)}")

    # Buscar el registro
    found = False
    for row in values[1:]:  # Skip header
        if len(row) >= 3 and str(row[0]).strip() == comitente:
            print(f"   Encontrado: {row}")
            found = True

    if not found:
        print(f"   WARN: No se encontro ningún registro para {comitente}")

    # 5. Releer alocación
    print(f"\n5. Releyendo alocacion despues de guardar:")
    new_alloc = sheets.get_target_allocation(comitente)
    for cat, pct in new_alloc.items():
        if pct > 0:
            print(f"   {cat}: {pct}%")

    print("\nTest completado")

if __name__ == "__main__":
    test_save()
