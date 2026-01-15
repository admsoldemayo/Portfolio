"""
Parser de nombres de archivo de brokers
=======================================
Extrae metadata del nombre del archivo (comitente, nombre, fecha).
"""

import re
from datetime import datetime
from typing import Optional, Dict
from pathlib import Path


def parse_filename(filepath: str) -> Dict[str, Optional[str]]:
    """
    Extrae metadata del nombre del archivo.

    Formatos soportados:
    - Tenencias-34491_LOPEZ_JUAN ANTONIO-2026-01-10.xlsx
    - Tenencias -34491_LOPEZ_JUAN ANTONIO-2026-01-10 (1).xlsx
    - 34491_LOPEZ_JUAN ANTONIO_2026-01-10.xlsx

    Returns:
        dict con 'comitente', 'nombre', 'fecha' (YYYY-MM-DD)
    """
    filename = Path(filepath).stem  # Sin extensión

    # Eliminar sufijos tipo " (1)", " (2)", etc
    filename = re.sub(r'\s*\(\d+\)$', '', filename)

    # Patrón 1: Tenencias-{comitente}_{nombre}-{fecha}
    pattern1 = r'Tenencias\s*-?\s*(\d+)[_-]([A-Z\s_]+?)-(\d{4}-\d{2}-\d{2})'
    match = re.search(pattern1, filename, re.IGNORECASE)

    if match:
        comitente = match.group(1)
        nombre = match.group(2).strip().replace('_', ' ')
        fecha = match.group(3)

        return {
            'comitente': comitente,
            'nombre': nombre,
            'fecha': fecha,
        }

    # Patrón 2: {comitente}_{nombre}_{fecha}
    pattern2 = r'(\d+)[_-]([A-Z\s]+)[_-](\d{4}-\d{2}-\d{2})'
    match = re.search(pattern2, filename, re.IGNORECASE)

    if match:
        comitente = match.group(1)
        nombre = match.group(2).strip().replace('_', ' ')
        fecha = match.group(3)

        return {
            'comitente': comitente,
            'nombre': nombre,
            'fecha': fecha,
        }

    # Patrón 3: Buscar solo comitente (5-6 dígitos)
    pattern3 = r'(\d{5,6})'
    match = re.search(pattern3, filename)

    if match:
        comitente = match.group(1)

        # Intentar extraer fecha (YYYY-MM-DD o YYYY-DD-MM)
        fecha_pattern = r'(\d{4}[-_]\d{2}[-_]\d{2})'
        fecha_match = re.search(fecha_pattern, filename)
        fecha = fecha_match.group(1).replace('_', '-') if fecha_match else None

        return {
            'comitente': comitente,
            'nombre': None,
            'fecha': fecha,
        }

    # No se pudo parsear
    return {
        'comitente': None,
        'nombre': None,
        'fecha': None,
    }


def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """
    Normaliza una fecha a formato YYYY-MM-DD.
    Intenta diferentes formatos comunes.
    """
    if not date_str:
        return None

    formats = [
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%Y_%m_%d',
        '%d-%m-%Y',
        '%d/%m/%Y',
        '%Y%m%d',
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue

    return date_str  # Devolver original si no se pudo parsear


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    test_files = [
        "Tenencias-34491_LOPEZ_JUAN ANTONIO-2026-01-10.xlsx",
        "Tenencias -34491_LOPEZ_JUAN ANTONIO-2026-01-10 (1).xlsx",
        "Tenencias-34462_LOPEZ ROJAS_PEDRO-2026-01-09.xlsx",
        "34491_LOPEZ_JUAN ANTONIO_2026-01-10.xlsx",
        "Cartera_34491_2026-01-10.xlsx",
        "archivo_sin_patron.xlsx",
    ]

    print("=" * 70)
    print("TEST DE PARSER DE FILENAMES")
    print("=" * 70)
    print()

    for filename in test_files:
        result = parse_filename(filename)
        print(f"Archivo: {filename}")
        print(f"  Comitente: {result['comitente']}")
        print(f"  Nombre:    {result['nombre']}")
        print(f"  Fecha:     {result['fecha']}")
        print()
