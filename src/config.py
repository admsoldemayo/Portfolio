"""
Configuración del sistema de gestión de carteras
"""

from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
TOKEN_FILE = PROJECT_ROOT / "token.json"

# Google Sheets - Creado en flopez@soldemayosa.com
SPREADSHEET_NAME = "Portfolio Tracker - Sol de Mayo"
SPREADSHEET_ID = "1lxCrSAdkPgJ6BBIzS02H3TMwcGOeb7L85C-WbVzH76Y"

# Nombres de las hojas
SHEET_CARTERAS = "carteras_maestro"
SHEET_PERFILES = "perfiles_alocacion"
SHEET_CUSTOM = "alocacion_custom"
SHEET_HISTORIAL = "historial_tenencias"
SHEET_SNAPSHOTS = "snapshots_totales"
SHEET_TICKER_MAPPINGS = "ticker_mappings"
SHEET_DETALLE_ACTIVOS = "detalle_activos"
SHEET_CUSTOM_CATEGORIES = "categorias_custom"

# Perfiles de alocación por defecto
DEFAULT_PROFILES = {
    "conservador": {
        "LIQUIDEZ": 40,
        "LETRAS": 35,
        "GLD": 15,
        "SPY": 10,
    },
    "moderado": {
        "SPY": 25,
        "LETRAS": 25,
        "MERV": 20,
        "GLD": 15,
        "LIQUIDEZ": 15,
    },
    "agresivo": {
        "SPY": 35,
        "MERV": 25,
        "CRYPTO_BTC": 15,
        "GLD": 10,
        "LETRAS": 10,
        "LIQUIDEZ": 5,
    },
}

# Carteras conocidas (comitente -> info)
KNOWN_PORTFOLIOS = {
    "34455": {"nombre": "LOPEZ ROJAS FELIPE", "perfil": "agresivo"},
    "34462": {"nombre": "LOPEZ ROJAS PEDRO", "perfil": "moderado"},
    "34469": {"nombre": "LOPEZ ROJAS JUAN IGNACIO", "perfil": "agresivo"},
    "243999": {"nombre": "Lopez Rojas Felipe", "perfil": "agresivo"},
    "242928": {"nombre": "Lopez Rojas Manuela", "perfil": "conservador"},
    "34489": {"nombre": "ROJAS CLARIA MARIANA", "perfil": "moderado"},
    "34491": {"nombre": "LOPEZ JUAN ANTONIO", "perfil": "agresivo"},
    "247585": {"nombre": "SOL DE MAYO SA", "perfil": "moderado"},
    "247262": {"nombre": "SANTO DOMINGO SRL", "perfil": "moderado"},
}

# Categorías disponibles (ordenadas por prioridad)
CATEGORIES = [
    "SPY",
    "MERV",
    "BONOS_SOBERANOS_USD",  # Bonos soberanos en dólares (GD30, AL30, etc.)
    "LETRAS",               # Letras/LECAPs en pesos
    "GLD",
    "SLV",
    "CRYPTO_BTC",
    "CRYPTO_ETH",
    "BRASIL",
    "EXTRAS_COBRE",
    "LIQUIDEZ",
    "OTROS",
]

# Colores para gráficos
CATEGORY_COLORS = {
    "SPY": "#3366CC",
    "MERV": "#109618",
    "BONOS_SOBERANOS_USD": "#1E90FF",  # Azul dodger - renta fija USD
    "LETRAS": "#FF9900",
    "GLD": "#FFD700",
    "SLV": "#C0C0C0",
    "CRYPTO_BTC": "#F7931A",
    "CRYPTO_ETH": "#627EEA",
    "BRASIL": "#009739",
    "EXTRAS_COBRE": "#B87333",
    "LIQUIDEZ": "#22AA99",
    "OTROS": "#999999",
}

# Exposición por categoría (ARGENTINA vs EXTERIOR)
# ARGENTINA: Activos con exposición al riesgo argentino
# EXTERIOR: Activos con exposición internacional
CATEGORY_EXPOSURE = {
    "SPY": "EXTERIOR",
    "MERV": "ARGENTINA",
    "BONOS_SOBERANOS_USD": "ARGENTINA",  # Aunque son en USD, son riesgo soberano ARG
    "LETRAS": "ARGENTINA",
    "GLD": "EXTERIOR",
    "SLV": "EXTERIOR",
    "CRYPTO_BTC": "EXTERIOR",
    "CRYPTO_ETH": "EXTERIOR",
    "BRASIL": "EXTERIOR",
    "EXTRAS_COBRE": "EXTERIOR",
    "LIQUIDEZ": "ARGENTINA",  # Default, pero puede ser mixto
    "OTROS": "ARGENTINA",
}

# Colores para exposición
EXPOSURE_COLORS = {
    "ARGENTINA": "#75AADB",  # Celeste
    "EXTERIOR": "#2E7D32",   # Verde oscuro
}

# =========================================================================
# SECTORES INDUSTRIALES
# =========================================================================

# Sectores disponibles para clasificación
SECTORS = [
    "SEMICONDUCTORES",  # NVDA, AMD, INTC, ASML
    "ENERGETICAS",      # YPF, PAMP, VIST, TGSU2, XOM
    "BANCOS",           # GGAL, BMA, BBAR, JPM
    "MINERAS",          # VALE, FCX, BHP, GOLD
    "TECH",             # AAPL, MSFT, GOOGL, META
    "CONSUMO",          # WMT, KO, MCD
    "HEALTHCARE",       # UNH, JNJ, PFE
    "REAL_ESTATE",      # REITs
    "UTILITIES",        # EDN, CEPU, XLU
    "TELECOM",          # TECO2, VZ
    "INDUSTRIAL",       # CAT, DE
    "AGRO",             # AGRO, empresas agropecuarias
    "RENTA_FIJA",       # Bonos, Letras (auto por categoría)
    "CRIPTO",           # BTC, ETH (auto por categoría)
    "COMMODITIES",      # Oro, Plata (auto por categoría)
    "ETF",              # ETFs diversificados (SPY, QQQ, EWZ)
    "N/A",              # Liquidez, FCIs, otros
]

# Colores para gráficos de sectores
SECTOR_COLORS = {
    "SEMICONDUCTORES": "#8B5CF6",  # Violeta
    "ENERGETICAS": "#F97316",      # Naranja
    "BANCOS": "#0EA5E9",           # Azul claro
    "MINERAS": "#A78BFA",          # Lavanda
    "TECH": "#3B82F6",             # Azul
    "CONSUMO": "#10B981",          # Verde
    "HEALTHCARE": "#EC4899",       # Rosa
    "REAL_ESTATE": "#6366F1",      # Indigo
    "UTILITIES": "#14B8A6",        # Teal
    "TELECOM": "#F59E0B",          # Amarillo
    "INDUSTRIAL": "#6B7280",       # Gris
    "AGRO": "#84CC16",             # Lima
    "RENTA_FIJA": "#64748B",       # Slate
    "CRIPTO": "#F7931A",           # Bitcoin naranja
    "COMMODITIES": "#FFD700",      # Dorado
    "ETF": "#7C3AED",              # Violeta oscuro
    "N/A": "#9CA3AF",              # Gris claro
}

# Hoja para mapeos de sector
SHEET_SECTOR_MAPPINGS = "sector_mappings"
