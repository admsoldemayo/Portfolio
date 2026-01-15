"""
Asset Mapper - Clasificación de activos financieros
====================================================
Mapea tickers/especies a categorías objetivo para el dashboard de carteras.

Categorías:
- SPY (USA/TECH): ETFs y acciones de EE.UU.
- MERV (ARG): Acciones argentinas
- BONOS_SOBERANOS_USD: Bonos soberanos en USD (GD30, AL30, etc.)
- LETRAS (RENTA FIJA ARS): LECAPs, BONCAPs, cheques/pagarés en pesos
- GLD (ORO): ETFs de oro y mineras de oro (incluye VALE)
- SLV (PLATA): ETFs de plata
- CRYPTO_BTC: Bitcoin (IBIT)
- CRYPTO_ETH: Ethereum (ETHA)
- BRASIL: ETFs de Brasil
- EXTRAS_COBRE: Mineras industriales y uranio
- LIQUIDEZ: Pesos, dólares, FCIs Money Market
- OTROS: Activos no clasificados (para revisión manual)
"""

from typing import Optional
import re


# =============================================================================
# DICCIONARIO MAESTRO DE CLASIFICACIÓN
# =============================================================================

ASSET_CATEGORIES = {
    # -------------------------------------------------------------------------
    # SPY (USA/TECH) - ETFs y acciones estadounidenses
    # -------------------------------------------------------------------------
    "SPY": "SPY",
    "QQQ": "SPY",
    "IWM": "SPY",
    "NVDA": "SPY",
    "AMZN": "SPY",
    "META": "SPY",
    "GOOGL": "SPY",
    "GOOG": "SPY",
    "ASML": "SPY",
    "ADBE": "SPY",
    "UNH": "SPY",
    "WMT": "SPY",
    "BKNG": "SPY",
    "XLU": "SPY",
    "AAPL": "SPY",
    "MSFT": "SPY",
    "TSLA": "SPY",

    # -------------------------------------------------------------------------
    # MERV (ARG) - Acciones argentinas
    # -------------------------------------------------------------------------
    "PAMP": "MERV",
    "PAMPA": "MERV",
    "PAMP.BA": "MERV",
    "PAM": "MERV",
    "TGS": "MERV",
    "TGSU2": "MERV",
    "TGSU2.BA": "MERV",
    "YPF": "MERV",
    "YPFD": "MERV",
    "YPFD.BA": "MERV",
    "VIST": "MERV",
    "VISTA": "MERV",
    "CRES": "MERV",
    "CRESUD": "MERV",
    "CRESY": "MERV",
    "EDN": "MERV",
    "EDENOR": "MERV",
    "GGAL": "MERV",
    "GALICIA": "MERV",
    "BMA": "MERV",
    "BBAR": "MERV",
    "SUPV": "MERV",
    "CEPU": "MERV",
    "LOMA": "MERV",
    "TXAR": "MERV",
    "ALUA": "MERV",
    "COME": "MERV",
    "MIRG": "MERV",
    "TECO2": "MERV",
    "BYMA": "MERV",

    # -------------------------------------------------------------------------
    # BONOS_SOBERANOS_USD - Bonos soberanos en dólares
    # -------------------------------------------------------------------------
    "AL30": "BONOS_SOBERANOS_USD",
    "AL30D": "BONOS_SOBERANOS_USD",
    "AL30C": "BONOS_SOBERANOS_USD",
    "AL35": "BONOS_SOBERANOS_USD",
    "AL35D": "BONOS_SOBERANOS_USD",
    "AL35C": "BONOS_SOBERANOS_USD",
    "AL41": "BONOS_SOBERANOS_USD",
    "AL41D": "BONOS_SOBERANOS_USD",
    "GD30": "BONOS_SOBERANOS_USD",
    "GD30D": "BONOS_SOBERANOS_USD",
    "GD30C": "BONOS_SOBERANOS_USD",
    "GD35": "BONOS_SOBERANOS_USD",
    "GD35D": "BONOS_SOBERANOS_USD",
    "GD38": "BONOS_SOBERANOS_USD",
    "GD38D": "BONOS_SOBERANOS_USD",
    "GD41": "BONOS_SOBERANOS_USD",
    "GD41D": "BONOS_SOBERANOS_USD",
    "GD46": "BONOS_SOBERANOS_USD",
    "GD46D": "BONOS_SOBERANOS_USD",
    "AE38": "BONOS_SOBERANOS_USD",
    "AE38D": "BONOS_SOBERANOS_USD",
    # Bonares adicionales
    "GD29": "BONOS_SOBERANOS_USD",
    "GD29D": "BONOS_SOBERANOS_USD",
    "AL29": "BONOS_SOBERANOS_USD",
    "AL29D": "BONOS_SOBERANOS_USD",

    # -------------------------------------------------------------------------
    # LETRAS (RENTA FIJA ARS) - LECAPs, BONCAPs, cheques en pesos
    # -------------------------------------------------------------------------
    # LECAPs y LEFIs
    "T13F6": "LETRAS",
    "T15D5": "LETRAS",
    "TZXD5": "LETRAS",
    "TZXO6": "LETRAS",
    "S31E5": "LETRAS",
    "S14F5": "LETRAS",
    "S28F5": "LETRAS",
    "S31M5": "LETRAS",
    "S30A5": "LETRAS",
    "S30J5": "LETRAS",
    "S31L5": "LETRAS",
    "S29G5": "LETRAS",
    "S12S5": "LETRAS",
    "S30S5": "LETRAS",
    "S17O5": "LETRAS",
    "S28N5": "LETRAS",
    "S30D5": "LETRAS",
    # BONCAPs
    "T15E6": "LETRAS",
    "T17F6": "LETRAS",
    "T15A6": "LETRAS",
    # Provinciales
    "PBA25": "LETRAS",
    "CABA24": "LETRAS",
    "BDC24": "LETRAS",
    "BDC28": "LETRAS",
    "CO26": "LETRAS",
    "ERF25": "LETRAS",

    # -------------------------------------------------------------------------
    # GLD (ORO) - ETFs de oro y mineras de oro
    # -------------------------------------------------------------------------
    "GLD": "GLD",
    "IAU": "GLD",
    "GOLD": "GLD",      # Barrick Gold
    "B": "GLD",         # Barrick (CEDEAR ticker)
    "BARRICK": "GLD",
    "AEM": "GLD",       # Agnico Eagle
    "NEM": "GLD",       # Newmont
    "FNV": "GLD",       # Franco-Nevada
    "WPM": "GLD",       # Wheaton Precious Metals
    "VALE": "GLD",      # Regla especial: VALE va en ORO

    # -------------------------------------------------------------------------
    # SLV (PLATA) - ETFs de plata
    # -------------------------------------------------------------------------
    "SLV": "SLV",
    "PSLV": "SLV",
    "SIL": "SLV",

    # -------------------------------------------------------------------------
    # CRYPTO - Bitcoin y Ethereum (sub-buckets)
    # -------------------------------------------------------------------------
    "IBIT": "CRYPTO_BTC",
    "GBTC": "CRYPTO_BTC",
    "FBTC": "CRYPTO_BTC",
    "BITO": "CRYPTO_BTC",
    "ETHA": "CRYPTO_ETH",
    "ETHE": "CRYPTO_ETH",
    "FETH": "CRYPTO_ETH",

    # -------------------------------------------------------------------------
    # BRASIL - ETFs de Brasil
    # -------------------------------------------------------------------------
    "EWZ": "BRASIL",
    "ARGT": "BRASIL",  # Si querés separar Argentina ETF, mover a otra categoría

    # -------------------------------------------------------------------------
    # EXTRAS/COBRE - Mineras industriales y uranio
    # -------------------------------------------------------------------------
    "BHP": "EXTRAS_COBRE",
    "RIO": "EXTRAS_COBRE",
    "TINTO": "EXTRAS_COBRE",
    "FCX": "EXTRAS_COBRE",     # Freeport-McMoRan (cobre)
    "SCCO": "EXTRAS_COBRE",    # Southern Copper
    "URA": "EXTRAS_COBRE",     # Uranio ETF
    "CCJ": "EXTRAS_COBRE",     # Cameco (uranio)
    "UUUU": "EXTRAS_COBRE",    # Energy Fuels (uranio)

    # -------------------------------------------------------------------------
    # LIQUIDEZ - Pesos, dólares, FCIs Money Market
    # -------------------------------------------------------------------------
    "PESOS": "LIQUIDEZ",
    "ARS": "LIQUIDEZ",
    "USD": "LIQUIDEZ",
    "USD.C": "LIQUIDEZ",        # Dólar Cable
    "USDC": "LIQUIDEZ",
    "DOLARES": "LIQUIDEZ",
    "DOLAR": "LIQUIDEZ",
    "GAINVEST": "LIQUIDEZ",
    "GAINVEST FF": "LIQUIDEZ",  # FCI StoneX
    "SCHRODERS": "LIQUIDEZ",
    "CONSULTATIO": "LIQUIDEZ",
    "FIMA": "LIQUIDEZ",
    "BALANZ": "LIQUIDEZ",
    "GALILEO": "LIQUIDEZ",
    "MEGAINVER": "LIQUIDEZ",
    "PIONERO": "LIQUIDEZ",
    "SBS": "LIQUIDEZ",
    "COMPASS": "LIQUIDEZ",
    "ALLARIA": "LIQUIDEZ",
    "COCOS": "LIQUIDEZ",
    "STONEX": "LIQUIDEZ",
}

# Patrones regex para clasificación heurística
CATEGORY_PATTERNS = {
    "BONOS_SOBERANOS_USD": [
        r"^(AL|GD|AE|AY)\d{2}[DC]?$",       # Bonos soberanos USD (AL30, GD30, etc.)
        r"BONO.*GLOBAL|GLOBAL.*BONO",       # Bonos Globales
        r"BONAR",                            # Bonares
    ],
    "LETRAS": [
        r"^[ST]\d{2}[A-Z]\d$",              # LECAPs (S31E5, T13F6)
        r"^TZ[A-Z]{2}\d$",                  # Boncer
        r"LETRA|LECAP|LEFI|BONCAP",
        r"CHEQUE|PAGARE|ECHEQ",
        r"^\*[A-Z]{3}\d+",                  # Cheques/Pagarés StoneX (*AVU..., *GAR...)
    ],
    "LIQUIDEZ": [
        r"FCI|MONEY\s*MARKET|CAUCION|MM$",
        r"CUENTA|SALDO|DISPONIBLE|EFECTIVO",
        r"GAINVEST",                        # FCIs Gainvest
    ],
    "MERV": [
        r"\.BA$",  # Tickers argentinos terminados en .BA
    ],
}


def normalize_ticker(ticker: str) -> str:
    """
    Normaliza un ticker para búsqueda consistente.
    - Convierte a mayúsculas
    - Elimina espacios y caracteres especiales
    - Maneja variantes comunes (D, C para dólar/pesos)
    """
    if not ticker:
        return ""

    # Uppercase y strip
    normalized = str(ticker).upper().strip()

    # Eliminar caracteres problemáticos (preservar * para cheques/pagarés)
    normalized = re.sub(r'[^\w\d\.\*]', '', normalized)

    return normalized


def classify_asset(ticker: str, description: str = "") -> str:
    """
    Clasifica un activo según su ticker y/o descripción.

    Args:
        ticker: Símbolo/ticker del activo
        description: Descripción adicional (opcional, para heurística)

    Returns:
        Categoría del activo (SPY, MERV, LETRAS, GLD, SLV, CRYPTO_BTC,
        CRYPTO_ETH, BRASIL, EXTRAS_COBRE, LIQUIDEZ, OTROS)
    """
    normalized = normalize_ticker(ticker)

    # 1. Búsqueda directa en diccionario
    if normalized in ASSET_CATEGORIES:
        return ASSET_CATEGORIES[normalized]

    # 2. Búsqueda sin sufijos de mercado (D, C, .BA)
    base_ticker = re.sub(r'[DC]$', '', normalized)  # Quitar D o C final
    base_ticker = re.sub(r'\.BA$', '', base_ticker)  # Quitar .BA

    if base_ticker in ASSET_CATEGORIES:
        return ASSET_CATEGORIES[base_ticker]

    # 3. Búsqueda por patrones regex
    combined_text = f"{normalized} {description.upper()}"

    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, combined_text):
                return category

    # 4. No clasificado
    return "OTROS"


def get_category_display_name(category: str) -> str:
    """Devuelve nombre legible de la categoría para el dashboard."""
    display_names = {
        "SPY": "USA/Tech",
        "MERV": "Argentina (MERV)",
        "BONOS_SOBERANOS_USD": "Bonos Soberanos USD",
        "LETRAS": "Renta Fija ARS",
        "GLD": "Oro",
        "SLV": "Plata",
        "CRYPTO_BTC": "Crypto - Bitcoin",
        "CRYPTO_ETH": "Crypto - Ethereum",
        "BRASIL": "Brasil",
        "EXTRAS_COBRE": "Commodities/Extras",
        "LIQUIDEZ": "Liquidez",
        "OTROS": "Sin Clasificar",
    }
    # Buscar en categorías custom si no está en base
    if category not in display_names:
        try:
            from sheets_manager import get_sheets_manager
            sheets = get_sheets_manager()
            custom_cats = sheets.get_custom_categories_full()
            for cat in custom_cats:
                if cat.get('nombre') == category:
                    return cat.get('display_name', category)
        except Exception:
            pass
    return display_names.get(category, category)


def get_category_exposure(category: str) -> str:
    """
    Devuelve la exposición geográfica de una categoría.

    Args:
        category: Nombre de la categoría

    Returns:
        "ARGENTINA" o "EXTERIOR"
    """
    from config import CATEGORY_EXPOSURE

    # Buscar en categorías base
    if category in CATEGORY_EXPOSURE:
        return CATEGORY_EXPOSURE[category]

    # Buscar en categorías custom
    try:
        from sheets_manager import get_sheets_manager
        sheets = get_sheets_manager()
        custom_cats = sheets.get_custom_categories_full()
        for cat in custom_cats:
            if cat.get('nombre') == category:
                return cat.get('exposicion', 'ARGENTINA')
    except Exception:
        pass

    return "ARGENTINA"  # Default


def get_exposure_summary(portfolio_data: list) -> dict:
    """
    Calcula el resumen de exposición para un portfolio.

    Args:
        portfolio_data: Lista de dicts con 'categoria' y 'valor'

    Returns:
        Dict con valor y porcentaje por exposición
    """
    exposure_totals = {"ARGENTINA": 0.0, "EXTERIOR": 0.0}

    for item in portfolio_data:
        categoria = item.get('categoria', 'OTROS')
        valor = float(item.get('valor', 0))
        exposure = get_category_exposure(categoria)
        exposure_totals[exposure] += valor

    total = sum(exposure_totals.values())

    result = {}
    for exp, valor in exposure_totals.items():
        result[exp] = {
            'valor': valor,
            'pct': (valor / total * 100) if total > 0 else 0
        }

    return result


def get_all_categories() -> list:
    """Lista todas las categorías disponibles en orden de prioridad."""
    base_categories = [
        "SPY",
        "MERV",
        "BONOS_SOBERANOS_USD",
        "LETRAS",
        "GLD",
        "SLV",
        "CRYPTO_BTC",
        "CRYPTO_ETH",
        "BRASIL",
        "EXTRAS_COBRE",
        "LIQUIDEZ",
        "OTROS",
    ]
    # Cargar categorías custom desde sheets si existen
    try:
        custom_categories = load_custom_categories_from_sheets()
        # Agregar custom antes de OTROS
        for cat in custom_categories:
            if cat not in base_categories:
                base_categories.insert(-1, cat)  # Insert before OTROS
    except Exception:
        pass
    return base_categories


def add_custom_mapping(ticker: str, category: str) -> None:
    """
    Agrega un mapeo personalizado al diccionario en runtime.
    Útil para agregar activos nuevos sin modificar el código.
    """
    normalized = normalize_ticker(ticker)
    if category in get_all_categories():
        ASSET_CATEGORIES[normalized] = category
    else:
        raise ValueError(f"Categoría '{category}' no válida. Usar: {get_all_categories()}")


def load_custom_mappings_from_sheets() -> int:
    """
    Carga mapeos personalizados desde Google Sheets y los agrega al diccionario.

    Returns:
        Número de mapeos cargados
    """
    try:
        from sheets_manager import get_sheets_manager
        sheets = get_sheets_manager()
        custom_mappings = sheets.get_custom_ticker_mappings()

        count = 0
        for ticker, category in custom_mappings.items():
            if ticker and category:
                normalized = normalize_ticker(ticker)
                ASSET_CATEGORIES[normalized] = category
                count += 1

        return count
    except Exception as e:
        # Silenciosamente ignorar si no hay conexión a Sheets
        return 0


def load_custom_categories_from_sheets() -> list:
    """
    Carga categorías custom desde Google Sheets.

    Returns:
        Lista de nombres de categorías custom
    """
    try:
        from sheets_manager import get_sheets_manager
        sheets = get_sheets_manager()
        return sheets.get_custom_categories()
    except Exception:
        return []


# Cache para categorías custom y sus display names
_custom_category_display_names = {}


def register_custom_category(name: str, display_name: str = None, color: str = None) -> bool:
    """
    Registra una categoría custom en runtime.

    Args:
        name: Nombre interno de la categoría (ej: "BONOS_CORPORATIVOS")
        display_name: Nombre para mostrar (ej: "Bonos Corporativos")
        color: Color hex para gráficos (ej: "#FF5733")

    Returns:
        True si se registró exitosamente
    """
    try:
        from sheets_manager import get_sheets_manager
        sheets = get_sheets_manager()

        # Guardar en sheets
        success = sheets.save_custom_category(name, display_name or name, color or "#808080")

        if success:
            # Agregar al cache local
            _custom_category_display_names[name] = display_name or name

        return success
    except Exception as e:
        return False


# =============================================================================
# CLASIFICACIÓN POR SECTOR INDUSTRIAL
# =============================================================================

ASSET_SECTORS = {
    # -------------------------------------------------------------------------
    # SEMICONDUCTORES
    # -------------------------------------------------------------------------
    "NVDA": "SEMICONDUCTORES",
    "AMD": "SEMICONDUCTORES",
    "INTC": "SEMICONDUCTORES",
    "ASML": "SEMICONDUCTORES",
    "TSM": "SEMICONDUCTORES",
    "AVGO": "SEMICONDUCTORES",
    "QCOM": "SEMICONDUCTORES",
    "MU": "SEMICONDUCTORES",

    # -------------------------------------------------------------------------
    # ENERGÉTICAS
    # -------------------------------------------------------------------------
    "YPF": "ENERGETICAS",
    "YPFD": "ENERGETICAS",
    "YPFD.BA": "ENERGETICAS",
    "PAMP": "ENERGETICAS",
    "PAMPA": "ENERGETICAS",
    "PAM": "ENERGETICAS",
    "VIST": "ENERGETICAS",
    "VISTA": "ENERGETICAS",
    "TGS": "ENERGETICAS",
    "TGSU2": "ENERGETICAS",
    "TGSU2.BA": "ENERGETICAS",
    "CEPU": "ENERGETICAS",
    "EDN": "ENERGETICAS",
    "EDENOR": "ENERGETICAS",
    "XOM": "ENERGETICAS",
    "CVX": "ENERGETICAS",
    "COP": "ENERGETICAS",
    "SLB": "ENERGETICAS",
    "OXY": "ENERGETICAS",

    # -------------------------------------------------------------------------
    # BANCOS
    # -------------------------------------------------------------------------
    "GGAL": "BANCOS",
    "GALICIA": "BANCOS",
    "BMA": "BANCOS",
    "BBAR": "BANCOS",
    "SUPV": "BANCOS",
    "BYMA": "BANCOS",
    "JPM": "BANCOS",
    "BAC": "BANCOS",
    "WFC": "BANCOS",
    "C": "BANCOS",
    "GS": "BANCOS",
    "MS": "BANCOS",

    # -------------------------------------------------------------------------
    # MINERAS
    # -------------------------------------------------------------------------
    "VALE": "MINERAS",
    "FCX": "MINERAS",
    "BHP": "MINERAS",
    "RIO": "MINERAS",
    "TINTO": "MINERAS",
    "GOLD": "MINERAS",
    "B": "MINERAS",
    "BARRICK": "MINERAS",
    "NEM": "MINERAS",
    "AEM": "MINERAS",
    "FNV": "MINERAS",
    "WPM": "MINERAS",
    "SCCO": "MINERAS",
    "CCJ": "MINERAS",
    "URA": "MINERAS",
    "UUUU": "MINERAS",

    # -------------------------------------------------------------------------
    # TECH
    # -------------------------------------------------------------------------
    "AAPL": "TECH",
    "MSFT": "TECH",
    "GOOGL": "TECH",
    "GOOG": "TECH",
    "META": "TECH",
    "AMZN": "TECH",
    "TSLA": "TECH",
    "ADBE": "TECH",
    "CRM": "TECH",
    "ORCL": "TECH",
    "NFLX": "TECH",

    # -------------------------------------------------------------------------
    # CONSUMO
    # -------------------------------------------------------------------------
    "WMT": "CONSUMO",
    "KO": "CONSUMO",
    "PEP": "CONSUMO",
    "MCD": "CONSUMO",
    "SBUX": "CONSUMO",
    "NKE": "CONSUMO",
    "PG": "CONSUMO",
    "COST": "CONSUMO",

    # -------------------------------------------------------------------------
    # HEALTHCARE
    # -------------------------------------------------------------------------
    "UNH": "HEALTHCARE",
    "JNJ": "HEALTHCARE",
    "PFE": "HEALTHCARE",
    "ABBV": "HEALTHCARE",
    "MRK": "HEALTHCARE",
    "LLY": "HEALTHCARE",

    # -------------------------------------------------------------------------
    # REAL ESTATE
    # -------------------------------------------------------------------------
    "CRES": "REAL_ESTATE",
    "CRESUD": "REAL_ESTATE",
    "CRESY": "REAL_ESTATE",
    "IRSA": "REAL_ESTATE",
    "O": "REAL_ESTATE",

    # -------------------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------------------
    "XLU": "UTILITIES",
    "NEE": "UTILITIES",
    "DUK": "UTILITIES",
    "SO": "UTILITIES",

    # -------------------------------------------------------------------------
    # TELECOM
    # -------------------------------------------------------------------------
    "TECO2": "TELECOM",
    "VZ": "TELECOM",
    "T": "TELECOM",
    "TMUS": "TELECOM",

    # -------------------------------------------------------------------------
    # INDUSTRIAL
    # -------------------------------------------------------------------------
    "CAT": "INDUSTRIAL",
    "DE": "INDUSTRIAL",
    "BA": "INDUSTRIAL",
    "GE": "INDUSTRIAL",
    "HON": "INDUSTRIAL",
    "UNP": "INDUSTRIAL",
    "TXAR": "INDUSTRIAL",
    "ALUA": "INDUSTRIAL",
    "LOMA": "INDUSTRIAL",

    # -------------------------------------------------------------------------
    # AGRO
    # -------------------------------------------------------------------------
    "AGRO": "AGRO",
    "ADM": "AGRO",
    "BG": "AGRO",
    "MIRG": "AGRO",

    # -------------------------------------------------------------------------
    # ETFs (cuando no encajan en sector específico)
    # -------------------------------------------------------------------------
    "SPY": "ETF",
    "QQQ": "ETF",
    "IWM": "ETF",
    "EWZ": "ETF",
    "ARGT": "ETF",
    "GLD": "COMMODITIES",
    "IAU": "COMMODITIES",
    "SLV": "COMMODITIES",
    "PSLV": "COMMODITIES",

    # -------------------------------------------------------------------------
    # CRIPTO ETFs
    # -------------------------------------------------------------------------
    "IBIT": "CRIPTO",
    "GBTC": "CRIPTO",
    "FBTC": "CRIPTO",
    "BITO": "CRIPTO",
    "ETHA": "CRIPTO",
    "ETHE": "CRIPTO",
    "FETH": "CRIPTO",
}


def classify_sector(ticker: str, categoria: str = "") -> str:
    """
    Clasifica un activo por sector industrial.

    Args:
        ticker: Símbolo del activo
        categoria: Categoría ya asignada (para inferir sector en algunos casos)

    Returns:
        Sector del activo
    """
    normalized = normalize_ticker(ticker)

    # 1. Buscar en diccionario de sectores
    if normalized in ASSET_SECTORS:
        return ASSET_SECTORS[normalized]

    # 2. Buscar sin sufijos
    base_ticker = re.sub(r'[DC]$', '', normalized)
    base_ticker = re.sub(r'\.BA$', '', base_ticker)

    if base_ticker in ASSET_SECTORS:
        return ASSET_SECTORS[base_ticker]

    # 3. Cargar mapeos custom de sectores desde Sheets
    try:
        from sheets_manager import get_sheets_manager
        sheets = get_sheets_manager()
        custom_sectors = sheets.get_custom_sector_mappings()
        if normalized in custom_sectors:
            return custom_sectors[normalized]
        if base_ticker in custom_sectors:
            return custom_sectors[base_ticker]
    except Exception:
        pass

    # 4. Inferir por categoría
    if categoria in ["LETRAS", "BONOS_SOBERANOS_USD"]:
        return "RENTA_FIJA"
    if categoria in ["CRYPTO_BTC", "CRYPTO_ETH"]:
        return "CRIPTO"
    if categoria == "GLD":
        return "COMMODITIES"
    if categoria == "SLV":
        return "COMMODITIES"
    if categoria == "LIQUIDEZ":
        return "N/A"
    if categoria == "EXTRAS_COBRE":
        return "MINERAS"

    # 5. No clasificado
    return "N/A"


def get_sector_display_name(sector: str) -> str:
    """Devuelve nombre legible del sector."""
    display_names = {
        "SEMICONDUCTORES": "Semiconductores",
        "ENERGETICAS": "Energéticas",
        "BANCOS": "Bancos",
        "MINERAS": "Mineras",
        "TECH": "Tecnología",
        "CONSUMO": "Consumo",
        "HEALTHCARE": "Salud",
        "REAL_ESTATE": "Real Estate",
        "UTILITIES": "Utilities",
        "TELECOM": "Telecomunicaciones",
        "INDUSTRIAL": "Industrial",
        "AGRO": "Agropecuario",
        "RENTA_FIJA": "Renta Fija",
        "CRIPTO": "Cripto",
        "COMMODITIES": "Commodities",
        "ETF": "ETF",
        "N/A": "Sin Clasificar",
    }
    return display_names.get(sector, sector)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Tests básicos
    test_cases = [
        ("SPY", "", "SPY"),
        ("NVDA", "", "SPY"),
        ("PAMP", "", "MERV"),
        ("AL30D", "", "LETRAS"),
        ("GD30", "", "LETRAS"),
        ("T13F6", "", "LETRAS"),
        ("GLD", "", "GLD"),
        ("VALE", "", "GLD"),  # Caso especial
        ("SLV", "", "SLV"),
        ("IBIT", "", "CRYPTO_BTC"),
        ("ETHA", "", "CRYPTO_ETH"),
        ("EWZ", "", "BRASIL"),
        ("BHP", "", "EXTRAS_COBRE"),
        ("URA", "", "EXTRAS_COBRE"),
        ("GAINVEST", "", "LIQUIDEZ"),
        ("RANDOM_TICKER", "", "OTROS"),
        ("S31E5", "", "LETRAS"),  # LECAP
        ("YPFD.BA", "", "MERV"),
    ]

    print("=" * 60)
    print("TEST DE CLASIFICACIÓN DE ACTIVOS")
    print("=" * 60)

    passed = 0
    failed = 0

    for ticker, desc, expected in test_cases:
        result = classify_asset(ticker, desc)
        status = "OK" if result == expected else "FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status} {ticker:15} -> {result:15} (esperado: {expected})")

    print("=" * 60)
    print(f"Resultado: {passed}/{len(test_cases)} tests pasados")

    if failed > 0:
        print(f"ATENCIÓN: {failed} tests fallaron")
