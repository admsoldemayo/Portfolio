"""
Migración: Agregar columna sector a datos existentes
=====================================================
Este script actualiza los registros existentes en detalle_activos
agregando la clasificación por sector industrial.

Ejecutar una sola vez después de agregar la funcionalidad de sectores.
"""

import sys
import logging
from pathlib import Path

# Agregar el directorio src al path
sys.path.insert(0, str(Path(__file__).parent))

from sheets_manager import get_sheets_manager, SHEET_DETALLE_ACTIVOS
from asset_mapper import classify_sector, normalize_ticker
from config import SECTORS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def migrate_add_sector_column():
    """
    Agrega la columna sector a todos los registros existentes en detalle_activos.
    Usa batch update para evitar rate limits.
    """
    logger.info("Iniciando migración: agregar columna sector")

    try:
        sheets = get_sheets_manager()

        # Leer todos los datos
        data = sheets._read_all(SHEET_DETALLE_ACTIVOS)

        if not data:
            logger.info("No hay datos en detalle_activos para migrar")
            return 0

        logger.info(f"Encontrados {len(data)} registros para procesar")

        # Verificar si ya tiene sector
        if data and 'sector' in data[0] and data[0].get('sector'):
            logger.info("Los datos ya tienen columna sector. Verificando valores vacíos...")

        # Preparar todos los valores de sector
        sector_values = []
        updated_count = 0
        skipped_count = 0

        for i, row in enumerate(data):
            ticker = row.get('ticker', '')
            categoria = row.get('categoria', 'OTROS')
            current_sector = row.get('sector', '').strip()

            # Solo actualizar si no tiene sector o es vacío
            if not current_sector or current_sector not in SECTORS:
                # Calcular sector
                new_sector = classify_sector(ticker, categoria)
                sector_values.append([new_sector])
                logger.info(f"  [{i+1}/{len(data)}] {ticker}: {categoria} -> sector: {new_sector}")
                updated_count += 1
            else:
                # Mantener el valor actual
                sector_values.append([current_sector])
                skipped_count += 1

        # Hacer batch update de toda la columna J (sector)
        if sector_values:
            range_name = f"{SHEET_DETALLE_ACTIVOS}!J2:J{len(data)+1}"
            sheets.sheets_service.spreadsheets().values().update(
                spreadsheetId=sheets.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body={'values': sector_values}
            ).execute()
            logger.info(f"\nBatch update completado para {len(sector_values)} registros")

        logger.info(f"\nMigración completada:")
        logger.info(f"  - Registros actualizados: {updated_count}")
        logger.info(f"  - Registros omitidos (ya tenían sector): {skipped_count}")

        return updated_count

    except Exception as e:
        logger.error(f"Error en migración: {e}")
        raise


def verify_header_has_sector():
    """
    Verifica que el header de detalle_activos incluya 'sector'.
    Si no lo tiene, actualiza el header.
    """
    logger.info("Verificando header de detalle_activos...")

    try:
        sheets = get_sheets_manager()

        # Leer solo el header
        result = sheets.sheets_service.spreadsheets().values().get(
            spreadsheetId=sheets.spreadsheet_id,
            range=f"{SHEET_DETALLE_ACTIVOS}!A1:L1"
        ).execute()

        headers = result.get('values', [[]])[0]
        logger.info(f"Headers actuales: {headers}")

        # Verificar si 'sector' está en la posición correcta (índice 9, columna J)
        expected_headers = [
            'fecha', 'comitente', 'nombre', 'ticker', 'descripcion',
            'cantidad', 'precio', 'valor', 'categoria', 'sector', 'tc_mep', 'tc_ccl'
        ]

        if len(headers) < 10 or headers[9] != 'sector':
            logger.info("Header no tiene 'sector'. Actualizando...")

            # Actualizar header completo
            sheets.sheets_service.spreadsheets().values().update(
                spreadsheetId=sheets.spreadsheet_id,
                range=f"{SHEET_DETALLE_ACTIVOS}!A1:L1",
                valueInputOption='USER_ENTERED',
                body={'values': [expected_headers]}
            ).execute()

            logger.info("Header actualizado correctamente")
            return True
        else:
            logger.info("Header ya incluye 'sector' en la posición correcta")
            return False

    except Exception as e:
        logger.error(f"Error verificando header: {e}")
        raise


if __name__ == "__main__":
    print("=" * 60)
    print("MIGRACIÓN: Agregar columna SECTOR a detalle_activos")
    print("=" * 60)

    # Paso 1: Verificar y actualizar header si es necesario
    print("\n[1/2] Verificando header...")
    verify_header_has_sector()

    # Paso 2: Actualizar datos existentes
    print("\n[2/2] Actualizando datos existentes...")
    count = migrate_add_sector_column()

    print("\n" + "=" * 60)
    print(f"Migración completada. {count} registros actualizados.")
    print("=" * 60)
