"""
Test de actualizacion de clasificaciones
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sheets_manager import get_sheets_manager, SHEET_DETALLE_ACTIVOS

def test_update():
    print("Conectando...")
    sheets = get_sheets_manager()

    comitente = "34455"
    ticker = "ARS"  # Un ticker que existe

    print(f"\n1. Buscando {ticker} para comitente {comitente}...")

    # Leer datos actuales
    data = sheets._read_all(SHEET_DETALLE_ACTIVOS)

    # Buscar el activo
    found = None
    found_idx = None
    for i, row in enumerate(data):
        if (str(row.get('comitente', '')).strip() == comitente and
            row.get('ticker', '').upper().strip() == ticker):
            found = row
            found_idx = i
            break

    if not found:
        print(f"No encontrado {ticker} para {comitente}")
        return

    print(f"   Encontrado en fila {found_idx + 2}")
    print(f"   Categoria actual: {found.get('categoria')}")
    print(f"   Sector actual: {found.get('sector')}")

    # Test: Actualizar categoria
    test_cat = "LIQUIDEZ"  # Deberia ser la misma
    test_sector = "N/A"

    print(f"\n2. Actualizando clasificacion...")
    print(f"   Nueva categoria: {test_cat}")
    print(f"   Nuevo sector: {test_sector}")

    success = sheets.update_activo_classification(
        comitente=comitente,
        ticker=ticker,
        categoria=test_cat,
        sector=test_sector
    )

    print(f"   Resultado: {'OK' if success else 'FALLO'}")

    # Verificar cambio
    print(f"\n3. Verificando cambio...")
    data_after = sheets._read_all(SHEET_DETALLE_ACTIVOS)

    for row in data_after:
        if (str(row.get('comitente', '')).strip() == comitente and
            row.get('ticker', '').upper().strip() == ticker):
            print(f"   Categoria ahora: {row.get('categoria')}")
            print(f"   Sector ahora: {row.get('sector')}")
            break

    # Test con cambio real
    print(f"\n4. Test con cambio real (LIQUIDEZ -> OTROS -> LIQUIDEZ)...")

    # Cambiar a OTROS
    sheets.update_activo_classification(comitente, ticker, categoria="OTROS")
    data_check = sheets._read_all(SHEET_DETALLE_ACTIVOS)
    for row in data_check:
        if (str(row.get('comitente', '')).strip() == comitente and
            row.get('ticker', '').upper().strip() == ticker):
            print(f"   Despues de cambiar a OTROS: {row.get('categoria')}")
            break

    # Volver a LIQUIDEZ
    sheets.update_activo_classification(comitente, ticker, categoria="LIQUIDEZ")
    data_check = sheets._read_all(SHEET_DETALLE_ACTIVOS)
    for row in data_check:
        if (str(row.get('comitente', '')).strip() == comitente and
            row.get('ticker', '').upper().strip() == ticker):
            print(f"   Despues de volver a LIQUIDEZ: {row.get('categoria')}")
            break

    print("\nTest completado!")


if __name__ == "__main__":
    test_update()
