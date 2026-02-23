"""
Ingest Pipeline - Procesamiento de carteras de inversión
=========================================================
Lee archivos Excel de brokers (IOL, PPI, Balanz, etc.),
normaliza los datos y genera un master dashboard consolidado.

Uso:
    python ingest.py                    # Procesa todos los .xlsx en data/input
    python ingest.py archivo.xlsx       # Procesa un archivo específico
"""

import os
import sys
import glob
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from asset_mapper import classify_asset, classify_sector, get_category_display_name, load_custom_mappings_from_sheets
from filename_parser import parse_filename
from portfolio_tracker import PortfolioTracker

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

# Paths relativos al directorio del proyecto
PROJECT_ROOT = Path(__file__).parent.parent
INPUT_DIR = PROJECT_ROOT / "data" / "input"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
HISTORY_DIR = PROJECT_ROOT / "data" / "history"
LOG_DIR = PROJECT_ROOT / "logs"

# Archivo de salida
MASTER_FILE = "master_dashboard.csv"

# Columnas esperadas (variantes comunes en exports de brokers)
TICKER_COLUMNS = [
    "ticker", "símbolo", "simbolo", "especie", "activo", "instrumento",
    "symbol", "asset", "codigo", "código"
]

AMOUNT_COLUMNS = [
    "valorización", "valorizacion", "monto", "valor", "total", "importe",
    "market_value", "value", "tenencia", "posición", "posicion",
    "valor_mercado", "valor mercado"
]

QUANTITY_COLUMNS = [
    "cantidad", "nominales", "qty", "quantity", "unidades", "titulos",
    "títulos", "shares"
]

DESCRIPTION_COLUMNS = [
    "descripción", "descripcion", "description", "nombre", "name", "detalle"
]

# Configurar logging
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"ingest_{datetime.now():%Y%m%d}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def find_column(df: pd.DataFrame, candidates: list) -> Optional[str]:
    """
    Busca una columna en el DataFrame que coincida con alguno de los candidatos.
    La búsqueda es case-insensitive.
    """
    df_cols_lower = {col.lower().strip(): col for col in df.columns}

    for candidate in candidates:
        candidate_lower = candidate.lower().strip()
        if candidate_lower in df_cols_lower:
            return df_cols_lower[candidate_lower]

    return None


def clean_numeric(value) -> float:
    """Convierte un valor a float, manejando formatos argentinos (1.234,56)."""
    if pd.isna(value):
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    # Convertir a string y limpiar
    s = str(value).strip()

    # Remover símbolos de moneda
    s = s.replace('$', '').replace('USD', '').replace('ARS', '').strip()

    # Detectar formato argentino (1.234,56) vs americano (1,234.56)
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'):
            # Formato argentino: 1.234,56
            s = s.replace('.', '').replace(',', '.')
        else:
            # Formato americano: 1,234.56
            s = s.replace(',', '')
    elif ',' in s:
        # Solo coma, asumimos decimal argentino
        s = s.replace(',', '.')

    try:
        return float(s)
    except ValueError:
        return 0.0


def extract_tc_from_file(filepath: str) -> dict:
    """
    Extrae los tipos de cambio (TC MEP y CCL) del archivo Excel.

    Returns:
        Dict con 'tc_mep' y 'tc_ccl', o valores por defecto si no se encuentran
    """
    try:
        df_raw = pd.read_excel(filepath, header=None, nrows=10)

        tc_mep = None
        tc_ccl = None

        for idx, row in df_raw.iterrows():
            cell0 = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""

            if "TC USD MEP" in cell0:
                tc_mep = clean_numeric(row.iloc[1])
            elif "TC USD CCL" in cell0:
                tc_ccl = clean_numeric(row.iloc[1])

        return {
            'tc_mep': tc_mep or 1150.0,
            'tc_ccl': tc_ccl or 1150.0
        }
    except Exception as e:
        logger.warning(f"Error extrayendo TC de {filepath}: {e}")
        return {'tc_mep': 1150.0, 'tc_ccl': 1150.0}


def parse_iol_stonex_format(filepath: str) -> pd.DataFrame:
    """
    Parser específico para formato IOL/StoneX con secciones por tipo de activo.

    Estructura del archivo:
    - Filas 1-6: Metadata (fecha, comitente, TC MEP/CCL)
    - Secciones: "Tipo de Activo: X" seguido de header y datos
    - Subtotales al final de cada sección
    """
    logger.info(f"Detectado formato IOL/StoneX: {filepath}")

    # Leer sin header para procesar manualmente
    df_raw = pd.read_excel(filepath, header=None)

    # Extraer TC del archivo
    tc_data = extract_tc_from_file(filepath)
    tc_mep = tc_data['tc_mep']
    tc_ccl = tc_data['tc_ccl']
    logger.info(f"  TC MEP: {tc_mep}, TC CCL: {tc_ccl}")

    # Buscar filas de datos (tienen ticker en columna 0)
    all_rows = []
    current_section = None

    for idx, row in df_raw.iterrows():
        cell0 = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""

        # Detectar sección
        if cell0.startswith("Tipo de Activo:"):
            current_section = cell0.replace("Tipo de Activo:", "").strip()
            continue

        # Saltar headers, subtotales y filas vacías
        if cell0 in ["Ticker", "Subtotal", "Total", ""] or cell0.startswith("Subtotal"):
            continue
        if "Tenencias en Portfolio" in cell0:
            continue
        if cell0.startswith("Fecha") or cell0.startswith("TC USD"):
            continue

        # Es una fila de datos si tiene ticker válido
        ticker = cell0.strip()
        if not ticker or len(ticker) < 1:
            continue

        # Extraer datos (columnas del formato IOL/StoneX)
        # Col 0: Ticker, Col 1: Nombre, Col 3: Garantía/Cantidad, Col 4: Disponibles
        # Col 5: Moneda, Col 6: Precio actual, Col 7: Monto $
        nombre = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""

        # Disponibles está en columna 4 (o 3 según el archivo)
        disponibles = row.iloc[4] if pd.notna(row.iloc[4]) else row.iloc[3]
        cantidad = clean_numeric(disponibles)

        # Precio en columna 6
        precio = clean_numeric(row.iloc[6]) if pd.notna(row.iloc[6]) else 0

        # Preferir Monto $ (col 7) si disponible, sino calcular
        monto_col = row.iloc[7] if len(row) > 7 and pd.notna(row.iloc[7]) else None
        valor = clean_numeric(monto_col) if monto_col is not None else cantidad * precio

        all_rows.append({
            'ticker': ticker.upper(),
            'descripcion': nombre,
            'cantidad': cantidad,
            'precio': precio,
            'valor': valor,
            'seccion_broker': current_section,
            'tc_mep': tc_mep,
            'tc_ccl': tc_ccl,
        })

    if not all_rows:
        logger.warning(f"No se encontraron datos en formato IOL/StoneX: {filepath}")
        return pd.DataFrame()

    return pd.DataFrame(all_rows)


def detect_broker_format(filepath: str) -> str:
    """
    Detecta el formato del archivo de broker.
    Returns: 'iol_stonex', 'standard', o 'unknown'
    """
    try:
        df_raw = pd.read_excel(filepath, header=None, nrows=10)

        # Buscar indicadores de formato IOL/StoneX
        for idx, row in df_raw.iterrows():
            cell0 = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
            if "Tipo de Activo:" in cell0 or "Tenencias en Portfolio" in cell0:
                return "iol_stonex"
            if "TC USD MEP" in cell0 or "TC USD CCL" in cell0:
                return "iol_stonex"

        # Si tiene columnas estándar, es formato standard
        df_test = pd.read_excel(filepath, nrows=5)
        cols_lower = [str(c).lower() for c in df_test.columns]
        if any(t in cols_lower for t in ['ticker', 'especie', 'símbolo']):
            return "standard"

    except Exception as e:
        logger.warning(f"Error detectando formato: {e}")

    return "unknown"


def standardize_dataframe(df: pd.DataFrame, source_file: str) -> pd.DataFrame:
    """
    Estandariza un DataFrame de broker al formato común.

    Columnas de salida:
    - ticker: Símbolo del activo
    - descripcion: Descripción del activo
    - cantidad: Cantidad/nominales
    - valor: Valorización en la moneda original
    - categoria: Categoría asignada por el mapper
    - categoria_nombre: Nombre legible de la categoría
    - fuente: Archivo de origen
    - fecha_proceso: Timestamp del procesamiento
    """
    logger.info(f"Estandarizando: {source_file}")
    logger.debug(f"Columnas encontradas: {list(df.columns)}")

    # Buscar columnas
    ticker_col = find_column(df, TICKER_COLUMNS)
    amount_col = find_column(df, AMOUNT_COLUMNS)
    qty_col = find_column(df, QUANTITY_COLUMNS)
    desc_col = find_column(df, DESCRIPTION_COLUMNS)

    if not ticker_col:
        logger.warning(f"No se encontró columna de ticker en {source_file}")
        logger.warning(f"Columnas disponibles: {list(df.columns)}")
        return pd.DataFrame()

    # Crear DataFrame estandarizado
    result = pd.DataFrame()
    result['ticker'] = df[ticker_col].astype(str).str.strip().str.upper()

    # Descripción (opcional)
    if desc_col:
        result['descripcion'] = df[desc_col].astype(str).str.strip()
    else:
        result['descripcion'] = ""

    # Cantidad (opcional)
    if qty_col:
        result['cantidad'] = df[qty_col].apply(clean_numeric)
    else:
        result['cantidad'] = 0

    # Valor/Monto
    if amount_col:
        result['valor'] = df[amount_col].apply(clean_numeric)
    else:
        logger.warning(f"No se encontró columna de valor en {source_file}")
        result['valor'] = 0

    # Clasificar activos
    result['categoria'] = result.apply(
        lambda row: classify_asset(row['ticker'], row['descripcion']),
        axis=1
    )
    result['categoria_nombre'] = result['categoria'].apply(get_category_display_name)

    # Metadata
    result['fuente'] = Path(source_file).name
    result['fecha_proceso'] = datetime.now().isoformat()

    # Filtrar filas vacías o inválidas
    result = result[
        (result['ticker'].notna()) &
        (result['ticker'] != '') &
        (result['ticker'] != 'NAN')
    ]

    # Log de activos no clasificados
    otros = result[result['categoria'] == 'OTROS']
    if len(otros) > 0:
        logger.warning(f"Activos sin clasificar en {source_file}:")
        for _, row in otros.iterrows():
            logger.warning(f"  - {row['ticker']}: {row['descripcion'][:50] if row['descripcion'] else 'N/A'}")

    return result


def read_excel_safe(filepath: str) -> pd.DataFrame:
    """
    Lee un archivo Excel manejando diferentes formatos y errores.
    Intenta múltiples hojas si la primera falla.
    """
    try:
        # Primero intentar leer la primera hoja
        df = pd.read_excel(filepath, sheet_name=0)

        # Si el DataFrame está vacío o tiene muy pocas columnas, probar otras hojas
        if len(df.columns) < 2 or len(df) < 1:
            xl = pd.ExcelFile(filepath)
            for sheet in xl.sheet_names:
                df_sheet = pd.read_excel(filepath, sheet_name=sheet)
                if len(df_sheet.columns) >= 2 and len(df_sheet) >= 1:
                    logger.info(f"Usando hoja '{sheet}' de {filepath}")
                    return df_sheet

        return df

    except Exception as e:
        logger.error(f"Error leyendo {filepath}: {e}")
        return pd.DataFrame()


# =============================================================================
# PIPELINE PRINCIPAL
# =============================================================================

def process_single_file(filepath: str) -> pd.DataFrame:
    """Procesa un único archivo Excel y retorna DataFrame estandarizado."""
    logger.info(f"Procesando: {filepath}")

    # Extraer metadata del filename
    metadata = parse_filename(filepath)
    logger.info(f"  Metadata: comitente={metadata['comitente']}, fecha={metadata['fecha']}")

    # Detectar formato del broker
    broker_format = detect_broker_format(filepath)
    logger.info(f"  Formato detectado: {broker_format}")

    if broker_format == "iol_stonex":
        # Parser específico para IOL/StoneX
        df_parsed = parse_iol_stonex_format(filepath)
        if df_parsed.empty:
            return pd.DataFrame()

        # Aplicar clasificación
        df_parsed['categoria'] = df_parsed.apply(
            lambda row: classify_asset(row['ticker'], row['descripcion']),
            axis=1
        )
        df_parsed['categoria_nombre'] = df_parsed['categoria'].apply(get_category_display_name)
        df_parsed['fuente'] = Path(filepath).name
        df_parsed['fecha_proceso'] = datetime.now().isoformat()

        # Agregar metadata del filename
        df_parsed['comitente'] = metadata['comitente']
        df_parsed['nombre_cliente'] = metadata['nombre']
        df_parsed['fecha_archivo'] = metadata['fecha']

        # Log de activos no clasificados
        otros = df_parsed[df_parsed['categoria'] == 'OTROS']
        if len(otros) > 0:
            logger.warning(f"Activos sin clasificar en {filepath}:")
            for _, row in otros.iterrows():
                logger.warning(f"  - {row['ticker']}: {row['descripcion'][:50] if row['descripcion'] else 'N/A'}")

        logger.info(f"  -> {len(df_parsed)} activos procesados")
        return df_parsed

    else:
        # Formato estándar
        df_raw = read_excel_safe(filepath)
        if df_raw.empty:
            logger.warning(f"Archivo vacío o no legible: {filepath}")
            return pd.DataFrame()

        df_std = standardize_dataframe(df_raw, filepath)

        # Agregar metadata del filename
        df_std['comitente'] = metadata['comitente']
        df_std['nombre_cliente'] = metadata['nombre']
        df_std['fecha_archivo'] = metadata['fecha']

        logger.info(f"  -> {len(df_std)} activos procesados")
        return df_std


def process_all_inputs() -> pd.DataFrame:
    """
    Procesa todos los archivos .xlsx en la carpeta de inputs.
    Retorna DataFrame consolidado.
    """
    # Buscar archivos Excel
    pattern = str(INPUT_DIR / "*.xlsx")
    files = glob.glob(pattern)

    # También buscar .xls
    pattern_xls = str(INPUT_DIR / "*.xls")
    files.extend(glob.glob(pattern_xls))

    if not files:
        logger.warning(f"No se encontraron archivos Excel en {INPUT_DIR}")
        return pd.DataFrame()

    logger.info(f"Encontrados {len(files)} archivos para procesar")

    # Procesar cada archivo
    all_dfs = []
    for filepath in files:
        df = process_single_file(filepath)
        if not df.empty:
            all_dfs.append(df)

    if not all_dfs:
        logger.warning("Ningún archivo produjo datos válidos")
        return pd.DataFrame()

    # Consolidar
    master = pd.concat(all_dfs, ignore_index=True)

    logger.info(f"Total consolidado: {len(master)} posiciones")
    return master


def save_outputs(df: pd.DataFrame) -> tuple:
    """
    Guarda el DataFrame procesado:
    1. Master actual (sobreescribe)
    2. Copia histórica con timestamp

    Returns:
        Tuple (master_path, history_path)
    """
    if df.empty:
        logger.warning("DataFrame vacío, no se guardan archivos")
        return None, None

    # Asegurar que existan los directorios
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. Master actual
    master_path = OUTPUT_DIR / MASTER_FILE
    df.to_csv(master_path, index=False, encoding='utf-8-sig')
    logger.info(f"Master guardado: {master_path}")

    # 2. Copia histórica
    history_filename = f"portfolio_{timestamp}.csv"
    history_path = HISTORY_DIR / history_filename
    df.to_csv(history_path, index=False, encoding='utf-8-sig')
    logger.info(f"Histórico guardado: {history_path}")

    return master_path, history_path


def generate_summary(df: pd.DataFrame) -> str:
    """Genera un resumen del portfolio procesado."""
    if df.empty:
        return "Portfolio vacío"

    lines = [
        "=" * 60,
        "RESUMEN DEL PORTFOLIO",
        "=" * 60,
        f"Total de posiciones: {len(df)}",
        f"Archivos procesados: {df['fuente'].nunique()}",
        "",
        "DISTRIBUCIÓN POR CATEGORÍA:",
        "-" * 40,
    ]

    # Agrupar por categoría
    summary = df.groupby('categoria_nombre').agg({
        'valor': 'sum',
        'ticker': 'count'
    }).rename(columns={'ticker': 'posiciones'})

    summary['% del total'] = (summary['valor'] / summary['valor'].sum() * 100).round(1)
    summary = summary.sort_values('valor', ascending=False)

    for cat, row in summary.iterrows():
        lines.append(
            f"  {cat:25} ${row['valor']:>15,.2f}  ({row['posiciones']:>3} pos) {row['% del total']:>5.1f}%"
        )

    lines.append("-" * 40)
    lines.append(f"  {'TOTAL':25} ${summary['valor'].sum():>15,.2f}")
    lines.append("=" * 60)

    # Activos sin clasificar
    otros = df[df['categoria'] == 'OTROS']
    if len(otros) > 0:
        lines.append("")
        lines.append("[!] ACTIVOS SIN CLASIFICAR (revisar):")
        for _, row in otros.iterrows():
            lines.append(f"  - {row['ticker']}: ${row['valor']:,.2f}")

    return "\n".join(lines)


def save_to_sheets(df: pd.DataFrame, auto_save: bool = True) -> dict:
    """
    Guarda snapshots de carteras en Google Sheets con rate limiting y retry.

    Args:
        df: DataFrame con datos procesados (debe tener columnas:
            comitente, nombre_cliente, fecha_archivo, categoria, ticker, valor)
        auto_save: Si es True, guarda automáticamente. Si es False, solo retorna info.

    Returns:
        Dict con resultados del guardado por comitente, incluyendo:
        - 'retries': lista de operaciones que necesitaron reintento
        - 'failed': True si falló definitivamente
        - 'error': mensaje de error si falló
    """
    from sheets_manager import get_sheets_manager

    if df.empty:
        logger.warning("DataFrame vacío, no se puede guardar en Sheets")
        return {}

    # Verificar columnas necesarias
    required_cols = ['comitente', 'nombre_cliente', 'fecha_archivo', 'categoria', 'valor']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.error(f"Faltan columnas requeridas: {missing_cols}")
        return {}

    tracker = PortfolioTracker()
    sheets = get_sheets_manager()
    results = {}

    comitentes = [c for c in df['comitente'].unique() if pd.notna(c) and c != '']
    total_carteras = len(comitentes)

    logger.info(f"Procesando {total_carteras} carteras con rate limiting (1s entre writes)")

    # Agrupar por comitente
    for idx, comitente in enumerate(comitentes, 1):
        df_comitente = df[df['comitente'] == comitente]

        # Obtener metadata
        nombre = df_comitente.iloc[0]['nombre_cliente']
        fecha = df_comitente.iloc[0]['fecha_archivo']

        if pd.isna(fecha) or fecha == '':
            fecha = datetime.now().strftime('%Y-%m-%d')
            logger.warning(f"Fecha no encontrada para {comitente}, usando hoy: {fecha}")

        # Obtener TC si está disponible
        tc_mep = df_comitente.iloc[0].get('tc_mep', 0) if 'tc_mep' in df_comitente.columns else 0
        tc_ccl = df_comitente.iloc[0].get('tc_ccl', 0) if 'tc_ccl' in df_comitente.columns else 0

        # Log info
        valor_total = df_comitente['valor'].sum()
        logger.info(
            f"[{idx}/{total_carteras}] {comitente} ({nombre}) - "
            f"${valor_total:,.0f} - {fecha}"
        )

        if auto_save:
            # Limpiar log de reintentos antes de cada cartera
            sheets.clear_retry_log()

            try:
                # Guardar snapshot agregado (por categoría)
                result = tracker.save_snapshot(
                    df=df_comitente[['categoria', 'ticker', 'valor']],
                    comitente=str(comitente),
                    nombre=nombre,
                    fecha=fecha
                )

                # Guardar detalle de activos (nivel ticker) con TC y sector
                activos = []
                for _, row in df_comitente.iterrows():
                    ticker = row.get('ticker', '')
                    categoria = row.get('categoria', 'OTROS')
                    sector = classify_sector(ticker, categoria)
                    activos.append({
                        'ticker': ticker,
                        'descripcion': row.get('descripcion', ''),
                        'cantidad': row.get('cantidad', 0),
                        'precio': row.get('precio', 0),
                        'valor': row.get('valor', 0),
                        'categoria': categoria,
                        'sector': sector
                    })

                sheets.save_detalle_activos(
                    fecha=fecha,
                    comitente=str(comitente),
                    nombre=nombre,
                    activos=activos,
                    tc_mep=float(tc_mep) if tc_mep else 0,
                    tc_ccl=float(tc_ccl) if tc_ccl else 0
                )

                # Recopilar info de reintentos para esta cartera
                retry_log = sheets.get_retry_log()
                retries = [r for r in retry_log if r['status'] == 'success']
                failures = [r for r in retry_log if r['status'] == 'failed']

                result['retries'] = retries
                result['failed'] = False

                if retries:
                    logger.info(
                        f"  -> OK con {len(retries)} reintentos: "
                        f"{', '.join(r['operation'] for r in retries)}"
                    )
                else:
                    logger.info(
                        f"  -> OK ({len(activos)} activos)"
                    )

                results[comitente] = result

            except Exception as e:
                logger.error(f"  -> ERROR DEFINITIVO para {comitente}: {e}")
                retry_log = sheets.get_retry_log()
                results[comitente] = {
                    'error': str(e),
                    'failed': True,
                    'retries': [r for r in retry_log if r['status'] == 'success'],
                    'nombre': nombre,
                }

                # Si fue rate limit, esperar antes de la siguiente cartera
                if '429' in str(e) or 'RATE_LIMIT' in str(e).upper():
                    logger.info("  -> Esperando 30s antes de continuar...")
                    time.sleep(30)
        else:
            results[comitente] = {
                'nombre': nombre,
                'fecha': fecha,
                'valor_total': valor_total,
                'dry_run': True
            }

    # Resumen final de rate limiting
    _log_rate_limit_summary(results)

    return results


def _log_rate_limit_summary(results: dict):
    """Imprime resumen de rate limiting: reintentos y fallos."""
    retried = []
    failed = []
    ok = []

    for comitente, result in results.items():
        if result.get('dry_run'):
            continue
        if result.get('failed'):
            failed.append((comitente, result.get('nombre', ''), result.get('error', '')))
        elif result.get('retries'):
            retried.append((comitente, result.get('nombre', ''), len(result['retries'])))
        else:
            ok.append(comitente)

    logger.info("")
    logger.info("=" * 60)
    logger.info("RESUMEN RATE LIMITING")
    logger.info("=" * 60)
    logger.info(f"  OK sin reintentos:  {len(ok)}")
    logger.info(f"  OK con reintentos:  {len(retried)}")
    logger.info(f"  FALLIDOS:           {len(failed)}")

    if retried:
        logger.info("")
        logger.info("  Carteras con reintentos:")
        for com, nombre, count in retried:
            logger.info(f"    - {com} ({nombre}): {count} reintentos")

    if failed:
        logger.info("")
        logger.info("  Carteras FALLIDAS:")
        for com, nombre, error in failed:
            logger.info(f"    - {com} ({nombre}): {error[:80]}")

    logger.info("=" * 60)


def run_pipeline(specific_file: str = None, save_to_gsheets: bool = True):
    """
    Ejecuta el pipeline completo de ingesta.

    Args:
        specific_file: Si se especifica, procesa solo ese archivo.
                      Si es None, procesa todos los archivos en input/.
        save_to_gsheets: Si es True, guarda automáticamente en Google Sheets.
    """
    logger.info("=" * 60)
    logger.info("INICIANDO PIPELINE DE INGESTA")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    # Cargar mapeos custom desde Google Sheets
    try:
        custom_count = load_custom_mappings_from_sheets()
        if custom_count > 0:
            logger.info(f"Cargados {custom_count} mapeos de clasificación personalizados")
    except Exception as e:
        logger.warning(f"No se pudieron cargar mapeos custom: {e}")

    if specific_file:
        df = process_single_file(specific_file)
    else:
        df = process_all_inputs()

    if df.empty:
        logger.error("No se obtuvieron datos para procesar")
        return

    # Guardar outputs locales
    master_path, history_path = save_outputs(df)

    # Guardar en Google Sheets (si está habilitado)
    if save_to_gsheets:
        logger.info("\n" + "=" * 60)
        logger.info("GUARDANDO SNAPSHOTS EN GOOGLE SHEETS")
        logger.info("=" * 60)
        sheets_results = save_to_sheets(df, auto_save=True)
        logger.info(f"Snapshots guardados: {len(sheets_results)} carteras")

    # Mostrar resumen
    summary = generate_summary(df)
    print("\n" + summary)

    logger.info("Pipeline completado exitosamente")

    return df


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Archivo específico pasado como argumento
        input_file = sys.argv[1]
        if not os.path.exists(input_file):
            print(f"Error: Archivo no encontrado: {input_file}")
            sys.exit(1)
        run_pipeline(specific_file=input_file)
    else:
        # Procesar todos los archivos en input/
        run_pipeline()
