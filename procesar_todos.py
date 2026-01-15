"""
Script para procesar todos los archivos de tenencias de Downloads
y guardarlos en Google Sheets
"""

import os
import sys
import glob
from pathlib import Path
from datetime import datetime

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ingest import process_single_file, save_to_sheets
from config import KNOWN_PORTFOLIOS

def main():
    print("=" * 70)
    print("PROCESADOR MASIVO DE TENENCIAS")
    print("=" * 70)
    print()

    # Buscar archivos en Downloads
    downloads_path = Path(os.path.expanduser("~")) / "Downloads"
    pattern = str(downloads_path / "Tenencias*.xlsx")

    files = glob.glob(pattern)

    # Filtrar archivos temporales
    files = [f for f in files if not os.path.basename(f).startswith("~$")]

    if not files:
        print(f"No se encontraron archivos en {downloads_path}")
        return

    print(f"Encontrados {len(files)} archivos para procesar")
    print()

    # Ordenar por fecha (del más antiguo al más reciente)
    files.sort()

    # Contadores
    procesados = 0
    errores = 0
    guardados = 0

    # Procesar cada archivo
    for i, filepath in enumerate(files, 1):
        filename = os.path.basename(filepath)
        print(f"[{i}/{len(files)}] {filename}")

        try:
            # Procesar archivo
            df = process_single_file(filepath)

            if df.empty:
                print(f"    -> VACÍO (sin datos)")
                errores += 1
                continue

            procesados += 1

            # Verificar si tiene metadata válida
            comitente = df.iloc[0].get('comitente', '')
            fecha = df.iloc[0].get('fecha_archivo', '')

            if not comitente or comitente not in KNOWN_PORTFOLIOS:
                print(f"    -> COMITENTE NO RECONOCIDO: {comitente}")
                # Intentar igual
                pass

            # Guardar en Google Sheets
            results = save_to_sheets(df, auto_save=True)

            if results:
                for com, result in results.items():
                    if 'error' in result:
                        print(f"    -> ERROR: {result['error']}")
                        errores += 1
                    else:
                        valor_total = df['valor'].sum()
                        print(f"    -> OK: ${valor_total:,.0f} guardado".replace(",", "."))
                        guardados += 1
            else:
                print(f"    -> SIN METADATA (no se pudo guardar)")
                errores += 1

        except Exception as e:
            print(f"    -> ERROR: {e}")
            errores += 1

    # Resumen final
    print()
    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"Total archivos:     {len(files)}")
    print(f"Procesados OK:      {procesados}")
    print(f"Guardados en Sheets: {guardados}")
    print(f"Errores:            {errores}")
    print()

    if guardados > 0:
        print("Los datos fueron guardados en Google Sheets")
        print("Ahora podes:")
        print("  1. Abrir el portal: python -m streamlit run app.py")
        print("  2. Ir a 'Portfolio Individual' para ver analisis")
        print("  3. Ir a 'Historial' para ver evolucion temporal")
        print("  4. Ir a 'Administracion' para ver registros guardados")
    else:
        print("No se guardaron datos. Verifica los errores arriba.")

    print("=" * 70)


if __name__ == "__main__":
    main()
