"""
Script para corregir la migración de datos
==========================================
La migración anterior corrompió datos:
- Header tiene 12 columnas
- Datos tienen 11 columnas (falta tc_ccl)

Este script arregla agregando tc_ccl a cada fila de datos.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sheets_manager import get_sheets_manager, SHEET_DETALLE_ACTIVOS

def fix_data():
    print("Conectando a Google Sheets...")
    sheets = get_sheets_manager()

    # Leer TODOS los datos crudos
    result = sheets.sheets_service.spreadsheets().values().get(
        spreadsheetId=sheets.spreadsheet_id,
        range=f"{SHEET_DETALLE_ACTIVOS}!A1:M"
    ).execute()

    values = result.get('values', [])

    if len(values) < 2:
        print("No hay datos para corregir")
        return

    header = values[0]
    print(f"Header: {header}")
    print(f"Total filas de datos: {len(values) - 1}")

    # Verificar que el header tenga 12 columnas
    expected_header = ['fecha', 'comitente', 'nombre', 'ticker', 'descripcion',
                       'cantidad', 'precio', 'valor', 'categoria', 'sector', 'tc_mep', 'tc_ccl']

    if header != expected_header:
        print(f"Header incorrecto. Actualizando...")
        sheets.sheets_service.spreadsheets().values().update(
            spreadsheetId=sheets.spreadsheet_id,
            range=f"{SHEET_DETALLE_ACTIVOS}!A1:L1",
            valueInputOption='USER_ENTERED',
            body={'values': [expected_header]}
        ).execute()
        print("Header actualizado")

    # Contar filas que necesitan fix
    rows_to_fix = []
    for i, row in enumerate(values[1:], start=2):  # start=2 because row 1 is header
        if len(row) < 12:
            # Necesita agregar tc_ccl
            rows_to_fix.append((i, row))

    print(f"\nFilas que necesitan correccion: {len(rows_to_fix)}")

    if not rows_to_fix:
        print("Todos los datos estan correctos!")
        return

    # Corregir cada fila agregando tc_ccl = tc_mep si falta
    print("\nCorrigiendo datos...")

    # Para hacer esto eficientemente, vamos a:
    # 1. Leer el valor de K (que deberia ser tc_mep)
    # 2. Copiarlo a L como tc_ccl

    # Preparar datos para batch update
    updates = []
    for row_num, row in rows_to_fix:
        # Si la fila tiene 11 columnas, agregar tc_ccl
        if len(row) == 11:
            tc_mep = row[10] if len(row) > 10 else '0'  # Column K
            tc_ccl = tc_mep  # Usar el mismo valor
            updates.append({
                'range': f"{SHEET_DETALLE_ACTIVOS}!L{row_num}",
                'values': [[tc_ccl]]
            })

    # Ejecutar batch update
    if updates:
        body = {
            'valueInputOption': 'USER_ENTERED',
            'data': updates
        }
        sheets.sheets_service.spreadsheets().values().batchUpdate(
            spreadsheetId=sheets.spreadsheet_id,
            body=body
        ).execute()
        print(f"Actualizadas {len(updates)} filas")

    print("\nVerificando resultado...")

    # Verificar
    result = sheets.sheets_service.spreadsheets().values().get(
        spreadsheetId=sheets.spreadsheet_id,
        range=f"{SHEET_DETALLE_ACTIVOS}!A1:L5"
    ).execute()

    values = result.get('values', [])
    for i, row in enumerate(values):
        print(f"Fila {i}: {len(row)} columnas")

    print("\nCorreccion completada!")


def check_comitente_data(comitente: str):
    """Verifica si hay datos para un comitente especifico."""
    print(f"\nBuscando datos para comitente {comitente}...")
    sheets = get_sheets_manager()

    # Leer todos los datos
    data = sheets._read_all(SHEET_DETALLE_ACTIVOS)
    comitente_str = str(comitente).strip()

    matching = [row for row in data if str(row.get('comitente', '')).strip() == comitente_str]

    print(f"Encontradas {len(matching)} filas para comitente {comitente}")

    if matching:
        print("\nPrimeros 3 registros:")
        for row in matching[:3]:
            print(f"  - {row.get('ticker')}: {row.get('valor')} ({row.get('categoria')})")

    return len(matching)


if __name__ == "__main__":
    print("=" * 60)
    print("FIX DE MIGRACION DE DATOS")
    print("=" * 60)

    fix_data()

    print("\n" + "=" * 60)
    print("VERIFICACION DE COMITENTES")
    print("=" * 60)

    # Verificar comitentes que interesan
    for com in ['34455', '34462', '242928']:
        check_comitente_data(com)
