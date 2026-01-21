"""Verificar datos en historial_tenencias"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sheets_manager import get_sheets_manager, SHEET_HISTORIAL

def check():
    print("Conectando...")
    sheets = get_sheets_manager()

    # Leer historial
    result = sheets.sheets_service.spreadsheets().values().get(
        spreadsheetId=sheets.spreadsheet_id,
        range=f"{SHEET_HISTORIAL}!A1:G10"
    ).execute()

    values = result.get('values', [])
    print(f"\nHistorial tenencias - {len(values)} filas (incluyendo header):")
    for i, row in enumerate(values[:10]):
        print(f"  Fila {i}: {row}")

    # Contar por comitente
    data = sheets._read_all(SHEET_HISTORIAL)
    print(f"\nTotal registros en historial: {len(data)}")

    if data:
        comitentes = set(str(row.get('comitente', '')).strip() for row in data)
        print(f"Comitentes con datos: {comitentes}")

if __name__ == "__main__":
    check()
