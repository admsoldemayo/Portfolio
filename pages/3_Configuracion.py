"""
Configuración - Perfiles y Alocaciones Custom
==============================================
Permite editar perfiles de alocación y definir overrides custom por cliente.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Agregar src y root al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth import require_auth
require_auth()

from config import KNOWN_PORTFOLIOS, DEFAULT_PROFILES, CATEGORIES
from sheets_manager import get_sheets_manager, reset_sheets_manager

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

st.set_page_config(
    page_title="Configuración",
    page_icon="⚙️",
    layout="wide"
)

# =============================================================================
# FUNCIONES
# =============================================================================

def load_profiles() -> dict:
    """Carga perfiles desde Google Sheets."""
    try:
        sheets = get_sheets_manager()
        df_perfiles = sheets.get_perfiles_alocacion()

        if df_perfiles.empty:
            return DEFAULT_PROFILES

        # Convertir porcentaje a numérico
        pct_col = 'objetivo_pct' if 'objetivo_pct' in df_perfiles.columns else 'porcentaje'
        df_perfiles[pct_col] = pd.to_numeric(df_perfiles[pct_col], errors='coerce')

        profiles = {}
        for perfil in df_perfiles['perfil'].unique():
            df_perfil = df_perfiles[df_perfiles['perfil'] == perfil]
            profiles[perfil] = dict(zip(df_perfil['categoria'], df_perfil[pct_col]))

        return profiles

    except Exception as e:
        st.error(f"Error cargando perfiles: {e}")
        return DEFAULT_PROFILES


def save_profile(perfil: str, allocation: dict) -> bool:
    """Guarda un perfil de alocación en Google Sheets."""
    try:
        sheets = get_sheets_manager()

        # Validar que suma 100%
        total = sum(allocation.values())
        if abs(total - 100) > 0.1:
            st.error(f"La suma debe ser 100%. Actualmente: {total:.1f}%")
            return False

        # Preparar datos
        data = []
        for cat, pct in allocation.items():
            if pct > 0:  # Solo guardar categorías con valor
                data.append([perfil, cat, pct])

        if not data:
            st.error("El perfil debe tener al menos una categoría con porcentaje > 0")
            return False

        # Guardar en Sheets
        success = sheets.update_profile_allocation(perfil, allocation)

        if success:
            st.success(f"✅ Perfil '{perfil}' guardado exitosamente")
            return True
        else:
            st.error("Error guardando en Google Sheets")
            return False

    except Exception as e:
        st.error(f"Error guardando perfil: {e}")
        return False


def load_custom_allocations() -> pd.DataFrame:
    """Carga alocaciones custom desde Google Sheets."""
    try:
        sheets = get_sheets_manager()
        return sheets.get_alocacion_custom()
    except Exception as e:
        st.error(f"Error cargando alocaciones custom: {e}")
        return pd.DataFrame()


def save_custom_allocation(comitente: str, categoria: str, porcentaje: float) -> bool:
    """Guarda un override custom para un cliente."""
    try:
        sheets = get_sheets_manager()
        success = sheets.update_custom_allocation(comitente, categoria, porcentaje)

        if success:
            st.success(f"✅ Override guardado: {comitente} - {categoria} = {porcentaje}%")
            return True
        else:
            st.error("Error guardando override")
            return False

    except Exception as e:
        st.error(f"Error: {e}")
        return False


# =============================================================================
# INTERFAZ PRINCIPAL
# =============================================================================

st.title("⚙️ Configuración de Alocaciones")
st.markdown("*Define perfiles de alocación y overrides personalizados por cliente*")

# Tabs para organizar contenido
tab1, tab2, tab3 = st.tabs(["📊 Perfiles Base", "✏️ Overrides Custom", "ℹ️ Información"])

# =============================================================================
# TAB 1: PERFILES BASE
# =============================================================================

with tab1:
    st.header("📊 Perfiles de Alocación Base")

    st.markdown("""
    Los perfiles definen la alocación objetivo por defecto para cada tipo de inversor.
    Cada cliente tiene asignado un perfil base que se puede override con alocaciones custom.
    """)

    # Cargar perfiles
    profiles = load_profiles()

    # Selector de perfil
    st.markdown("---")
    col1, col2 = st.columns([1, 2])

    with col1:
        perfil_seleccionado = st.selectbox(
            "Seleccionar perfil:",
            options=list(profiles.keys()),
            key="perfil_selector"
        )

    with col2:
        st.markdown("##### Clientes con este perfil:")
        clientes = [
            f"{info['nombre']} ({comitente})"
            for comitente, info in KNOWN_PORTFOLIOS.items()
            if info['perfil'] == perfil_seleccionado
        ]
        st.write(", ".join(clientes) if clientes else "Ninguno")

    # Editor de perfil
    st.markdown("---")
    st.subheader(f"Editar Perfil: {perfil_seleccionado.title()}")

    allocation = profiles[perfil_seleccionado].copy()

    # Crear inputs para cada categoría
    col1, col2, col3 = st.columns(3)

    new_allocation = {}
    total_pct = 0

    for i, categoria in enumerate(CATEGORIES):
        current_value = allocation.get(categoria, 0)

        col = [col1, col2, col3][i % 3]

        with col:
            new_value = st.number_input(
                f"{categoria}",
                min_value=0.0,
                max_value=100.0,
                value=float(current_value),
                step=1.0,
                key=f"pct_{perfil_seleccionado}_{categoria}"
            )
            new_allocation[categoria] = new_value
            total_pct += new_value

    # Mostrar total
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        color = "green" if abs(total_pct - 100) < 0.1 else "red"
        st.markdown(f"### Total: :{color}[{total_pct:.1f}%]")

    with col2:
        if abs(total_pct - 100) < 0.1:
            st.success("✅ Suma correcta (100%)")
        else:
            diff = total_pct - 100
            st.error(f"❌ Diferencia: {diff:+.1f}%")

    with col3:
        if st.button("💾 Guardar Perfil", key=f"save_{perfil_seleccionado}"):
            save_profile(perfil_seleccionado, new_allocation)

    # Visualización del perfil
    st.markdown("---")
    st.subheader("Vista Previa")

    # Filtrar solo categorías con valor > 0
    df_preview = pd.DataFrame([
        {'Categoría': cat, 'Porcentaje': pct}
        for cat, pct in new_allocation.items()
        if pct > 0
    ]).sort_values('Porcentaje', ascending=False)

    if not df_preview.empty:
        import plotly.express as px

        fig = px.pie(
            df_preview,
            values='Porcentaje',
            names='Categoría',
            title=f'Perfil {perfil_seleccionado.title()}',
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# TAB 2: OVERRIDES CUSTOM
# =============================================================================

with tab2:
    st.header("✏️ Alocaciones Custom (Overrides)")

    st.markdown("""
    Los overrides custom permiten ajustar la alocación objetivo de un cliente específico
    sin modificar el perfil base. El sistema combina el perfil base + overrides custom.
    """)

    # Cargar overrides existentes
    df_custom = load_custom_allocations()

    if not df_custom.empty:
        st.markdown("---")
        st.subheader("Overrides Activos")

        # Convertir comitente a string para consistencia
        df_custom['comitente'] = df_custom['comitente'].astype(str).str.strip()

        # Agrupar por comitente
        for comitente in df_custom['comitente'].unique():
            df_comitente = df_custom[df_custom['comitente'] == comitente]

            # Obtener nombre
            nombre = KNOWN_PORTFOLIOS.get(comitente, {}).get('nombre', 'Desconocido')
            perfil_base = KNOWN_PORTFOLIOS.get(comitente, {}).get('perfil', 'N/A')

            with st.expander(f"📁 {nombre} ({comitente}) - Perfil base: {perfil_base}"):
                df_display = df_comitente[['categoria', 'objetivo_pct']].copy()
                df_display['objetivo_pct'] = pd.to_numeric(df_display['objetivo_pct'], errors='coerce').fillna(0)
                df_display.columns = ['Categoría', 'Porcentaje Custom']
                df_display['Porcentaje Custom'] = df_display['Porcentaje Custom'].apply(lambda x: f"{x:.1f}%")
                st.dataframe(df_display, use_container_width=True, hide_index=True)

    # Agregar nuevo override
    st.markdown("---")
    st.subheader("➕ Agregar Nuevo Override")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Selector de cliente
        portfolio_options = {
            f"{info['nombre']} ({comitente})": comitente
            for comitente, info in KNOWN_PORTFOLIOS.items()
        }

        selected_label = st.selectbox(
            "Cliente:",
            options=list(portfolio_options.keys()),
            key="custom_portfolio_selector"
        )

        selected_comitente = portfolio_options[selected_label]

    with col2:
        # Selector de categoría
        selected_categoria = st.selectbox(
            "Categoría:",
            options=CATEGORIES,
            key="custom_categoria_selector"
        )

    with col3:
        # Input de porcentaje
        custom_pct = st.number_input(
            "Porcentaje:",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=1.0,
            key="custom_pct_input"
        )

    with col4:
        # Botón guardar
        st.markdown("##")  # Spacer
        if st.button("💾 Guardar Override", key="save_custom"):
            save_custom_allocation(selected_comitente, selected_categoria, custom_pct)

    # Nota informativa
    st.info("""
    **Nota:** Los overrides custom tienen prioridad sobre el perfil base. Si defines un override
    para una categoría, ese porcentaje reemplazará el del perfil base para ese cliente específico.
    """)

# =============================================================================
# TAB 3: INFORMACIÓN
# =============================================================================

with tab3:
    st.header("ℹ️ Información del Sistema")

    st.markdown("---")
    st.subheader("📁 Carteras Configuradas")

    # Crear tabla de portfolios
    df_portfolios = pd.DataFrame([
        {
            'Comitente': comitente,
            'Nombre': info['nombre'],
            'Perfil': info['perfil'].title()
        }
        for comitente, info in KNOWN_PORTFOLIOS.items()
    ])

    st.dataframe(df_portfolios, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("🏷️ Categorías Disponibles")

    st.markdown("""
    - **SPY**: ETFs y acciones USA/Tech (SPY, QQQ, NVDA, AAPL, etc.)
    - **MERV**: Acciones argentinas (YPFD, GGAL, PAMP, etc.)
    - **LETRAS**: Renta fija (bonos, LECAPs, ONs, cheques, pagarés)
    - **GLD**: Oro y mineras de oro (GLD, Barrick, etc.)
    - **SLV**: Plata (SLV)
    - **CRYPTO_BTC**: Bitcoin y ETFs relacionados
    - **CRYPTO_ETH**: Ethereum y ETFs relacionados
    - **BRASIL**: ETFs de Brasil (EWZ)
    - **EXTRAS_COBRE**: Commodities (cobre, uranio, etc.)
    - **LIQUIDEZ**: Efectivo, dólares, pesos, FCIs money market
    - **OTROS**: Activos sin clasificar (revisar manualmente)
    """)

    st.markdown("---")
    st.subheader("📊 Conexión con Google Sheets")

    try:
        sheets = get_sheets_manager()
        from config import SPREADSHEET_ID, SPREADSHEET_NAME

        st.success("✅ Conexión activa")
        st.info(f"**Spreadsheet:** {SPREADSHEET_NAME}")
        st.code(f"ID: {SPREADSHEET_ID}")

        # Mostrar hojas disponibles
        st.markdown("##### Hojas configuradas:")
        st.markdown("""
        - `carteras_maestro`: Registro de carteras y perfiles
        - `perfiles_alocacion`: Perfiles base (conservador, moderado, agresivo)
        - `alocacion_custom`: Overrides personalizados por cliente
        - `historial_tenencias`: Histórico de posiciones por categoría
        - `snapshots_totales`: Evolución del valor total de cada cartera
        """)

    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")

    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray; padding: 20px;'>
    Portfolio Automation System v1.0<br>
    Desarrollado para Sol de Mayo
    </div>
    """, unsafe_allow_html=True)
