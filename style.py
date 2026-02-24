"""
Style Module - Obsidian Finance Theme
======================================
Dark, refined dashboard aesthetic with gold accents.
Inject CSS + Plotly dark theme for the Portfolio Dashboard.
"""

import streamlit as st


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
    'text_primary': '#E2E8F0',
    'text_secondary': '#8B95A5',
    'border': '#21262D',
    'border_hover': '#30363D',
}

# Refined chart colors for dark backgrounds
CHART_COLORS = [
    '#C9A54E',   # Gold
    '#10B981',   # Emerald
    '#3B82F6',   # Blue
    '#8B5CF6',   # Violet
    '#EF4444',   # Red
    '#F59E0B',   # Amber
    '#06B6D4',   # Cyan
    '#EC4899',   # Pink
    '#F97316',   # Orange
    '#14B8A6',   # Teal
    '#A78BFA',   # Light violet
    '#6366F1',   # Indigo
]

# Category colors optimized for dark backgrounds
CATEGORY_COLORS_DARK = {
    "SPY": "#3B82F6",
    "MERV": "#10B981",
    "BONOS_SOBERANOS_USD": "#60A5FA",
    "LETRAS": "#F59E0B",
    "GLD": "#C9A54E",
    "SLV": "#94A3B8",
    "CRYPTO_BTC": "#F7931A",
    "CRYPTO_ETH": "#818CF8",
    "BRASIL": "#22C55E",
    "EXTRAS_COBRE": "#D97706",
    "LIQUIDEZ": "#06B6D4",
    "OTROS": "#6B7280",
}


# =============================================================================
# CSS INJECTION
# =============================================================================

def inject_css():
    """Inject the Obsidian Finance theme CSS."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* ===== BASE TYPOGRAPHY ===== */
    html, body, [class*="css"] {
        font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* Page container - tighter padding */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* ===== HEADINGS ===== */
    h1 {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.03em !important;
        background: linear-gradient(135deg, #C9A54E 0%, #E8D5A3 50%, #C9A54E 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        padding-bottom: 0.15em;
    }

    h2 {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em !important;
        color: #E2E8F0 !important;
        border-bottom: 1px solid #21262D;
        padding-bottom: 0.4em;
        margin-top: 1.5em;
    }

    h3 {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em !important;
        color: #CBD5E1 !important;
    }

    /* ===== METRIC CARDS ===== */
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #1A1F2E 0%, #161B22 100%);
        border: 1px solid #21262D;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }

    [data-testid="stMetric"]:hover {
        border-color: rgba(201, 165, 78, 0.35);
        box-shadow: 0 8px 25px rgba(201, 165, 78, 0.12);
        transform: translateY(-2px);
    }

    [data-testid="stMetricLabel"] {
        color: #8B95A5 !important;
    }

    [data-testid="stMetricLabel"] p {
        font-size: 0.78rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 600 !important;
        color: #E2E8F0 !important;
    }

    [data-testid="stMetricDelta"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.85rem !important;
    }

    /* ===== SIDEBAR ===== */
    [data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(180deg, #0D1117 0%, #131820 50%, #161B22 100%);
        border-right: 1px solid #21262D;
    }

    [data-testid="stSidebar"] h1 {
        font-size: 1.2rem !important;
        -webkit-text-fill-color: #C9A54E !important;
        background: none !important;
    }

    [data-testid="stSidebar"] h3 {
        color: #C9A54E !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    /* Sidebar nav links */
    [data-testid="stSidebarNav"] li a {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 500 !important;
        border-radius: 8px;
        transition: all 0.2s ease;
    }

    [data-testid="stSidebarNav"] li a:hover {
        background-color: rgba(201, 165, 78, 0.08);
    }

    [data-testid="stSidebarNav"] li a[aria-selected="true"] {
        background-color: rgba(201, 165, 78, 0.12);
        border-left: 3px solid #C9A54E;
    }

    /* ===== BUTTONS ===== */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #C9A54E 0%, #B8923E 100%) !important;
        color: #0E1117 !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.5rem;
        box-shadow: 0 2px 10px rgba(201, 165, 78, 0.25);
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        letter-spacing: 0.01em;
    }

    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="stBaseButton-primary"]:hover {
        box-shadow: 0 6px 20px rgba(201, 165, 78, 0.4) !important;
        transform: translateY(-1px);
    }

    .stButton > button[kind="secondary"],
    .stButton > button[data-testid="stBaseButton-secondary"],
    .stButton > button:not([kind="primary"]):not([data-testid="stBaseButton-primary"]) {
        border: 1px solid #30363D !important;
        border-radius: 8px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 500 !important;
        transition: all 0.2s ease;
        background: transparent !important;
    }

    .stButton > button:not([kind="primary"]):not([data-testid="stBaseButton-primary"]):hover {
        border-color: #C9A54E !important;
        color: #C9A54E !important;
        background: rgba(201, 165, 78, 0.06) !important;
    }

    /* ===== DATAFRAME / TABLES ===== */
    [data-testid="stDataFrame"] {
        border: 1px solid #21262D;
        border-radius: 10px;
        overflow: hidden;
    }

    [data-testid="stDataFrame"] table {
        font-family: 'DM Sans', sans-serif !important;
    }

    /* ===== DIVIDERS ===== */
    hr {
        border-color: #21262D !important;
        opacity: 0.6;
        margin: 1.2rem 0 !important;
    }

    /* ===== EXPANDERS ===== */
    [data-testid="stExpander"] {
        border: 1px solid #21262D;
        border-radius: 10px;
        overflow: hidden;
        background: #161B22;
    }

    [data-testid="stExpander"] summary {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 500;
    }

    /* ===== ALERTS (info, success, warning, error) ===== */
    .stAlert {
        border-radius: 10px !important;
        border-left-width: 4px !important;
        font-family: 'DM Sans', sans-serif !important;
    }

    /* ===== TABS ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 10px 24px;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 500;
    }

    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        border-bottom: 2px solid #C9A54E;
    }

    /* ===== FILE UPLOADER ===== */
    [data-testid="stFileUploader"] {
        border: 2px dashed #30363D !important;
        border-radius: 12px;
        transition: all 0.3s ease;
    }

    [data-testid="stFileUploader"]:hover {
        border-color: #C9A54E !important;
        background: rgba(201, 165, 78, 0.03);
    }

    [data-testid="stFileUploader"] small {
        color: #8B95A5 !important;
    }

    /* ===== INPUTS (select, number, text) ===== */
    [data-testid="stSelectbox"],
    [data-testid="stNumberInput"],
    [data-testid="stTextInput"] {
        font-family: 'DM Sans', sans-serif !important;
    }

    [data-baseweb="select"] > div {
        border-radius: 8px !important;
        border-color: #21262D !important;
        transition: border-color 0.2s ease;
    }

    [data-baseweb="select"] > div:hover {
        border-color: #C9A54E !important;
    }

    [data-baseweb="input"] {
        border-radius: 8px !important;
    }

    /* ===== MULTISELECT ===== */
    [data-testid="stMultiSelect"] span[data-baseweb="tag"] {
        background-color: rgba(201, 165, 78, 0.15) !important;
        border: 1px solid rgba(201, 165, 78, 0.3) !important;
        border-radius: 6px !important;
        color: #C9A54E !important;
    }

    /* ===== PROGRESS BAR ===== */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #C9A54E 0%, #E8D5A3 100%) !important;
    }

    /* ===== CHECKBOX ===== */
    [data-testid="stCheckbox"] label span {
        font-family: 'DM Sans', sans-serif !important;
    }

    /* ===== SCROLLBAR ===== */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }

    ::-webkit-scrollbar-track {
        background: #0E1117;
    }

    ::-webkit-scrollbar-thumb {
        background: #30363D;
        border-radius: 3px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: rgba(201, 165, 78, 0.5);
    }

    /* ===== HIDE STREAMLIT BRANDING ===== */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* ===== CUSTOM CAPTION STYLING ===== */
    .stCaption, [data-testid="stCaptionContainer"] {
        font-family: 'DM Sans', sans-serif !important;
        color: #6B7280 !important;
    }

    /* ===== FORM STYLING ===== */
    [data-testid="stForm"] {
        border: 1px solid #21262D;
        border-radius: 12px;
        padding: 1.5rem;
        background: #161B22;
    }

    </style>
    """, unsafe_allow_html=True)


# =============================================================================
# PLOTLY THEME
# =============================================================================

def get_plotly_theme() -> dict:
    """Get Plotly layout overrides for the dark finance theme."""
    return dict(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(
            family='DM Sans, -apple-system, sans-serif',
            color='#8B95A5',
            size=12,
        ),
        title=dict(
            font=dict(
                size=15,
                color='#E2E8F0',
                family='DM Sans, sans-serif',
            ),
            x=0,
            xanchor='left',
            pad=dict(b=12),
        ),
        xaxis=dict(
            gridcolor='#1E2330',
            gridwidth=0.5,
            zerolinecolor='#21262D',
            tickfont=dict(size=11, color='#6B7280'),
            title_font=dict(size=12, color='#8B95A5'),
        ),
        yaxis=dict(
            gridcolor='#1E2330',
            gridwidth=0.5,
            zerolinecolor='#21262D',
            tickfont=dict(size=11, color='#6B7280'),
            title_font=dict(size=12, color='#8B95A5'),
        ),
        hoverlabel=dict(
            bgcolor='#1A1F2E',
            font_size=12,
            font_family='DM Sans, sans-serif',
            font_color='#E2E8F0',
            bordercolor='#30363D',
        ),
        colorway=CHART_COLORS,
        legend=dict(
            bgcolor='rgba(0,0,0,0)',
            font=dict(size=11, color='#8B95A5'),
        ),
        margin=dict(l=20, r=20, t=50, b=20),
    )


def apply_plotly_theme(fig):
    """Apply the dark finance theme to a Plotly figure. Returns the figure."""
    fig.update_layout(**get_plotly_theme())
    return fig


def styled_pie_chart(fig):
    """Extra styling for pie/donut charts."""
    apply_plotly_theme(fig)
    fig.update_traces(
        textfont=dict(
            family='DM Sans, sans-serif',
            size=11,
            color='#E2E8F0',
        ),
        marker=dict(
            line=dict(color='#0E1117', width=2)
        ),
    )
    return fig


# =============================================================================
# STYLED COMPONENTS
# =============================================================================

def page_header(title: str, subtitle: str = ""):
    """Render a styled page header (use instead of st.title)."""
    sub_html = ""
    if subtitle:
        sub_html = f'<p style="color: #8B95A5; font-size: 0.95rem; margin: 4px 0 0 0; font-family: DM Sans, sans-serif;">{subtitle}</p>'

    st.markdown(f"""
    <div style="margin-bottom: 0.5rem;">
        <h1 style="
            font-family: 'DM Sans', sans-serif;
            font-size: 2rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            background: linear-gradient(135deg, #C9A54E 0%, #E8D5A3 50%, #C9A54E 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin: 0;
            padding: 0;
            line-height: 1.2;
        ">{title}</h1>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)


def login_header():
    """Render the login page header with Sol de Mayo branding."""
    st.markdown("""
    <div style="
        text-align: center;
        padding: 3rem 0 1.5rem 0;
    ">
        <div style="
            display: inline-block;
            width: 64px;
            height: 64px;
            background: linear-gradient(135deg, #C9A54E 0%, #E8D5A3 50%, #B8923E 100%);
            border-radius: 16px;
            margin-bottom: 1.2rem;
            box-shadow: 0 8px 30px rgba(201, 165, 78, 0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.8rem;
            margin-left: auto;
            margin-right: auto;
        ">
            <span style="display:block;text-align:center;line-height:64px;width:64px;">&#9670;</span>
        </div>
        <h1 style="
            font-family: 'DM Sans', sans-serif;
            font-size: 1.8rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            background: linear-gradient(135deg, #C9A54E 0%, #E8D5A3 50%, #C9A54E 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin: 0 0 0.3rem 0;
        ">Portfolio Dashboard</h1>
        <p style="
            color: #6B7280;
            font-size: 0.9rem;
            margin: 0;
            font-family: 'DM Sans', sans-serif;
            letter-spacing: 0.04em;
        ">Sol de Mayo &middot; Santo Domingo</p>
    </div>
    """, unsafe_allow_html=True)


def section_header(text: str):
    """Render a styled section header."""
    st.markdown(f"""
    <h3 style="
        font-family: 'DM Sans', sans-serif;
        font-weight: 600;
        color: #CBD5E1;
        font-size: 1.1rem;
        margin: 0.5rem 0;
        letter-spacing: -0.01em;
    ">{text}</h3>
    """, unsafe_allow_html=True)


def footer_text(text: str):
    """Render a styled footer."""
    st.markdown(f"""
    <div style="
        text-align: center;
        color: #4B5563;
        padding: 2rem 0 1rem 0;
        font-size: 0.8rem;
        font-family: 'DM Sans', sans-serif;
        letter-spacing: 0.02em;
    ">{text}</div>
    """, unsafe_allow_html=True)
