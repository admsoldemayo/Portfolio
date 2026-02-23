"""
Historial - Evolución Temporal de Carteras
===========================================
Muestra la evolución del valor total y rentabilidad histórica.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# Agregar src y root al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth import require_auth
require_auth()

from config import KNOWN_PORTFOLIOS, CATEGORY_COLORS
from portfolio_tracker import PortfolioTracker

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

st.set_page_config(
    page_title="Historial de Carteras",
    page_icon="📈",
    layout="wide"
)

# =============================================================================
# FUNCIONES
# =============================================================================

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


def create_evolution_chart(df: pd.DataFrame, title: str) -> go.Figure:
    """Crea gráfico de evolución temporal."""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['fecha'],
        y=df['valor_total'],
        mode='lines+markers',
        name='Valor Total',
        line=dict(color='#3366CC', width=3),
        marker=dict(size=8),
        fill='tozeroy',
        fillcolor='rgba(51, 102, 204, 0.2)'
    ))

    fig.update_layout(
        title=title,
        xaxis_title='Fecha',
        yaxis_title='Valor Total ($)',
        height=500,
        hovermode='x unified'
    )

    # Formato del eje Y
    fig.update_yaxis(tickformat=',')

    return fig


def create_returns_chart(returns: dict) -> go.Figure:
    """Crea gráfico de rentabilidad por categoría."""
    by_category = returns.get('by_category', {})

    if not by_category:
        return None

    df_returns = pd.DataFrame([
        {
            'categoria': cat,
            'return_pct': data['return_pct'],
            'return_abs': data['return_abs']
        }
        for cat, data in by_category.items()
    ])

    df_returns = df_returns.sort_values('return_pct', ascending=True)

    # Colorear según positivo/negativo
    colors = ['green' if x >= 0 else 'red' for x in df_returns['return_pct']]

    fig = go.Figure(go.Bar(
        x=df_returns['return_pct'],
        y=df_returns['categoria'],
        orientation='h',
        marker_color=colors,
        text=df_returns['return_pct'].apply(lambda x: f"{x:+.1f}%"),
        textposition='outside'
    ))

    fig.update_layout(
        title='Rentabilidad por Categoría',
        xaxis_title='Rentabilidad (%)',
        yaxis_title='Categoría',
        height=400
    )

    return fig


# =============================================================================
# INTERFAZ PRINCIPAL
# =============================================================================

st.title("📈 Historial de Carteras")
st.markdown("*Evolución temporal y análisis de rentabilidad*")

# Inicializar tracker
tracker = PortfolioTracker()

# =============================================================================
# SELECTOR DE CARTERA
# =============================================================================

st.markdown("---")
col1, col2 = st.columns([2, 3])

with col1:
    st.subheader("Seleccionar Cliente")

    # Opciones del selector
    portfolio_options = {
        f"{info['nombre']} ({comitente})": comitente
        for comitente, info in KNOWN_PORTFOLIOS.items()
    }

    # Agregar opción "Todas las carteras"
    portfolio_options = {"📊 Todas las Carteras": "ALL", **portfolio_options}

    selected_label = st.selectbox(
        "Cliente:",
        options=list(portfolio_options.keys()),
        key="portfolio_selector_hist"
    )

    selected_comitente = portfolio_options[selected_label]

with col2:
    st.subheader("Periodo")

    periodo = st.selectbox(
        "Seleccionar periodo:",
        options=['all', 'ytd', 'mtd', '1m', '3m', '6m', '1y'],
        format_func=lambda x: {
            'all': 'Todo el historial',
            'ytd': 'Año hasta la fecha (YTD)',
            'mtd': 'Mes hasta la fecha (MTD)',
            '1m': 'Último mes',
            '3m': 'Últimos 3 meses',
            '6m': 'Últimos 6 meses',
            '1y': 'Último año'
        }[x],
        key="periodo_selector"
    )

# =============================================================================
# VISTA: TODAS LAS CARTERAS
# =============================================================================

if selected_comitente == "ALL":
    st.markdown("---")
    st.header("📊 Resumen de Todas las Carteras")

    try:
        df_summary = tracker.get_all_portfolios_summary()

        if df_summary.empty:
            st.warning("⚠️ No hay datos históricos disponibles.")
            st.info("Los datos se guardarán automáticamente cuando proceses archivos Excel.")
        else:
            # Métricas agregadas
            valor_total_all = df_summary['valor_total'].sum()
            num_carteras = len(df_summary)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💰 Valor Total Consolidado", format_currency(valor_total_all))
            with col2:
                st.metric("📁 Carteras Monitoreadas", num_carteras)
            with col3:
                ultima_actualizacion = df_summary['fecha'].max()
                st.metric("📅 Última Actualización", ultima_actualizacion)

            # Tabla resumen
            st.markdown("#### Resumen por Cliente")

            df_display = df_summary.copy()
            df_display['valor_total'] = df_display['valor_total'].astype(float).apply(lambda x: format_currency(x, show_full=True))
            df_display['variacion_vs_anterior_pct'] = df_display['variacion_vs_anterior_pct'].apply(
                lambda x: f"{float(x):+.2f}%" if pd.notna(x) and x != '' else "N/A"
            )
            df_display.columns = ['Comitente', 'Nombre', 'Valor Total', 'Fecha', 'Var. vs Anterior']

            st.dataframe(df_display, use_container_width=True, hide_index=True)

            # Gráfico de torta - distribución entre clientes
            st.markdown("---")
            st.subheader("📊 Distribución por Cliente")

            fig_clients = px.pie(
                df_summary,
                values='valor_total',
                names='nombre',
                title='Distribución del Patrimonio Total',
                hole=0.4
            )
            st.plotly_chart(fig_clients, use_container_width=True)

    except Exception as e:
        st.error(f"Error cargando resumen: {e}")

# =============================================================================
# VISTA: CARTERA INDIVIDUAL
# =============================================================================

else:
    portfolio_info = KNOWN_PORTFOLIOS[selected_comitente]

    st.markdown("---")
    st.header(f"📈 {portfolio_info['nombre']}")

    try:
        # Obtener serie temporal
        df_evolution = tracker.get_evolution_series(selected_comitente, periodo)

        if df_evolution.empty:
            st.warning(f"⚠️ No hay datos históricos para el comitente {selected_comitente}")
            st.info("Los datos se guardarán automáticamente la próxima vez que proceses un archivo Excel de este cliente.")
            st.stop()

        # Convertir fecha a datetime si es string
        if df_evolution['fecha'].dtype == 'object':
            df_evolution['fecha'] = pd.to_datetime(df_evolution['fecha'])

        # Métricas principales
        valor_actual = df_evolution.iloc[-1]['valor_total']
        fecha_actual = df_evolution.iloc[-1]['fecha'].strftime('%Y-%m-%d')

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("💰 Valor Actual", format_currency(valor_actual))

        with col2:
            st.metric("📅 Última Actualización", fecha_actual)

        with col3:
            snapshots_count = len(df_evolution)
            st.metric("📸 Snapshots", snapshots_count)

        # =======================================================================
        # GRÁFICO DE EVOLUCIÓN
        # =======================================================================

        st.markdown("---")
        st.subheader("📊 Evolución del Valor Total")

        fig_evolution = create_evolution_chart(
            df_evolution,
            f"Evolución de {portfolio_info['nombre']}"
        )
        st.plotly_chart(fig_evolution, use_container_width=True)

        # =======================================================================
        # ANÁLISIS DE RENTABILIDAD
        # =======================================================================

        if len(df_evolution) >= 2:
            st.markdown("---")
            st.subheader("💹 Análisis de Rentabilidad")

            # Calcular rentabilidad
            returns = tracker.calculate_returns(selected_comitente)

            if 'error' not in returns:
                # Métricas de rentabilidad
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        "Fecha Inicial",
                        returns['fecha_inicio']
                    )

                with col2:
                    st.metric(
                        "Valor Inicial",
                        format_currency(returns['valor_inicio'])
                    )

                with col3:
                    st.metric(
                        "Rentabilidad Total",
                        f"{returns['total_return_pct']:+.2f}%",
                        delta=format_currency(returns['total_return_abs'])
                    )

                with col4:
                    st.metric(
                        "Valor Final",
                        format_currency(returns['valor_fin'])
                    )

                # Gráfico de rentabilidad por categoría
                fig_returns = create_returns_chart(returns)
                if fig_returns:
                    st.plotly_chart(fig_returns, use_container_width=True)

                # Tabla detallada
                st.markdown("#### Detalle por Categoría")

                by_category = returns.get('by_category', {})
                if by_category:
                    df_returns = pd.DataFrame([
                        {
                            'Categoría': cat,
                            'Valor Inicial': format_currency(data['valor_inicio']),
                            'Valor Final': format_currency(data['valor_fin']),
                            'Ganancia/Pérdida': format_currency(data['return_abs']),
                            'Rentabilidad %': f"{data['return_pct']:+.2f}%"
                        }
                        for cat, data in by_category.items()
                    ])

                    df_returns = df_returns.sort_values('Rentabilidad %', ascending=False, key=lambda x: x.str.rstrip('%').astype(float))

                    st.dataframe(df_returns, use_container_width=True, hide_index=True)

            else:
                st.warning(returns['error'])

        else:
            st.info("Se necesitan al menos 2 snapshots para calcular rentabilidad.")

        # =======================================================================
        # TABLA DE HISTORIAL
        # =======================================================================

        st.markdown("---")
        st.subheader("📋 Historial de Snapshots")

        df_display_hist = df_evolution.copy()
        df_display_hist['fecha'] = df_display_hist['fecha'].dt.strftime('%Y-%m-%d')
        df_display_hist['valor_total'] = df_display_hist['valor_total'].astype(float).apply(lambda x: format_currency(x, show_full=True))
        df_display_hist.columns = ['Fecha', 'Valor Total']

        st.dataframe(df_display_hist, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Error cargando historial: {e}")
        st.exception(e)
