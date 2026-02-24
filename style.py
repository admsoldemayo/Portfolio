"""
Style Module - Obsidian Finance Theme v2
=========================================
Heavy custom HTML components + aggressive CSS overrides.
Replaces native Streamlit widgets where possible for maximum visual impact.
"""

import streamlit as st
import html as html_lib


# =============================================================================
# COLOR PALETTE
# =============================================================================

COLORS = {
    'bg_primary': '#0E1117',
    'bg_secondary': '#161B22',
    'bg_card': '#1A1F2E',
    'accent_gold': '#C9A54E',
    'accent_gold_light': '#E8D5A3',
    'accent_green': '#10B981',
    'accent_red': '#EF4444',
    'accent_blue': '#3B82F6',
    'accent_cyan': '#06B6D4',
    'accent_violet': '#8B5CF6',
    'text_primary': '#E2E8F0',
    'text_secondary': '#8B95A5',
    'border': '#21262D',
    'border_hover': '#30363D',
}

CHART_COLORS = [
    '#C9A54E', '#10B981', '#3B82F6', '#8B5CF6', '#EF4444',
    '#F59E0B', '#06B6D4', '#EC4899', '#F97316', '#14B8A6',
    '#A78BFA', '#6366F1',
]

CATEGORY_COLORS_DARK = {
    "SPY": "#3B82F6", "MERV": "#10B981", "BONOS_SOBERANOS_USD": "#60A5FA",
    "LETRAS": "#F59E0B", "GLD": "#C9A54E", "SLV": "#94A3B8",
    "CRYPTO_BTC": "#F7931A", "CRYPTO_ETH": "#818CF8", "BRASIL": "#22C55E",
    "EXTRAS_COBRE": "#D97706", "LIQUIDEZ": "#06B6D4", "OTROS": "#6B7280",
}


# =============================================================================
# CSS INJECTION - AGGRESSIVE OVERRIDES
# =============================================================================

def inject_css():
    """Inject the Obsidian Finance theme CSS with heavy overrides."""

    # Use <link> for fonts (more reliable than @import inside <style>)
    st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    """, unsafe_allow_html=True)

    st.markdown("""
    <style>

    /* ===== GLOBAL RESET ===== */
    *, *::before, *::after {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }

    .main .block-container {
        padding: 2rem 3rem 2rem 3rem;
        max-width: 1200px;
    }

    /* ===== HEADINGS - DRAMATIC ===== */
    h1 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 800 !important;
        font-size: 2.2rem !important;
        letter-spacing: -0.04em !important;
        background: linear-gradient(135deg, #C9A54E 0%, #F0DFA0 40%, #C9A54E 70%, #A07B28 100%) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        background-clip: text !important;
        padding-bottom: 0.1em !important;
        line-height: 1.1 !important;
    }

    h2 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        font-size: 1.35rem !important;
        letter-spacing: -0.03em !important;
        color: #F1F5F9 !important;
        margin-top: 1.8em !important;
        margin-bottom: 0.6em !important;
        position: relative;
        padding-left: 16px !important;
        border-bottom: none !important;
    }

    h2::before {
        content: '';
        position: absolute;
        left: 0;
        top: 4px;
        bottom: 4px;
        width: 4px;
        background: linear-gradient(180deg, #C9A54E, #8B6914);
        border-radius: 2px;
    }

    h3 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        font-size: 1.05rem !important;
        color: #94A3B8 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        font-size: 0.8rem !important;
    }

    /* ===== METRIC CARDS - GLASS MORPHISM ===== */
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(26, 31, 46, 0.9) 0%, rgba(22, 27, 34, 0.95) 100%) !important;
        border: 1px solid rgba(201, 165, 78, 0.15) !important;
        border-radius: 16px !important;
        padding: 20px 24px !important;
        backdrop-filter: blur(10px) !important;
        box-shadow:
            0 4px 16px rgba(0, 0, 0, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.03) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        position: relative !important;
        overflow: hidden !important;
    }

    [data-testid="stMetric"]::before {
        content: '' !important;
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        height: 3px !important;
        background: linear-gradient(90deg, #C9A54E, #F0DFA0, #C9A54E) !important;
        opacity: 0.6 !important;
    }

    [data-testid="stMetric"]:hover {
        border-color: rgba(201, 165, 78, 0.4) !important;
        box-shadow:
            0 8px 32px rgba(201, 165, 78, 0.15),
            0 4px 16px rgba(0, 0, 0, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
        transform: translateY(-3px) !important;
    }

    [data-testid="stMetricLabel"] p {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.7rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        color: #64748B !important;
    }

    [data-testid="stMetricValue"] div {
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
        font-size: 1.6rem !important;
        color: #F8FAFC !important;
        letter-spacing: -0.02em !important;
    }

    [data-testid="stMetricDelta"] {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* ===== SIDEBAR - BRANDED ===== */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #080B10 0%, #0D1117 40%, #131820 100%) !important;
        border-right: 1px solid #1A1F2E !important;
    }

    section[data-testid="stSidebar"] > div:first-child {
        background: transparent !important;
        padding-top: 0 !important;
    }

    /* Nav links */
    [data-testid="stSidebarNav"] {
        padding-top: 1rem;
    }

    [data-testid="stSidebarNav"] li {
        margin-bottom: 2px;
    }

    [data-testid="stSidebarNav"] li a {
        border-radius: 10px !important;
        padding: 8px 12px !important;
        transition: all 0.2s ease !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
    }

    [data-testid="stSidebarNav"] li a:hover {
        background: rgba(201, 165, 78, 0.08) !important;
    }

    [data-testid="stSidebarNav"] li a[aria-selected="true"] {
        background: linear-gradient(90deg, rgba(201, 165, 78, 0.12) 0%, rgba(201, 165, 78, 0.04) 100%) !important;
        border-left: 3px solid #C9A54E !important;
        font-weight: 600 !important;
    }

    /* Sidebar headings */
    section[data-testid="stSidebar"] h3 {
        color: #C9A54E !important;
        font-size: 0.72rem !important;
        letter-spacing: 0.12em !important;
        margin-top: 1.5rem !important;
        padding-left: 0 !important;
    }

    section[data-testid="stSidebar"] h3::before {
        display: none !important;
    }

    /* ===== BUTTONS ===== */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #C9A54E 0%, #A07B28 100%) !important;
        color: #0A0D12 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.6rem 2rem !important;
        font-size: 0.85rem !important;
        letter-spacing: 0.02em !important;
        box-shadow: 0 4px 14px rgba(201, 165, 78, 0.35) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        text-transform: uppercase !important;
    }

    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="stBaseButton-primary"]:hover {
        box-shadow: 0 6px 24px rgba(201, 165, 78, 0.5) !important;
        transform: translateY(-2px) !important;
        background: linear-gradient(135deg, #D4B05A 0%, #B8923E 100%) !important;
    }

    .stButton > button:not([kind="primary"]):not([data-testid="stBaseButton-primary"]) {
        border: 1px solid #2D3548 !important;
        border-radius: 10px !important;
        background: rgba(26, 31, 46, 0.5) !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
        color: #94A3B8 !important;
    }

    .stButton > button:not([kind="primary"]):not([data-testid="stBaseButton-primary"]):hover {
        border-color: #C9A54E !important;
        color: #C9A54E !important;
        background: rgba(201, 165, 78, 0.08) !important;
        box-shadow: 0 0 20px rgba(201, 165, 78, 0.1) !important;
    }

    /* ===== DATAFRAMES ===== */
    [data-testid="stDataFrame"] {
        border: 1px solid #1E2536 !important;
        border-radius: 14px !important;
        overflow: hidden !important;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.2) !important;
    }

    /* ===== DIVIDERS ===== */
    hr {
        border: none !important;
        height: 1px !important;
        background: linear-gradient(90deg, transparent 0%, #2D3548 30%, #2D3548 70%, transparent 100%) !important;
        margin: 2rem 0 !important;
    }

    /* ===== EXPANDERS ===== */
    [data-testid="stExpander"] {
        border: 1px solid #1E2536 !important;
        border-radius: 14px !important;
        background: rgba(22, 27, 34, 0.6) !important;
        overflow: hidden !important;
    }

    [data-testid="stExpander"] summary {
        font-weight: 500 !important;
        padding: 12px 16px !important;
    }

    /* ===== ALERTS ===== */
    .stAlert {
        border-radius: 12px !important;
        border-left-width: 4px !important;
        backdrop-filter: blur(5px) !important;
    }

    /* ===== FILE UPLOADER ===== */
    [data-testid="stFileUploader"] {
        border: 2px dashed #2D3548 !important;
        border-radius: 16px !important;
        background: rgba(26, 31, 46, 0.3) !important;
        transition: all 0.3s ease !important;
    }

    [data-testid="stFileUploader"]:hover {
        border-color: #C9A54E !important;
        background: rgba(201, 165, 78, 0.04) !important;
        box-shadow: 0 0 30px rgba(201, 165, 78, 0.08) !important;
    }

    /* ===== INPUTS ===== */
    [data-baseweb="select"] > div,
    [data-baseweb="input"] > div {
        border-radius: 10px !important;
        border-color: #1E2536 !important;
        background: rgba(14, 17, 23, 0.6) !important;
        transition: all 0.2s ease !important;
    }

    [data-baseweb="select"] > div:hover,
    [data-baseweb="input"] > div:hover {
        border-color: rgba(201, 165, 78, 0.4) !important;
    }

    [data-baseweb="select"] > div:focus-within,
    [data-baseweb="input"] > div:focus-within {
        border-color: #C9A54E !important;
        box-shadow: 0 0 0 2px rgba(201, 165, 78, 0.15) !important;
    }

    /* ===== MULTISELECT TAGS ===== */
    [data-testid="stMultiSelect"] span[data-baseweb="tag"] {
        background: rgba(201, 165, 78, 0.12) !important;
        border: 1px solid rgba(201, 165, 78, 0.25) !important;
        border-radius: 8px !important;
        color: #E8D5A3 !important;
        font-weight: 500 !important;
    }

    /* ===== TABS ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px !important;
        background: rgba(14, 17, 23, 0.5) !important;
        border-radius: 12px !important;
        padding: 4px !important;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 10px !important;
        padding: 10px 20px !important;
        font-weight: 500 !important;
        font-size: 0.85rem !important;
        transition: all 0.2s ease !important;
    }

    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: rgba(201, 165, 78, 0.12) !important;
        color: #C9A54E !important;
        font-weight: 600 !important;
    }

    /* ===== PROGRESS BAR ===== */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #C9A54E 0%, #F0DFA0 50%, #C9A54E 100%) !important;
        border-radius: 99px !important;
    }

    /* ===== SCROLLBAR ===== */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #2D3548; border-radius: 99px; }
    ::-webkit-scrollbar-thumb:hover { background: #C9A54E; }

    /* ===== FORM ===== */
    [data-testid="stForm"] {
        border: 1px solid #1E2536 !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        background: rgba(22, 27, 34, 0.5) !important;
    }

    /* ===== HIDE BRANDING ===== */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {
        background: rgba(14, 17, 23, 0.8) !important;
        backdrop-filter: blur(10px) !important;
    }

    /* ===== CUSTOM KPI CARD CLASS ===== */
    .kpi-grid {
        display: grid;
        gap: 16px;
        margin: 1rem 0 1.5rem 0;
    }
    .kpi-grid-2 { grid-template-columns: repeat(2, 1fr); }
    .kpi-grid-3 { grid-template-columns: repeat(3, 1fr); }
    .kpi-grid-4 { grid-template-columns: repeat(4, 1fr); }

    .kpi-card {
        background: linear-gradient(145deg, rgba(26, 31, 46, 0.95) 0%, rgba(22, 27, 34, 0.98) 100%);
        border: 1px solid rgba(45, 53, 72, 0.6);
        border-radius: 16px;
        padding: 20px 24px;
        position: relative;
        overflow: hidden;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
    }

    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        border-radius: 0 2px 2px 0;
    }

    .kpi-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }

    .kpi-card .kpi-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.68rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #64748B;
        margin: 0 0 8px 0;
    }

    .kpi-card .kpi-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.5rem;
        font-weight: 700;
        color: #F8FAFC;
        margin: 0;
        letter-spacing: -0.02em;
        line-height: 1.2;
    }

    .kpi-card .kpi-sub {
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        color: #475569;
        margin: 6px 0 0 0;
    }

    .kpi-card.gold::before { background: linear-gradient(180deg, #C9A54E, #8B6914); }
    .kpi-card.green::before { background: linear-gradient(180deg, #10B981, #047857); }
    .kpi-card.blue::before { background: linear-gradient(180deg, #3B82F6, #1D4ED8); }
    .kpi-card.cyan::before { background: linear-gradient(180deg, #06B6D4, #0E7490); }
    .kpi-card.violet::before { background: linear-gradient(180deg, #8B5CF6, #6D28D9); }
    .kpi-card.red::before { background: linear-gradient(180deg, #EF4444, #B91C1C); }

    .kpi-card.gold:hover { border-color: rgba(201, 165, 78, 0.3); }
    .kpi-card.green:hover { border-color: rgba(16, 185, 129, 0.3); }
    .kpi-card.blue:hover { border-color: rgba(59, 130, 246, 0.3); }
    .kpi-card.cyan:hover { border-color: rgba(6, 182, 212, 0.3); }
    .kpi-card.violet:hover { border-color: rgba(139, 92, 246, 0.3); }

    /* ===== SECTION CONTAINER ===== */
    .section-box {
        background: rgba(22, 27, 34, 0.4);
        border: 1px solid #1E2536;
        border-radius: 16px;
        padding: 24px;
        margin: 1rem 0;
    }

    /* ===== BRAND BADGE ===== */
    .brand-badge {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 16px 0;
        margin-bottom: 8px;
    }

    .brand-badge .brand-icon {
        width: 36px;
        height: 36px;
        background: linear-gradient(135deg, #C9A54E 0%, #8B6914 100%);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
        box-shadow: 0 4px 12px rgba(201, 165, 78, 0.25);
    }

    .brand-badge .brand-text {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 0.95rem;
        color: #E2E8F0;
        letter-spacing: -0.02em;
    }

    .brand-badge .brand-sub {
        font-family: 'Inter', sans-serif;
        font-size: 0.7rem;
        color: #475569;
        letter-spacing: 0.02em;
    }

    /* ===== RESPONSIVE ===== */
    @media (max-width: 768px) {
        .kpi-grid-4 { grid-template-columns: repeat(2, 1fr); }
        .kpi-grid-3 { grid-template-columns: repeat(2, 1fr); }
        .main .block-container { padding: 1rem 1.5rem; }
    }

    </style>
    """, unsafe_allow_html=True)


# =============================================================================
# PLOTLY THEME
# =============================================================================

def get_plotly_theme() -> dict:
    return dict(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif', color='#8B95A5', size=12),
        title=dict(
            font=dict(size=14, color='#E2E8F0', family='Inter, sans-serif'),
            x=0, xanchor='left', pad=dict(b=12),
        ),
        xaxis=dict(
            gridcolor='rgba(45, 53, 72, 0.4)', gridwidth=0.5,
            zerolinecolor='#21262D',
            tickfont=dict(size=11, color='#64748B'),
            title_font=dict(size=12, color='#8B95A5'),
        ),
        yaxis=dict(
            gridcolor='rgba(45, 53, 72, 0.4)', gridwidth=0.5,
            zerolinecolor='#21262D',
            tickfont=dict(size=11, color='#64748B'),
            title_font=dict(size=12, color='#8B95A5'),
        ),
        hoverlabel=dict(
            bgcolor='#1A1F2E', font_size=12, font_family='Inter, sans-serif',
            font_color='#E2E8F0', bordercolor='#2D3548',
        ),
        colorway=CHART_COLORS,
        legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=11, color='#8B95A5')),
        margin=dict(l=20, r=20, t=50, b=20),
    )


def apply_plotly_theme(fig):
    fig.update_layout(**get_plotly_theme())
    return fig


def styled_pie_chart(fig):
    apply_plotly_theme(fig)
    fig.update_traces(
        textfont=dict(family='Inter, sans-serif', size=11, color='#E2E8F0'),
        marker=dict(line=dict(color='#0E1117', width=2)),
    )
    return fig


# =============================================================================
# CUSTOM HTML COMPONENTS
# =============================================================================

def _esc(text):
    """Escape HTML entities."""
    return html_lib.escape(str(text))


def kpi_row(cards: list):
    """
    Render a row of KPI cards using custom HTML.
    cards: list of dicts with keys: label, value, color (gold/green/blue/cyan/violet/red), sub (optional)
    """
    n = len(cards)
    grid_class = f"kpi-grid-{min(n, 4)}"

    cards_html = ""
    for card in cards:
        color = card.get('color', 'gold')
        label = _esc(card.get('label', ''))
        value = _esc(card.get('value', ''))
        sub = card.get('sub', '')
        sub_html = f'<p class="kpi-sub">{_esc(sub)}</p>' if sub else ''
        cards_html += f"""
        <div class="kpi-card {color}">
            <p class="kpi-label">{label}</p>
            <p class="kpi-value">{value}</p>
            {sub_html}
        </div>
        """

    st.markdown(f'<div class="kpi-grid {grid_class}">{cards_html}</div>', unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ""):
    """Render a styled page header."""
    sub_html = ""
    if subtitle:
        sub_html = f'<p style="color: #64748B; font-size: 0.88rem; margin: 6px 0 0 0; font-family: Inter, sans-serif; font-weight: 400;">{_esc(subtitle)}</p>'

    st.markdown(f"""
    <div style="margin-bottom: 0.8rem; padding-top: 0.5rem;">
        <h1 style="
            font-family: 'Inter', sans-serif;
            font-size: 2.2rem;
            font-weight: 800;
            letter-spacing: -0.04em;
            background: linear-gradient(135deg, #C9A54E 0%, #F0DFA0 40%, #C9A54E 70%, #A07B28 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin: 0;
            padding: 0;
            line-height: 1.15;
        ">{_esc(title)}</h1>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)


def login_header():
    """Render the login page header with Sol de Mayo branding."""
    st.markdown("""
    <div style="text-align: center; padding: 4rem 0 2rem 0;">
        <div style="
            width: 56px; height: 56px;
            background: linear-gradient(135deg, #C9A54E 0%, #F0DFA0 40%, #A07B28 100%);
            border-radius: 14px;
            margin: 0 auto 1.5rem auto;
            box-shadow: 0 8px 32px rgba(201, 165, 78, 0.35);
            display: flex; align-items: center; justify-content: center;
        ">
            <span style="font-size: 1.4rem; line-height: 56px; display: block; width: 56px; text-align: center; color: #0A0D12;">&#9670;</span>
        </div>
        <h1 style="
            font-family: 'Inter', sans-serif;
            font-size: 1.6rem; font-weight: 800;
            letter-spacing: -0.04em;
            background: linear-gradient(135deg, #C9A54E 0%, #F0DFA0 40%, #C9A54E 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
            margin: 0 0 0.4rem 0;
        ">Portfolio Dashboard</h1>
        <p style="color: #475569; font-size: 0.82rem; margin: 0; font-family: 'Inter', sans-serif; letter-spacing: 0.08em; text-transform: uppercase; font-weight: 500;">
            Sol de Mayo &middot; Santo Domingo
        </p>
    </div>
    """, unsafe_allow_html=True)


def sidebar_brand():
    """Render brand badge in sidebar."""
    st.markdown("""
    <div class="brand-badge">
        <div class="brand-icon">
            <span style="color: #0A0D12; font-size: 0.9rem; line-height: 36px; display: block; width: 36px; text-align: center;">&#9670;</span>
        </div>
        <div>
            <div class="brand-text">Sol de Mayo</div>
            <div class="brand-sub">Portfolio Manager</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def section_box_start():
    """Open a styled section container."""
    st.markdown('<div class="section-box">', unsafe_allow_html=True)


def section_box_end():
    """Close a styled section container."""
    st.markdown('</div>', unsafe_allow_html=True)


def section_header(text: str):
    """Render a styled section header."""
    st.markdown(f"""
    <h3 style="
        font-family: 'Inter', sans-serif; font-weight: 600;
        color: #94A3B8; font-size: 0.78rem;
        text-transform: uppercase; letter-spacing: 0.1em;
        margin: 0.5rem 0 1rem 0;
        padding-left: 0;
    ">{_esc(text)}</h3>
    """, unsafe_allow_html=True)


def footer_text(text: str):
    """Render a styled footer."""
    st.markdown(f"""
    <div style="
        text-align: center; color: #334155;
        padding: 2.5rem 0 1rem 0;
        font-size: 0.75rem; font-family: 'Inter', sans-serif;
        letter-spacing: 0.04em; text-transform: uppercase; font-weight: 500;
    ">{text}</div>
    """, unsafe_allow_html=True)


def nav_cards(items: list):
    """
    Render navigation cards instead of st.info blocks.
    items: list of dicts with keys: title, description, icon (emoji string)
    """
    cols_html = ""
    for item in items:
        icon = item.get('icon', '')
        title = _esc(item.get('title', ''))
        desc = _esc(item.get('description', ''))
        cols_html += f"""
        <div style="
            background: linear-gradient(145deg, rgba(26, 31, 46, 0.8) 0%, rgba(22, 27, 34, 0.9) 100%);
            border: 1px solid #1E2536;
            border-radius: 16px;
            padding: 24px;
            transition: all 0.3s ease;
            cursor: default;
        ">
            <div style="font-size: 1.5rem; margin-bottom: 10px;">{icon}</div>
            <p style="font-family: 'Inter', sans-serif; font-weight: 700; font-size: 0.95rem; color: #E2E8F0; margin: 0 0 6px 0;">{title}</p>
            <p style="font-family: 'Inter', sans-serif; font-size: 0.82rem; color: #64748B; margin: 0; line-height: 1.4;">{desc}</p>
        </div>
        """

    st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat({len(items)}, 1fr); gap: 16px; margin: 1rem 0;">
        {cols_html}
    </div>
    """, unsafe_allow_html=True)
