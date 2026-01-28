"""
Portfolio Individual - Análisis por Cliente
============================================
Muestra alocación actual vs objetivo, desviaciones y sugerencias de rebalanceo.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import KNOWN_PORTFOLIOS, CATEGORY_COLORS, CATEGORIES, SECTORS, SECTOR_COLORS
from sheets_manager import get_sheets_manager, reset_sheets_manager
from allocation_manager import AllocationManager
from portfolio_tracker import PortfolioTracker
from asset_mapper import ASSET_CATEGORIES, add_custom_mapping, get_category_display_name, classify_sector, get_sector_display_name

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

st.set_page_config(
    page_title="Portfolio Individual",
    page_icon="📁",
    layout="wide"
)

# =============================================================================
# CACHING - Reducir llamadas a Google Sheets API
# =============================================================================

@st.cache_data(ttl=300)  # 5 minutos de cache
def cached_get_historial_tenencias():
    """Carga historial de tenencias con cache."""
    sheets = get_sheets_manager()
    return sheets.get_historial_tenencias()

@st.cache_data(ttl=300)
def cached_get_detalle_activos(comitente: str, fecha: str = None):
    """Carga detalle de activos con cache. Si no se pasa fecha, devuelve la más reciente."""
    sheets = get_sheets_manager()
    return sheets.get_detalle_activos(comitente, fecha)

@st.cache_data(ttl=300)
def cached_get_target_allocation(comitente: str):
    """Carga alocación objetivo con cache."""
    sheets = get_sheets_manager()
    return sheets.get_target_allocation(comitente)

@st.cache_data(ttl=300)
def cached_get_custom_ticker_mappings():
    """Carga mapeos custom de tickers con cache."""
    sheets = get_sheets_manager()
    return sheets.get_custom_ticker_mappings()

@st.cache_data(ttl=300)
def cached_get_custom_profiles():
    """Carga perfiles custom con cache."""
    sheets = get_sheets_manager()
    return sheets.get_custom_profiles()

@st.cache_data(ttl=300)
def cached_get_custom_profile_allocation(nombre: str):
    """Carga alocación de un perfil custom específico."""
    sheets = get_sheets_manager()
    return sheets.get_custom_profile_allocation(nombre)

def clear_all_cache():
    """Limpia todo el cache de datos."""
    cached_get_historial_tenencias.clear()
    cached_get_detalle_activos.clear()
    cached_get_target_allocation.clear()
    cached_get_custom_ticker_mappings.clear()
    cached_get_custom_profiles.clear()


def clear_allocation_widgets(comitente: str):
    """Limpia los widgets de alocación del session state para forzar recarga de valores."""
    from config import CATEGORIES
    keys_to_delete = []
    for cat in CATEGORIES:
        key = f"custom_alloc_{comitente}_{cat}"
        if key in st.session_state:
            keys_to_delete.append(key)
    for key in keys_to_delete:
        del st.session_state[key]

# =============================================================================
# FUNCIONES
# =============================================================================

def get_available_dates_for_comitente(comitente: str) -> list:
    """Obtiene las fechas disponibles para un comitente."""
    try:
        df_hist = cached_get_historial_tenencias()
        if df_hist.empty:
            return []

        # Convertir fecha
        if len(df_hist) > 0:
            sample_fecha = df_hist['fecha'].iloc[0]
            if isinstance(sample_fecha, str) and len(str(sample_fecha)) >= 10 and '-' in str(sample_fecha):
                df_hist['fecha'] = df_hist['fecha'].astype(str)
            else:
                df_hist['fecha'] = pd.to_numeric(df_hist['fecha'], errors='coerce')
                df_hist['fecha'] = pd.to_datetime(df_hist['fecha'], origin='1899-12-30', unit='D', errors='coerce')
                df_hist['fecha'] = df_hist['fecha'].dt.strftime('%Y-%m-%d')

        df_hist['comitente'] = df_hist['comitente'].astype(str).str.strip()
        comitente_str = str(comitente).strip()

        df_filtered = df_hist[df_hist['comitente'] == comitente_str]
        if df_filtered.empty:
            return []

        fechas = sorted(df_filtered['fecha'].unique(), reverse=True)
        return [f for f in fechas if f and f != 'nan']

    except Exception:
        return []


def get_portfolio_data(comitente: str, fecha: str = None) -> pd.DataFrame:
    """Obtiene datos de un portfolio desde Sheets para una fecha específica."""
    try:
        # Usar versión cacheada para reducir llamadas API
        df_hist = cached_get_historial_tenencias()

        if df_hist.empty:
            return pd.DataFrame()

        # Verificar que las columnas necesarias existan
        required_cols = ['fecha', 'comitente', 'valor', 'categoria']
        missing_cols = [col for col in required_cols if col not in df_hist.columns]
        if missing_cols:
            st.error(f"Columnas faltantes en historial: {missing_cols}")
            return pd.DataFrame()

        # Convertir fecha - detectar formato (string ISO o número serial Excel)
        if len(df_hist) > 0:
            sample_fecha = df_hist['fecha'].iloc[0]
            # Si ya es string en formato ISO (YYYY-MM-DD), dejarlo como está
            if isinstance(sample_fecha, str) and len(str(sample_fecha)) >= 10 and '-' in str(sample_fecha):
                df_hist['fecha'] = df_hist['fecha'].astype(str)
            else:
                # Convertir de número serial de Excel
                df_hist['fecha'] = pd.to_numeric(df_hist['fecha'], errors='coerce')
                df_hist['fecha'] = pd.to_datetime(df_hist['fecha'], origin='1899-12-30', unit='D', errors='coerce')
                df_hist['fecha'] = df_hist['fecha'].dt.strftime('%Y-%m-%d')

        # Convertir valores numéricos
        df_hist['valor'] = pd.to_numeric(df_hist['valor'], errors='coerce')
        if 'valor_total_cartera' in df_hist.columns:
            df_hist['valor_total_cartera'] = pd.to_numeric(df_hist['valor_total_cartera'], errors='coerce')

        # Convertir comitente a string para comparación consistente
        df_hist['comitente'] = df_hist['comitente'].astype(str).str.strip()
        comitente_str = str(comitente).strip()

        # Filtrar por comitente
        df_filtered = df_hist[df_hist['comitente'] == comitente_str]
        if df_filtered.empty:
            return pd.DataFrame()

        # Filtrar por fecha específica o última disponible
        if fecha:
            df_result = df_filtered[df_filtered['fecha'] == fecha]
        else:
            ultima_fecha = df_filtered['fecha'].max()
            df_result = df_filtered[df_filtered['fecha'] == ultima_fecha]

        return df_result

    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()


def format_currency(value, show_full=False):
    """
    Formatea un número como moneda con formato argentino.

    Args:
        value: Valor numérico
        show_full: Si True, muestra el número completo con decimales.
    """
    if pd.isna(value):
        return "N/A"

    value = float(value)

    if show_full:
        formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"${formatted}"
    else:
        if value >= 1_000_000_000:
            formatted = f"{value/1_000_000_000:,.2f}B".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"${formatted}"
        elif value >= 1_000_000:
            formatted = f"{value/1_000_000:,.2f}M".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"${formatted}"
        else:
            formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"${formatted}"


def create_comparison_chart(comparison_df: pd.DataFrame) -> go.Figure:
    """Crea gráfico de comparación actual vs objetivo."""
    fig = go.Figure()

    # Actual
    fig.add_trace(go.Bar(
        name='Actual',
        x=comparison_df['categoria'],
        y=comparison_df['actual_pct'],
        marker_color='lightblue',
        hovertemplate='<b>%{x}</b><br>Actual: %{y:.1f}%<extra></extra>'
    ))

    # Objetivo
    fig.add_trace(go.Bar(
        name='Objetivo',
        x=comparison_df['categoria'],
        y=comparison_df['objetivo_pct'],
        marker_color='orange',
        hovertemplate='<b>%{x}</b><br>Objetivo: %{y:.1f}%<extra></extra>'
    ))

    fig.update_layout(
        title='Alocación: Actual vs Objetivo',
        xaxis_title='Categoría',
        yaxis_title='Porcentaje (%)',
        barmode='group',
        height=400,
        hoverlabel=dict(bgcolor="white", font_size=12)
    )

    return fig


def create_status_chart(comparison_df: pd.DataFrame) -> go.Figure:
    """Crea gráfico de desviaciones por categoría."""
    # Ordenar por desviación absoluta
    df_sorted = comparison_df.sort_values('desviacion', ascending=True)

    # Color según status
    colors = df_sorted['status'].map({
        'OK': 'green',
        'SOBRE': 'red',
        'BAJO': 'orange'
    })

    # Crear texto de hover personalizado
    hover_texts = df_sorted.apply(
        lambda r: f"<b>{r['categoria']}</b><br>Desviación: {r['desviacion']:+.1f}%<br>Estado: {r['status']}",
        axis=1
    )

    fig = go.Figure(go.Bar(
        x=df_sorted['desviacion'],
        y=df_sorted['categoria'],
        orientation='h',
        marker_color=colors,
        text=df_sorted['desviacion'].apply(lambda x: f"{x:+.1f}%"),
        textposition='outside',
        hovertext=hover_texts,
        hoverinfo='text'
    ))

    fig.update_layout(
        title='Desviaciones por Categoría',
        xaxis_title='Desviación (puntos porcentuales)',
        yaxis_title='Categoría',
        height=400,
        hoverlabel=dict(bgcolor="white", font_size=12)
    )

    return fig


# =============================================================================
# INTERFAZ PRINCIPAL
# =============================================================================

st.title("📁 Portfolio Individual")
st.markdown("*Análisis detallado por cliente: alocación, comparación y sugerencias*")

# Selector de cartera
st.markdown("---")
col1, col2 = st.columns([2, 3])

with col1:
    st.subheader("Seleccionar Cliente")

    # Opciones del selector
    portfolio_options = {
        f"{info['nombre']} ({comitente})": comitente
        for comitente, info in KNOWN_PORTFOLIOS.items()
    }

    selected_label = st.selectbox(
        "Cliente:",
        options=list(portfolio_options.keys()),
        key="portfolio_selector"
    )

    selected_comitente = portfolio_options[selected_label]
    portfolio_info = KNOWN_PORTFOLIOS[selected_comitente]

with col2:
    st.subheader("Información del Cliente")
    col_a, col_b, col_c = st.columns([2, 2, 1])
    with col_a:
        st.metric("Comitente", selected_comitente)
    with col_b:
        st.metric("Perfil", portfolio_info['perfil'].title())
    with col_c:
        if st.button("🔄 Refrescar", help="Limpiar cache y recargar datos desde Google Sheets"):
            clear_all_cache()
            st.rerun()

# Selector de fecha
st.markdown("---")
fechas_disponibles = get_available_dates_for_comitente(selected_comitente)

col_fecha1, col_fecha2, col_fecha3 = st.columns([2, 2, 1])

with col_fecha1:
    if fechas_disponibles:
        fecha_options = ["Última disponible"] + fechas_disponibles
        selected_fecha_option = st.selectbox(
            "📅 Fecha de datos:",
            options=fecha_options,
            index=0,
            key="fecha_selector",
            help="Selecciona una fecha para ver datos históricos"
        )
        selected_fecha = None if selected_fecha_option == "Última disponible" else selected_fecha_option
    else:
        selected_fecha = None
        st.info("No hay fechas históricas disponibles")

with col_fecha2:
    if fechas_disponibles:
        fecha_mostrar = selected_fecha if selected_fecha else fechas_disponibles[0]
        st.metric("📆 Fecha de los datos", fecha_mostrar)

with col_fecha3:
    if fechas_disponibles and len(fechas_disponibles) > 1:
        st.caption(f"📊 {len(fechas_disponibles)} fechas disponibles")

# Inicializar sheets manager para uso global
sheets = get_sheets_manager()

# Cargar datos - más resiliente a errores
df_portfolio = pd.DataFrame()
portfolio_load_error = None

with st.spinner("Cargando datos..."):
    try:
        df_portfolio = get_portfolio_data(selected_comitente, selected_fecha)
    except Exception as e:
        portfolio_load_error = str(e)

# Cargar también detalle de activos (para edición) - usar cache con fecha seleccionada
df_activos = cached_get_detalle_activos(selected_comitente, selected_fecha)
has_activos = not df_activos.empty

# Mostrar estado
if portfolio_load_error:
    st.error(f"Error cargando historial: {portfolio_load_error}")

if df_portfolio.empty and not has_activos:
    st.warning(f"⚠️ No hay datos para el comitente {selected_comitente}")
    st.info("Los datos se guardarán automáticamente la próxima vez que proceses un archivo Excel de este cliente.")
    st.stop()

# Si no hay historial pero sí hay activos, permitir ver activos
if df_portfolio.empty and has_activos:
    st.warning("⚠️ No hay datos de historial agregado, pero hay activos individuales guardados.")
    st.info("Puedes ver y editar los activos abajo. Para ver el análisis de alocación, procesa un Excel con datos actualizados.")

# =============================================================================
# ANÁLISIS DE ALOCACIÓN (usa detalle_activos si está disponible para reflejar cambios de clasificación)
# =============================================================================

# Determinar qué datos usar para el análisis
# Prioridad: detalle_activos (tiene clasificaciones actualizadas) > historial_tenencias
if has_activos:
    # Usar detalle_activos con clasificaciones actualizadas
    df_analysis = df_activos[['categoria', 'valor']].copy()
    df_analysis = df_analysis.groupby('categoria').agg({'valor': 'sum'}).reset_index()
    valor_total = df_analysis['valor'].sum()
    # Usar la fecha seleccionada o la última disponible
    ultima_fecha = selected_fecha if selected_fecha else (fechas_disponibles[0] if fechas_disponibles else "Sin fecha")
    has_data_for_analysis = True
elif not df_portfolio.empty:
    # Fallback a historial_tenencias
    df_analysis = df_portfolio[['categoria', 'valor']].copy()
    valor_total = df_analysis['valor'].sum()
    ultima_fecha = df_portfolio.iloc[0]['fecha']
    has_data_for_analysis = True
else:
    has_data_for_analysis = False

if has_data_for_analysis:
    st.markdown("---")
    st.header("📊 Análisis de Alocación")

    # Obtener TC para conversión a USD (con retry si hay error SSL)
    try:
        tc_info = sheets.get_tc_for_comitente(selected_comitente)
    except Exception as e:
        if 'SSL' in str(e) or 'ssl' in str(e) or 'DECRYPTION' in str(e):
            # Error SSL - resetear conexión y reintentar
            reset_sheets_manager()
            sheets = get_sheets_manager()
            try:
                tc_info = sheets.get_tc_for_comitente(selected_comitente)
            except Exception:
                tc_info = {'tc_mep': 1200, 'tc_ccl': 1200}
        else:
            tc_info = {'tc_mep': 1200, 'tc_ccl': 1200}
    tc_mep = tc_info.get('tc_mep', 1200)  # Default si no hay TC
    valor_total_usd = valor_total / tc_mep if tc_mep > 0 else 0

    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Valor Total ARS", format_currency(valor_total))
    with col2:
        st.metric("💵 Valor Total USD", f"USD {valor_total_usd:,.0f}")
    with col3:
        st.metric("📅 Fecha Datos", ultima_fecha)
    with col4:
        categorias_count = df_analysis['categoria'].nunique()
        st.metric("🏷️ Categorías", categorias_count)

    # Realizar análisis con AllocationManager
    manager = AllocationManager()

    try:
        target, comparison, suggestions = manager.analyze_portfolio(df_analysis, selected_comitente)

        # ==========================================================================
        # COMPARACIÓN ACTUAL VS OBJETIVO
        # ==========================================================================

        st.markdown("---")
        st.subheader("📈 Comparación Actual vs Objetivo")

        col1, col2 = st.columns(2)

        with col1:
            # Gráfico de barras comparativo
            fig_comparison = create_comparison_chart(comparison)
            st.plotly_chart(fig_comparison, use_container_width=True)

        with col2:
            # Gráfico de desviaciones
            fig_status = create_status_chart(comparison)
            st.plotly_chart(fig_status, use_container_width=True)

        # Tabla de comparación
        st.markdown("#### Tabla de Comparación")

        df_display = comparison.copy()
        df_display['actual_pct'] = df_display['actual_pct'].apply(lambda x: f"{x:.1f}%")
        df_display['objetivo_pct'] = df_display['objetivo_pct'].apply(lambda x: f"{x:.1f}%")
        df_display['desviacion'] = df_display['desviacion'].apply(lambda x: f"{x:+.1f}%")

        # Color coding para status
        def color_status(val):
            if val == 'OK':
                return 'background-color: #d4edda'
            elif val == 'SOBRE':
                return 'background-color: #f8d7da'
            else:
                return 'background-color: #fff3cd'

        styled_df = df_display.style.applymap(color_status, subset=['status'])

        st.dataframe(
            df_display[['categoria', 'actual_pct', 'objetivo_pct', 'desviacion', 'status']],
            use_container_width=True,
            hide_index=True
        )

        # ==========================================================================
        # SUGERENCIAS DE REBALANCEO
        # ==========================================================================

        if suggestions:
            st.markdown("---")
            st.subheader("💡 Sugerencias de Rebalanceo")

            # Crear DataFrame de sugerencias
            df_sugg = pd.DataFrame(suggestions)

            # Separar por acción
            comprar = df_sugg[df_sugg['accion'] == 'COMPRAR']
            vender = df_sugg[df_sugg['accion'] == 'VENDER']

            col1, col2 = st.columns(2)

            with col1:
                if not comprar.empty:
                    st.markdown("##### 🟢 Comprar / Aumentar")
                    for _, row in comprar.iterrows():
                        st.success(
                            f"**{row['categoria']}**: {format_currency(row['monto_sugerido'])} "
                            f"({row['desviacion_pct']:.1f}% bajo objetivo)"
                        )

            with col2:
                if not vender.empty:
                    st.markdown("##### 🔴 Vender / Reducir")
                    for _, row in vender.iterrows():
                        st.error(
                            f"**{row['categoria']}**: {format_currency(row['monto_sugerido'])} "
                            f"({row['desviacion_pct']:+.1f}% sobre objetivo)"
                        )

            # Resumen de montos
            total_comprar = comprar['monto_sugerido'].sum() if not comprar.empty else 0
            total_vender = vender['monto_sugerido'].sum() if not vender.empty else 0

            st.info(
                f"**Resumen**: Vender ~{format_currency(total_vender)} de categorías sobrerepresentadas "
                f"y comprar ~{format_currency(total_comprar)} en categorías subrepresentadas."
            )

        else:
            st.success("✅ Portfolio en equilibrio. No se requieren ajustes significativos.")

        # ==========================================================================
        # PIE CHARTS COMPARATIVOS
        # ==========================================================================

        st.markdown("---")
        st.subheader("🥧 Distribución de Cartera")

        col1, col2 = st.columns(2)

        with col1:
            # Actual
            actual_data = comparison[comparison['actual_pct'] > 0][['categoria', 'actual_pct']].copy()
            # Calcular valor desde porcentaje
            actual_data['valor'] = (actual_data['actual_pct'] / 100) * valor_total
            colors_actual = [CATEGORY_COLORS.get(cat, '#999999') for cat in actual_data['categoria']]

            fig_actual = px.pie(
                actual_data,
                values='actual_pct',
                names='categoria',
                title='Alocación Actual',
                hole=0.4,
                color_discrete_sequence=colors_actual
            )
            fig_actual.update_traces(
                hovertemplate='<b>%{label}</b><br>Porcentaje: %{value:.1f}%<br>Valor: $%{customdata:,.0f}<extra></extra>',
                customdata=actual_data['valor']
            )
            fig_actual.update_layout(hoverlabel=dict(bgcolor="white", font_size=12))
            st.plotly_chart(fig_actual, use_container_width=True)

        with col2:
            # Objetivo
            objetivo_data = comparison[comparison['objetivo_pct'] > 0][['categoria', 'objetivo_pct']].copy()
            colors_objetivo = [CATEGORY_COLORS.get(cat, '#999999') for cat in objetivo_data['categoria']]

            fig_objetivo = px.pie(
                objetivo_data,
                values='objetivo_pct',
                names='categoria',
                title='Alocación Objetivo',
                hole=0.4,
                color_discrete_sequence=colors_objetivo
            )
            fig_objetivo.update_traces(
                hovertemplate='<b>%{label}</b><br>Objetivo: %{value:.1f}%<extra></extra>'
            )
            fig_objetivo.update_layout(hoverlabel=dict(bgcolor="white", font_size=12))
            st.plotly_chart(fig_objetivo, use_container_width=True)

    except Exception as e:
        st.error(f"Error realizando análisis: {e}")
        st.exception(e)

    # =============================================================================
    # DETALLE DE POSICIONES (por categoría agregada)
    # =============================================================================

    st.markdown("---")
    st.header("📝 Detalle de Posiciones")

    # Usar df_analysis que ya está preparado con los datos correctos
    df_summary = df_analysis.copy()
    df_summary = df_summary.sort_values('valor', ascending=False)
    df_summary['porcentaje'] = (df_summary['valor'] / df_summary['valor'].sum() * 100).round(1)

    df_display_detail = df_summary.copy()
    df_display_detail['valor'] = df_display_detail['valor'].apply(lambda x: format_currency(x, show_full=True))
    df_display_detail['porcentaje'] = df_display_detail['porcentaje'].apply(lambda x: f"{x:.2f}%")
    df_display_detail.columns = ['Categoría', 'Valor', '% Total']

    st.dataframe(df_display_detail, use_container_width=True, hide_index=True)

# =============================================================================
# VER/EDITAR ACTIVOS INDIVIDUALES
# =============================================================================

st.markdown("---")
st.header("🔍 Activos Individuales")

# Ya tenemos df_activos cargado arriba

if not df_activos.empty:
    # Mostrar TC del archivo
    tc_info = sheets.get_tc_for_comitente(selected_comitente)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💱 TC MEP", f"${tc_info['tc_mep']:,.2f}")
    with col2:
        st.metric("💱 TC CCL", f"${tc_info['tc_ccl']:,.2f}")
    with col3:
        st.metric("📊 Total Activos", len(df_activos))

    st.markdown("---")
    st.subheader(f"📋 Activos de {portfolio_info['nombre']}")

    # Preparar datos para edición (incluyendo sector)
    cols_to_use = ['ticker', 'descripcion', 'valor', 'categoria']
    if 'sector' in df_activos.columns:
        cols_to_use.append('sector')
    df_edit = df_activos[cols_to_use].copy()

    # Si no hay columna sector, calcularla
    if 'sector' not in df_edit.columns:
        df_edit['sector'] = df_edit.apply(
            lambda r: classify_sector(r['ticker'], r['categoria']), axis=1
        )

    df_edit = df_edit.sort_values('valor', ascending=False)

    # Opciones
    cat_options = CATEGORIES
    sector_options = SECTORS

    # ---- FILTROS ----
    st.markdown("##### 🔍 Filtros")
    filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 1])

    with filter_col1:
        # Filtro por categoría
        unique_cats = ["Todas"] + sorted(df_edit['categoria'].unique().tolist())
        selected_cat_filter = st.selectbox(
            "Filtrar por Categoría:",
            options=unique_cats,
            key=f"filter_cat_{selected_comitente}"
        )

    with filter_col2:
        # Filtro por sector
        unique_sectors = ["Todos"] + sorted(df_edit['sector'].unique().tolist())
        selected_sector_filter = st.selectbox(
            "Filtrar por Sector:",
            options=unique_sectors,
            key=f"filter_sector_{selected_comitente}"
        )

    with filter_col3:
        st.markdown("##")  # Spacer
        if st.button("Limpiar filtros", key=f"clear_filters_{selected_comitente}"):
            st.rerun()

    # Aplicar filtros
    df_filtered = df_edit.copy()
    if selected_cat_filter != "Todas":
        df_filtered = df_filtered[df_filtered['categoria'] == selected_cat_filter]
    if selected_sector_filter != "Todos":
        df_filtered = df_filtered[df_filtered['sector'] == selected_sector_filter]

    # Mostrar conteo con filtros aplicados
    filter_info = ""
    if selected_cat_filter != "Todas" or selected_sector_filter != "Todos":
        filter_info = f" (filtrado de {len(df_edit)} total)"

    st.info(f"**{len(df_filtered)} activos**{filter_info} | Edita Categoría y Sector con los dropdowns")

    # Header de la tabla (5 columnas)
    col1, col2, col3, col4, col5 = st.columns([1.5, 2.5, 1.5, 1.5, 1.5])
    with col1:
        st.markdown("**Ticker**")
    with col2:
        st.markdown("**Descripción**")
    with col3:
        st.markdown("**Valor**")
    with col4:
        st.markdown("**Categoría**")
    with col5:
        st.markdown("**Sector**")

    st.markdown("---")

    # Mostrar cada activo con dropdowns para categoría y sector
    changes_made = []

    for idx, row in df_filtered.iterrows():
        col1, col2, col3, col4, col5 = st.columns([1.5, 2.5, 1.5, 1.5, 1.5])

        with col1:
            st.text(row['ticker'])
        with col2:
            desc = str(row['descripcion'])[:25] + "..." if len(str(row['descripcion'])) > 25 else str(row['descripcion'])
            st.text(desc)
        with col3:
            st.text(format_currency(row['valor'], show_full=True))

        # Dropdown Categoría
        with col4:
            current_cat = row['categoria']
            current_cat_idx = cat_options.index(current_cat) if current_cat in cat_options else len(cat_options) - 1

            new_cat = st.selectbox(
                "Cat",
                options=cat_options,
                index=current_cat_idx,
                key=f"cat_{selected_comitente}_{row['ticker']}_{idx}",
                label_visibility="collapsed"
            )

        # Dropdown Sector
        with col5:
            current_sector = row.get('sector', 'N/A')
            if current_sector not in sector_options:
                current_sector = 'N/A'
            current_sector_idx = sector_options.index(current_sector) if current_sector in sector_options else len(sector_options) - 1

            new_sector = st.selectbox(
                "Sector",
                options=sector_options,
                index=current_sector_idx,
                key=f"sector_{selected_comitente}_{row['ticker']}_{idx}",
                label_visibility="collapsed"
            )

        # Registrar cambios
        if new_cat != current_cat or new_sector != row.get('sector', 'N/A'):
            changes_made.append({
                'ticker': row['ticker'],
                'old_cat': current_cat,
                'new_cat': new_cat if new_cat != current_cat else None,
                'old_sector': row.get('sector', 'N/A'),
                'new_sector': new_sector if new_sector != row.get('sector', 'N/A') else None
            })

    # Botón para guardar cambios de clasificación
    if changes_made:
        st.markdown("---")
        st.warning(f"⚠️ {len(changes_made)} cambio(s) pendiente(s) de guardar")

        for change in changes_made:
            changes_desc = []
            if change['new_cat']:
                changes_desc.append(f"Cat: {change['old_cat']} → {change['new_cat']}")
            if change['new_sector']:
                changes_desc.append(f"Sector: {change['old_sector']} → {change['new_sector']}")
            st.write(f"  • **{change['ticker']}**: {', '.join(changes_desc)}")

        if st.button("💾 Guardar Cambios", key="save_classification_changes"):
            try:
                saved = 0
                for change in changes_made:
                    # 1. Guardar mapeos persistentes
                    if change['new_cat']:
                        sheets.save_custom_ticker_mapping(
                            change['ticker'],
                            change['new_cat'],
                            f"Reclasificado desde {change['old_cat']}"
                        )
                        add_custom_mapping(change['ticker'], change['new_cat'])

                    if change['new_sector']:
                        sheets.save_custom_sector_mapping(
                            change['ticker'],
                            change['new_sector'],
                            f"Sector reclasificado"
                        )

                    # 2. Actualizar detalle_activos inmediatamente
                    sheets.update_activo_classification(
                        comitente=selected_comitente,
                        ticker=change['ticker'],
                        categoria=change['new_cat'],
                        sector=change['new_sector']
                    )
                    saved += 1

                st.success(f"✅ {saved} activo(s) actualizado(s)")
                # Limpiar cache para que se recarguen los datos actualizados
                cached_get_detalle_activos.clear()
                st.rerun()  # Recargar para ver cambios
            except Exception as e:
                st.error(f"Error guardando: {e}")

    # Resumen por categoría
    st.markdown("---")
    st.subheader("📊 Resumen por Categoría")

    df_cat_summary = df_edit.groupby('categoria').agg({
        'valor': 'sum',
        'ticker': 'count'
    }).reset_index()
    df_cat_summary.columns = ['Categoría', 'Valor', 'Activos']
    df_cat_summary['%'] = (df_cat_summary['Valor'] / df_cat_summary['Valor'].sum() * 100).round(1)
    df_cat_summary = df_cat_summary.sort_values('Valor', ascending=False)
    df_cat_summary['Valor'] = df_cat_summary['Valor'].apply(lambda x: format_currency(x, show_full=True))
    df_cat_summary['%'] = df_cat_summary['%'].apply(lambda x: f"{x:.1f}%")

    st.dataframe(df_cat_summary, use_container_width=True, hide_index=True)

    # Resumen por sector
    st.markdown("---")
    st.subheader("🏭 Resumen por Sector")

    df_sector_summary = df_edit.groupby('sector').agg({
        'valor': 'sum',
        'ticker': 'count'
    }).reset_index()
    df_sector_summary.columns = ['Sector', 'Valor', 'Activos']
    df_sector_summary['%'] = (df_sector_summary['Valor'] / df_sector_summary['Valor'].sum() * 100).round(1)
    df_sector_summary = df_sector_summary.sort_values('Valor', ascending=False)

    # Pie chart de sectores
    col1, col2 = st.columns([1, 1])

    with col1:
        df_sector_display = df_sector_summary.copy()
        df_sector_display['Valor_fmt'] = df_sector_display['Valor'].apply(lambda x: format_currency(x, show_full=True))
        df_sector_display['%_fmt'] = df_sector_display['%'].apply(lambda x: f"{x:.1f}%")
        st.dataframe(
            df_sector_display[['Sector', 'Valor_fmt', 'Activos', '%_fmt']].rename(
                columns={'Valor_fmt': 'Valor', '%_fmt': '%'}
            ),
            use_container_width=True,
            hide_index=True
        )

    with col2:
        # Pie chart
        colors_sector = [SECTOR_COLORS.get(s, '#808080') for s in df_sector_summary['Sector']]
        fig_sector = px.pie(
            df_sector_summary,
            values='Valor',
            names='Sector',
            title='Distribución por Sector',
            color_discrete_sequence=colors_sector,
            hole=0.4,
            custom_data=['%', 'Activos']
        )
        fig_sector.update_traces(
            hovertemplate='<b>%{label}</b><br>Valor: $%{value:,.0f}<br>Porcentaje: %{customdata[0]:.1f}%<br>Activos: %{customdata[1]}<extra></extra>'
        )
        fig_sector.update_layout(height=350, hoverlabel=dict(bgcolor="white", font_size=12))
        st.plotly_chart(fig_sector, use_container_width=True)

else:
    st.warning(f"⚠️ No hay activos detallados guardados para {portfolio_info['nombre']}")
    st.info("💡 Los activos se guardarán automáticamente la próxima vez que proceses un archivo Excel de este cliente.")

# =============================================================================
# EDITAR ALOCACIÓN PERSONALIZADA
# =============================================================================

st.markdown("---")
st.header("✏️ Editar Alocación Objetivo")
st.markdown(f"*Ajusta los porcentajes objetivo para **{portfolio_info['nombre']}** ({selected_comitente})*")

# Cargar alocación actual (base + custom) - usar cache
current_target = cached_get_target_allocation(selected_comitente)
base_profile = portfolio_info['perfil']

# Selector de perfil de cartera
from config import DEFAULT_PROFILES

# Obtener perfiles custom disponibles
custom_profiles = cached_get_custom_profiles()

# Construir opciones: Default profiles + Custom profiles
profile_options = list(DEFAULT_PROFILES.keys())
profile_labels = {p: f"📊 {p.title()}" for p in profile_options}

# Agregar perfiles custom con prefijo distintivo
for cp in custom_profiles:
    profile_options.append(f"custom:{cp}")
    profile_labels[f"custom:{cp}"] = f"⭐ {cp}"

profile_col1, profile_col2, profile_col3 = st.columns([2, 1, 2])

with profile_col1:
    selected_profile = st.selectbox(
        "📊 Cargar perfil:",
        options=profile_options,
        index=profile_options.index(base_profile) if base_profile in profile_options else 0,
        key=f"profile_selector_{selected_comitente}",
        format_func=lambda x: profile_labels.get(x, x.title())
    )

with profile_col2:
    st.markdown("##")  # Spacer
    if st.button("📥 Cargar Perfil", key=f"load_profile_{selected_comitente}"):
        # Determinar si es perfil default o custom
        if selected_profile.startswith("custom:"):
            # Perfil custom
            profile_name = selected_profile.replace("custom:", "")
            profile_values = cached_get_custom_profile_allocation(profile_name)
        else:
            # Perfil default
            profile_values = DEFAULT_PROFILES.get(selected_profile, {})

        # Guardar como custom allocation para este comitente
        full_allocation = {cat: profile_values.get(cat, 0.0) for cat in CATEGORIES}
        try:
            sheets.set_custom_allocation_batch(selected_comitente, full_allocation)
            cached_get_target_allocation.clear()
            clear_allocation_widgets(selected_comitente)  # Limpiar widgets para que tomen nuevos valores
            profile_display = profile_name if selected_profile.startswith("custom:") else selected_profile.title()
            st.success(f"✅ Perfil '{profile_display}' cargado")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

with profile_col3:
    # Mostrar perfiles custom disponibles
    if custom_profiles:
        st.info(f"**Perfil base:** {base_profile.title()}\n\n**Custom:** {len(custom_profiles)} guardados")
    else:
        st.info(f"**Perfil base:** {base_profile.title()}")

# Crear inputs para cada categoría
col1, col2, col3 = st.columns(3)
custom_allocation = {}
total_custom_pct = 0

for i, categoria in enumerate(CATEGORIES):
    current_value = current_target.get(categoria, 0)
    col = [col1, col2, col3][i % 3]

    with col:
        new_value = st.number_input(
            f"{categoria}",
            min_value=0.0,
            max_value=100.0,
            value=float(current_value),
            step=1.0,
            key=f"custom_alloc_{selected_comitente}_{categoria}"
        )
        custom_allocation[categoria] = new_value
        total_custom_pct += new_value

# Mostrar total y botón guardar
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    color = "green" if abs(total_custom_pct - 100) < 0.1 else "red"
    st.markdown(f"### Total: :{color}[{total_custom_pct:.1f}%]")

with col2:
    if abs(total_custom_pct - 100) < 0.1:
        st.success("✅ Suma correcta (100%)")
    else:
        diff = total_custom_pct - 100
        st.error(f"❌ Diferencia: {diff:+.1f}%")

with col3:
    if st.button("💾 Guardar Alocación Custom", key=f"save_custom_alloc_{selected_comitente}"):
        if abs(total_custom_pct - 100) > 0.1:
            st.error(f"La suma debe ser 100%. Actualmente: {total_custom_pct:.1f}%")
        else:
            try:
                # Guardar TODAS las categorías de una vez (batch)
                sheets.set_custom_allocation_batch(selected_comitente, custom_allocation)
                st.success(f"✅ Alocación guardada: {len(custom_allocation)} categorías actualizadas para {selected_comitente}")
                # Limpiar cache de alocación Y historial para actualizar análisis
                cached_get_target_allocation.clear()
                cached_get_historial_tenencias.clear()
                st.rerun()  # Recargar para ver cambios
            except Exception as e:
                st.error(f"Error guardando alocación: {e}")

# =============================================================================
# GUARDAR COMO PERFIL REUTILIZABLE
# =============================================================================

st.markdown("---")
st.subheader("⭐ Guardar como Perfil Reutilizable")
st.markdown("*Guarda esta alocación como un perfil que podrás usar en cualquier cliente*")

profile_save_col1, profile_save_col2, profile_save_col3 = st.columns([2, 1, 2])

with profile_save_col1:
    # Sugerir nombre basado en el cliente actual
    suggested_name = portfolio_info['nombre'].title()
    new_profile_name = st.text_input(
        "Nombre del perfil:",
        value=suggested_name,
        placeholder="Ej: Felipe Lopez, Perfil Conservador Plus",
        key=f"new_profile_name_{selected_comitente}"
    )

with profile_save_col2:
    st.markdown("##")  # Spacer
    if st.button("⭐ Guardar Perfil", key=f"save_as_profile_{selected_comitente}"):
        if not new_profile_name.strip():
            st.error("Ingresa un nombre para el perfil")
        elif abs(total_custom_pct - 100) > 0.1:
            st.error(f"La suma debe ser 100% antes de guardar. Actualmente: {total_custom_pct:.1f}%")
        else:
            try:
                # Guardar como perfil reutilizable
                sheets.save_custom_profile(
                    nombre=new_profile_name.strip(),
                    allocations=custom_allocation,
                    creado_por=portfolio_info['nombre']
                )
                # Limpiar cache de perfiles custom
                cached_get_custom_profiles.clear()
                st.success(f"✅ Perfil '{new_profile_name}' guardado. Ahora está disponible en el selector de perfiles.")
                st.rerun()
            except Exception as e:
                st.error(f"Error guardando perfil: {e}")

with profile_save_col3:
    # Mostrar perfiles guardados con opción de eliminar
    if custom_profiles:
        st.markdown("**Perfiles guardados:**")
        for cp in custom_profiles[:5]:  # Mostrar máximo 5
            col_name, col_del = st.columns([3, 1])
            with col_name:
                st.text(f"⭐ {cp}")
            with col_del:
                if st.button("🗑️", key=f"del_profile_{cp}", help=f"Eliminar {cp}"):
                    try:
                        sheets.delete_custom_profile(cp)
                        cached_get_custom_profiles.clear()
                        st.success(f"Perfil '{cp}' eliminado")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
        if len(custom_profiles) > 5:
            st.caption(f"... y {len(custom_profiles) - 5} más")
    else:
        st.info("No hay perfiles guardados aún")

# =============================================================================
# CLASIFICACIÓN DE ACTIVOS
# =============================================================================

st.markdown("---")
st.header("🏷️ Clasificación de Activos")
st.markdown("*Agrega reglas de clasificación para tickers no reconocidos*")

# Cargar mapeos custom desde Google Sheets - usar cache
try:
    custom_mappings = cached_get_custom_ticker_mappings()
    # Aplicar mapeos custom al diccionario en memoria
    for ticker, cat in custom_mappings.items():
        if ticker and cat:
            ASSET_CATEGORIES[ticker] = cat
except Exception as e:
    st.warning(f"No se pudieron cargar mapeos custom: {e}")
    custom_mappings = {}

# Mostrar mapeos custom guardados
if custom_mappings:
    st.subheader("📋 Mapeos Personalizados Guardados")
    df_custom_mapeos = pd.DataFrame(
        [(t, c, get_category_display_name(c)) for t, c in custom_mappings.items()],
        columns=['Ticker', 'Categoría', 'Nombre']
    )
    st.dataframe(df_custom_mapeos, use_container_width=True, hide_index=True)

# Mostrar mapeos del sistema
with st.expander("📋 Ver mapeos del sistema (primeros 50)"):
    mapeos_list = list(ASSET_CATEGORIES.items())[:50]
    df_mapeos = pd.DataFrame(mapeos_list, columns=['Ticker', 'Categoría'])
    df_mapeos['Nombre Categoría'] = df_mapeos['Categoría'].apply(get_category_display_name)
    st.dataframe(df_mapeos, use_container_width=True, hide_index=True)
    st.info(f"Total de mapeos configurados: {len(ASSET_CATEGORIES)}")

# Formulario para agregar nuevo mapeo
st.subheader("➕ Agregar Nueva Regla de Clasificación")

col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    nuevo_ticker = st.text_input(
        "Ticker/Símbolo:",
        placeholder="Ej: AAPL, MELI, etc.",
        key="nuevo_ticker_clasificacion"
    ).upper().strip()

with col2:
    categoria_options = {get_category_display_name(cat): cat for cat in CATEGORIES}
    selected_cat_label = st.selectbox(
        "Categoría:",
        options=list(categoria_options.keys()),
        key="nueva_categoria_clasificacion"
    )
    nueva_categoria = categoria_options[selected_cat_label]

with col3:
    st.markdown("##")  # Spacer para alinear
    if st.button("➕ Agregar", key="btn_agregar_mapeo"):
        if nuevo_ticker:
            try:
                # Guardar en Google Sheets (persistente)
                success = sheets.save_custom_ticker_mapping(nuevo_ticker, nueva_categoria)
                if success:
                    # También agregar al diccionario en memoria
                    add_custom_mapping(nuevo_ticker, nueva_categoria)
                    st.success(f"✅ Mapeo guardado: {nuevo_ticker} → {selected_cat_label}")
                    # Limpiar cache de mapeos
                    cached_get_custom_ticker_mappings.clear()
                    st.rerun()  # Recargar para ver cambios
                else:
                    st.error("Error guardando el mapeo")
            except ValueError as e:
                st.error(f"Error: {e}")
        else:
            st.warning("⚠️ Ingresa un ticker válido")

# Nota explicativa
st.info("""
**¿Cómo funciona la clasificación?**
1. Los tickers se buscan primero en los mapeos personalizados (guardados en Google Sheets)
2. Luego en el diccionario de mapeos del sistema
3. Si no se encuentra, se aplican reglas de patrones (LECAPs, bonos, etc.)
4. Si aún no se clasifica, queda como "Sin Clasificar" (OTROS)

Los mapeos que agregues aquí se guardan en Google Sheets y persisten entre sesiones.
""")
