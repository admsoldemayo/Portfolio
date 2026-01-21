"""
Diagnóstico de datos en detalle_activos
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sheets_manager import get_sheets_manager, SHEET_DETALLE_ACTIVOS

def diagnose():
    print("Conectando a Google Sheets...")
    sheets = get_sheets_manager()

    # Leer datos crudos
    result = sheets.sheets_service.spreadsheets().values().get(
        spreadsheetId=sheets.spreadsheet_id,
        range=f"{SHEET_DETALLE_ACTIVOS}!A1:M10"
    ).execute()

    values = result.get('values', [])

    print("\n" + "=" * 80)
    print("PRIMERAS 10 FILAS DE detalle_activos:")
    print("=" * 80)

    for i, row in enumerate(values):
        print(f"\nFila {i}: ({len(row)} columnas)")
        for j, val in enumerate(row):
            col_letter = chr(65 + j)  # A, B, C...
            print(f"  [{col_letter}] = '{val}'")

    # Verificar estructura
    if values:
        header = values[0]
        print("\n" + "=" * 80)
        print("ANÁLISIS DE HEADER:")
        print("=" * 80)
        print(f"Columnas: {len(header)}")
        for i, h in enumerate(header):
            col_letter = chr(65 + i)
            print(f"  {col_letter}: {h}")

        expected = ['fecha', 'comitente', 'nombre', 'ticker', 'descripcion',
                    'cantidad', 'precio', 'valor', 'categoria', 'sector', 'tc_mep', 'tc_ccl']

        print(f"\nHeader esperado: {expected}")
        print(f"Header actual:   {header}")

        if header == expected:
            print("\n✅ Header correcto")
        else:
            print("\n❌ Header incorrecto")

        # Verificar datos
        if len(values) > 1:
            first_data = values[1]
            print(f"\nPrimera fila de datos tiene {len(first_data)} columnas")
            if len(first_data) != len(header):
                print(f"⚠️ PROBLEMA: Header tiene {len(header)} cols, datos tienen {len(first_data)}")

if __name__ == "__main__":
    diagnose()
