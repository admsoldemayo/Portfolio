"""
Portfolio Dashboard - Interfaz Web
===================================
Aplicación Streamlit para procesar y visualizar carteras de inversión.

Ejecutar con: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
import sys
import tempfile
import os

# Agregar src al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent / "src"))

from asset_mapper import (
    classify_asset,
    get_category_display_name,
    get_all_categories,
    load_custom_mappings_from_sheets,
    get_category_exposure,
    get_exposure_summary
)
from config import CATEGORY_EXPOSURE, EXPOSURE_COLORS
from ingest import (
    detect_broker_format,
    parse_iol_stonex_format,
    read_excel_safe,
    standardize_dataframe,
    clean_numeric,
    save_to_sheets
)
from portfolio_tracker import PortfolioTracker
from sheets_manager import get_sheets_manager
from config import KNOWN_PORTFOLIOS, SPREADSHEET_ID

# =============================================================================
# CONFIGURACIÓN DE LA PÁGINA
# =============================================================================

st.set_page_config(
    page_title="Portfolio Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Colores por categoría para gráficos
CATEGORY_COLORS = {
    "SPY": "#3366CC",
    "MERV": "#109618",
    "BONOS_SOBERANOS_USD": "#1E90FF",
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


# =============================================================================
# FUNCIONES DE PROCESAMIENTO
# =============================================================================

def process_uploaded_file(uploaded_file) -> pd.DataFrame:
    """Procesa un archivo subido y retorna DataFrame clasificado."""

    # Guardar temporalmente el archivo
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        # Detectar formato
        broker_format = detect_broker_format(tmp_path)

        if broker_format == "iol_stonex":
            df = parse_iol_stonex_format(tmp_path)
        else:
            df_raw = read_excel_safe(tmp_path)
            df = standardize_dataframe(df_raw, uploaded_file.name)

        if df.empty:
            return pd.DataFrame()

        # Asegurar clasificación
        if 'categoria' not in df.columns:
            df['categoria'] = df.apply(
                lambda row: classify_asset(
                    row.get('ticker', ''),
                    row.get('descripcion', '')
                ),
                axis=1
            )

        if 'categoria_nombre' not in df.columns:
            df['categoria_nombre'] = df['categoria'].apply(get_category_display_name)

        df['fuente'] = uploaded_file.name
        df['fecha_proceso'] = datetime.now().isoformat()

        return df

    finally:
        # Limpiar archivo temporal
        os.unlink(tmp_path)


def format_currency(value, show_full=False):
    """
    Formatea un número como moneda con formato argentino.

    Args:
        value: Valor numérico
        show_full: Si True, muestra el número completo con decimales.
                   Si False, abrevia millones/billones.
    """
    if pd.isna(value):
        return "N/A"

    value = float(value)

    if show_full:
        # Formato completo: $1.234.567,89
        formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"${formatted}"
    else:
        # Formato abreviado para valores grandes
        if value >= 1_000_000_000:
            formatted = f"{value/1_000_000_000:,.2f}B".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"${formatted}"
        elif value >= 1_000_000:
            formatted = f"{value/1_000_000:,.2f}M".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"${formatted}"
        else:
            # Para valores menores a 1M, mostrar completo
            formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"${formatted}"


# =============================================================================
# INTERFAZ PRINCIPAL
# =============================================================================

def main():
    st.title("📊 Portfolio Dashboard - Sol de Mayo")
    st.markdown("*Sistema de gestión y análisis de carteras de inversión*")

    # Cargar mapeos custom desde Google Sheets al inicio
    try:
        custom_count = load_custom_mappings_from_sheets()
        if custom_count > 0:
            st.sidebar.success(f"✅ {custom_count} mapeos custom cargados")
    except Exception:
        pass  # Silenciosamente ignorar si no hay conexión

    # Navegación rápida
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("**📁 Portfolio Individual**\nAnaliza carteras por cliente con comparación vs objetivo")
    with col2:
        st.info("**📈 Historial**\nVisualiza evolución temporal y rentabilidad")
    with col3:
        st.info("**⚙️ Configuración**\nEdita perfiles de alocación y overrides")

    # Sidebar - Upload
    with st.sidebar:
        st.header("📁 Cargar Archivos")

        uploaded_files = st.file_uploader(
            "Arrastra archivos Excel de tu broker",
            type=['xlsx', 'xls'],
            accept_multiple_files=True,
            help="Soporta formato IOL, PPI, Balanz, StoneX y otros brokers argentinos"
        )

        # Opción de auto-guardar
        auto_save_sheets = st.checkbox(
            "💾 Guardar automáticamente en Google Sheets",
            value=True,
            help="Si está activado, guardará los snapshots en Google Sheets automáticamente"
        )

        st.markdown("---")
        st.markdown("### Categorías")
        st.markdown("""
        - **USA/Tech**: SPY, QQQ, acciones USA
        - **Argentina**: Acciones MERV
        - **Renta Fija**: Bonos, LECAPs, cheques
        - **Oro**: GLD, mineras de oro
        - **Plata**: SLV
        - **Crypto BTC**: Bitcoin ETFs
        - **Crypto ETH**: Ethereum ETFs
        - **Brasil**: EWZ
        - **Commodities**: Cobre, uranio
        - **Liquidez**: Pesos, USD, FCIs
        """)

    # Contenido principal
    if not uploaded_files:
        st.info("👆 Sube uno o más archivos Excel desde el panel izquierdo para comenzar")

        # Mostrar resumen de carteras desde Google Sheets
        st.markdown("---")
        st.markdown("### 📊 Resumen de Carteras Cargadas")

        try:
            sheets = get_sheets_manager()

            # Selector de fecha histórica
            available_dates = sheets.get_available_dates()

            if available_dates:
                col_date1, col_date2 = st.columns([2, 3])
                with col_date1:
                    selected_date = st.selectbox(
                        "📅 Seleccionar fecha de datos",
                        options=["Último disponible"] + available_dates,
                        help="Seleccioná una fecha para ver datos históricos"
                    )

                    if selected_date != "Último disponible":
                        st.info(f"Mostrando datos del: **{selected_date}**")

            tracker = PortfolioTracker()
            df_portfolios = tracker.get_all_portfolios_summary()

            if not df_portfolios.empty:
                # Obtener TC guardado desde los archivos procesados
                sheets = get_sheets_manager()
                all_tc = sheets.get_all_tc()

                # Calcular TC promedio de los archivos
                tc_values = [tc['tc_mep'] for tc in all_tc.values() if tc['tc_mep'] > 0]
                tc_default = sum(tc_values) / len(tc_values) if tc_values else 1150.0

                # Configuración: Tipo de cambio y filtros
                st.markdown("#### ⚙️ Configuración")
                col_config1, col_config2 = st.columns([1, 3])

                with col_config1:
                    if tc_values:
                        st.metric("💱 TC MEP (archivo)", f"${tc_default:,.2f}")
                        tipo_cambio = tc_default
                    else:
                        tipo_cambio = st.number_input(
                            "💵 Tipo de Cambio (ARS/USD)",
                            min_value=100.0,
                            max_value=5000.0,
                            value=1150.0,
                            step=10.0,
                            help="Tipo de cambio para convertir pesos a dólares"
                        )

                with col_config2:
                    # Multiselect para filtrar carteras
                    todas_carteras = df_portfolios['nombre'].tolist()
                    carteras_visibles = st.multiselect(
                        "👁️ Carteras a mostrar (deselecciona para omitir)",
                        options=todas_carteras,
                        default=todas_carteras,
                        help="Selecciona qué carteras incluir en el análisis"
                    )

                # Filtrar por carteras seleccionadas
                if carteras_visibles:
                    df_portfolios = df_portfolios[df_portfolios['nombre'].isin(carteras_visibles)]
                else:
                    st.warning("⚠️ No hay carteras seleccionadas")
                    return

                # Calcular totales
                df_portfolios['valor_total'] = df_portfolios['valor_total'].astype(float)
                valor_total_ars = df_portfolios['valor_total'].sum()
                valor_total_usd = valor_total_ars / tipo_cambio

                # Mostrar métricas
                st.markdown("---")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("💰 Total ARS", format_currency(valor_total_ars))
                with col2:
                    st.metric("💵 Total USD", f"USD {valor_total_usd:,.2f}".replace(",", "."))
                with col3:
                    st.metric("👥 Carteras", len(df_portfolios))
                with col4:
                    fecha = df_portfolios['fecha'].iloc[0] if len(df_portfolios) > 0 else "N/A"
                    st.metric("📅 Fecha Datos", fecha)

                # Tabla de carteras con formato correcto
                st.markdown("---")
                st.markdown("#### Detalle por Cartera")

                df_display = df_portfolios[['comitente', 'nombre', 'valor_total', 'fecha']].copy()

                # Agregar columna USD
                df_display['valor_usd'] = df_display['valor_total'] / tipo_cambio

                # Calcular porcentaje del total
                df_display['pct_total'] = (df_display['valor_total'] / valor_total_ars * 100).round(2)

                # Ordenar por valor descendente antes de formatear
                df_display = df_display.sort_values('valor_total', ascending=False)

                # Formatear valores
                df_display['valor_total_fmt'] = df_display['valor_total'].apply(lambda x: format_currency(x, show_full=True))
                df_display['valor_usd_fmt'] = df_display['valor_usd'].apply(lambda x: f"USD {x:,.2f}".replace(",", "."))
                df_display['pct_total_fmt'] = df_display['pct_total'].apply(lambda x: f"{x:.2f}%")

                # Seleccionar columnas para mostrar
                df_final = df_display[['comitente', 'nombre', 'valor_total_fmt', 'valor_usd_fmt', 'fecha', 'pct_total_fmt']].copy()
                df_final.columns = ['Comitente', 'Nombre', 'Valor ARS', 'Valor USD', 'Fecha', '% Total']

                # Agregar fila de TOTALES
                totals_row = pd.DataFrame([{
                    'Comitente': '',
                    'Nombre': '📊 TOTAL',
                    'Valor ARS': format_currency(valor_total_ars, show_full=True),
                    'Valor USD': f"USD {valor_total_usd:,.2f}".replace(",", "."),
                    'Fecha': '',
                    '% Total': '100.00%'
                }])
                df_final = pd.concat([df_final, totals_row], ignore_index=True)

                st.dataframe(df_final, use_container_width=True, hide_index=True)

                # Mostrar TC usado
                st.caption(f"💱 Tipo de cambio usado: ARS {tipo_cambio:,.2f} por USD")

                # Gráfico de distribución
                col1, col2 = st.columns(2)
                with col1:
                    fig = px.pie(
                        df_portfolios,
                        values='valor_total',
                        names='nombre',
                        title='Distribución del Patrimonio por Cliente',
                        hole=0.4
                    )
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    # Gráfico de barras en USD
                    df_bar = df_display.copy()
                    df_bar = df_bar.sort_values('valor_usd', ascending=True)

                    fig_bar = px.bar(
                        df_bar,
                        x='valor_usd',
                        y='nombre',
                        title='Valor por Cartera (USD)',
                        orientation='h',
                        text=df_bar['valor_usd'].apply(lambda x: f"USD {x/1000000:.2f}M")
                    )
                    fig_bar.update_traces(textposition='outside')
                    fig_bar.update_layout(xaxis_title="Valor (USD)")
                    st.plotly_chart(fig_bar, use_container_width=True)

                # Fila de totales
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"### 💰 **TOTAL ARS: {format_currency(valor_total_ars, show_full=True)}**")
                with col2:
                    st.markdown(f"### 💵 **TOTAL USD: USD {valor_total_usd:,.2f}**".replace(",", "."))

            else:
                st.info("No hay datos cargados. Sube archivos Excel para comenzar.")

        except Exception as e:
            st.warning(f"No se pudieron cargar los datos: {e}")
            st.exception(e)
            st.info("Sube archivos Excel para comenzar a analizar carteras.")

        return

    # Procesar archivos
    all_dfs = []

    with st.spinner("Procesando archivos..."):
        progress_bar = st.progress(0)

        for i, file in enumerate(uploaded_files):
            df = process_uploaded_file(file)
            if not df.empty:
                all_dfs.append(df)
            progress_bar.progress((i + 1) / len(uploaded_files))

    if not all_dfs:
        st.error("No se pudieron procesar los archivos. Verifica el formato.")
        return

    # Consolidar datos
    df_master = pd.concat(all_dfs, ignore_index=True)

    # Guardar en Google Sheets si está habilitado
    if auto_save_sheets:
        st.markdown("---")
        st.subheader("💾 Guardando en Google Sheets")

        with st.spinner("Guardando snapshots en Google Sheets..."):
            try:
                results = save_to_sheets(df_master, auto_save=True)

                if results:
                    # Contar éxitos y errores
                    exitos = sum(1 for r in results.values() if 'error' not in r)
                    errores = len(results) - exitos

                    if errores == 0:
                        st.success(f"✅ Todos los snapshots guardados exitosamente: {exitos} cartera(s)")
                    else:
                        st.warning(f"⚠️ Guardado parcial: {exitos} éxitos, {errores} errores")

                    # Mostrar detalles en tabla
                    detalles = []
                    for comitente, result in results.items():
                        nombre = KNOWN_PORTFOLIOS.get(comitente, {}).get('nombre', 'Desconocido')

                        if 'error' in result:
                            detalles.append({
                                'Comitente': comitente,
                                'Nombre': nombre,
                                'Estado': '❌ Error',
                                'Detalle': result['error']
                            })
                        else:
                            variacion = result.get('variacion_pct', 'N/A')
                            detalles.append({
                                'Comitente': comitente,
                                'Nombre': nombre,
                                'Estado': '✅ Guardado',
                                'Detalle': f"Variación: {variacion}"
                            })

                    df_detalles = pd.DataFrame(detalles)
                    st.dataframe(df_detalles, use_container_width=True, hide_index=True)

                    # Link directo a Google Sheets
                    from config import SPREADSHEET_ID
                    sheets_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
                    st.info(f"📊 [Ver datos en Google Sheets]({sheets_url})")

                else:
                    st.warning("⚠️ No se guardaron datos. Verifica que los archivos tengan metadata válida (comitente, fecha).")

            except Exception as e:
                st.error(f"❌ Error guardando en Google Sheets: {e}")
                st.exception(e)

    # ==========================================================================
    # MÉTRICAS PRINCIPALES
    # ==========================================================================

    st.markdown("---")

    total_valor = df_master['valor'].sum()
    total_posiciones = len(df_master)
    total_archivos = df_master['fuente'].nunique()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("💰 Valor Total", format_currency(total_valor))
    with col2:
        st.metric("📈 Posiciones", total_posiciones)
    with col3:
        st.metric("📁 Archivos", total_archivos)
    with col4:
        categorias_usadas = df_master['categoria'].nunique()
        st.metric("🏷️ Categorías", categorias_usadas)

    # ==========================================================================
    # GRÁFICOS
    # ==========================================================================

    st.markdown("---")
    st.header("📊 Distribución de Cartera")

    # Agrupar por categoría
    df_summary = df_master.groupby(['categoria', 'categoria_nombre']).agg({
        'valor': 'sum',
        'ticker': 'count'
    }).reset_index()
    df_summary.columns = ['categoria', 'categoria_nombre', 'valor', 'posiciones']
    df_summary['porcentaje'] = (df_summary['valor'] / df_summary['valor'].sum() * 100).round(1)
    df_summary = df_summary.sort_values('valor', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        # Pie chart
        colors = [CATEGORY_COLORS.get(cat, '#999999') for cat in df_summary['categoria']]

        fig_pie = px.pie(
            df_summary,
            values='valor',
            names='categoria_nombre',
            title='Distribución por Categoría',
            hole=0.4,
            color_discrete_sequence=colors
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        # Bar chart
        fig_bar = px.bar(
            df_summary,
            x='categoria_nombre',
            y='valor',
            title='Valor por Categoría',
            color='categoria',
            color_discrete_map=CATEGORY_COLORS,
            text=df_summary['valor'].apply(format_currency)
        )
        fig_bar.update_traces(textposition='outside')
        fig_bar.update_layout(showlegend=False, xaxis_tickangle=-45)
        st.plotly_chart(fig_bar, use_container_width=True)

    # ==========================================================================
    # EXPOSICIÓN ARGENTINA vs EXTERIOR
    # ==========================================================================

    st.markdown("---")
    st.header("🌎 Exposición Geográfica")

    # Calcular exposición
    exposure_data = []
    for _, row in df_summary.iterrows():
        exposure_data.append({
            'categoria': row['categoria'],
            'valor': row['valor']
        })

    exposure_summary = get_exposure_summary(exposure_data)

    col_exp1, col_exp2, col_exp3 = st.columns([1, 2, 1])

    with col_exp1:
        st.markdown("### Resumen")
        for exp_type, data in exposure_summary.items():
            color = EXPOSURE_COLORS.get(exp_type, "#808080")
            emoji = "🇦🇷" if exp_type == "ARGENTINA" else "🌍"
            st.markdown(f"""
            **{emoji} {exp_type}**
            - Valor: {format_currency(data['valor'], show_full=True)}
            - Porcentaje: **{data['pct']:.1f}%**
            """)

    with col_exp2:
        # Gráfico de exposición
        df_exposure = pd.DataFrame([
            {"Exposición": f"🇦🇷 Argentina", "Valor": exposure_summary['ARGENTINA']['valor'], "Tipo": "ARGENTINA"},
            {"Exposición": f"🌍 Exterior", "Valor": exposure_summary['EXTERIOR']['valor'], "Tipo": "EXTERIOR"}
        ])

        fig_exp = px.pie(
            df_exposure,
            values='Valor',
            names='Exposición',
            title='Distribución por Exposición',
            color='Tipo',
            color_discrete_map={
                "ARGENTINA": EXPOSURE_COLORS['ARGENTINA'],
                "EXTERIOR": EXPOSURE_COLORS['EXTERIOR']
            },
            hole=0.4
        )
        fig_exp.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_exp, use_container_width=True)

    with col_exp3:
        # Desglose por categoría con exposición
        st.markdown("### Por Categoría")
        for exp_type in ['ARGENTINA', 'EXTERIOR']:
            emoji = "🇦🇷" if exp_type == "ARGENTINA" else "🌍"
            st.markdown(f"**{emoji} {exp_type}:**")
            for _, row in df_summary.iterrows():
                cat_exposure = get_category_exposure(row['categoria'])
                if cat_exposure == exp_type:
                    st.caption(f"  • {row['categoria_nombre']}: {row['porcentaje']:.1f}%")

    # ==========================================================================
    # TABLA RESUMEN CON USD
    # ==========================================================================

    st.markdown("---")
    st.header("📋 Resumen por Categoría")

    # Obtener TC
    try:
        sheets = get_sheets_manager()
        all_tc = sheets.get_all_tc()
        tc_values = [tc['tc_mep'] for tc in all_tc.values() if tc['tc_mep'] > 0]
        tipo_cambio = sum(tc_values) / len(tc_values) if tc_values else 1150.0
    except Exception:
        tipo_cambio = 1150.0

    df_display = df_summary[['categoria_nombre', 'valor', 'posiciones', 'porcentaje']].copy()
    df_display['valor_usd'] = df_display['valor'] / tipo_cambio
    df_display['exposicion'] = df_summary['categoria'].apply(get_category_exposure)

    df_display.columns = ['Categoría', 'Valor ARS', 'Posiciones', '% Total', 'Valor USD', 'Exposición']
    df_display['Valor ARS'] = df_display['Valor ARS'].apply(lambda x: format_currency(x, show_full=True))
    df_display['Valor USD'] = df_display['Valor USD'].apply(lambda x: f"USD {x:,.2f}".replace(",", "."))
    df_display['% Total'] = df_display['% Total'].apply(lambda x: f"{x:.2f}%")

    st.dataframe(df_display, use_container_width=True, hide_index=True)
    st.caption(f"💱 TC usado: ARS {tipo_cambio:,.2f}")

    # ==========================================================================
    # DETALLE DE ACTIVOS (CON % Y USD)
    # ==========================================================================

    st.markdown("---")
    st.header("📝 Detalle de Activos por Ticker")

    # Filtro por categoría
    categorias = ['Todas'] + list(df_master['categoria_nombre'].unique())
    categoria_filtro = st.selectbox("Filtrar por categoría:", categorias)

    if categoria_filtro != 'Todas':
        df_filtered = df_master[df_master['categoria_nombre'] == categoria_filtro]
    else:
        df_filtered = df_master

    # Calcular porcentaje por ticker
    df_show = df_filtered[['ticker', 'descripcion', 'cantidad', 'valor', 'categoria_nombre', 'categoria']].copy()
    df_show['pct_total'] = (df_show['valor'] / total_valor * 100)
    df_show['valor_usd'] = df_show['valor'] / tipo_cambio
    df_show['exposicion'] = df_show['categoria'].apply(get_category_exposure)

    # Ordenar por valor
    df_show = df_show.sort_values('valor', ascending=False)

    # Formatear para display
    df_display = df_show[['ticker', 'descripcion', 'cantidad', 'valor', 'valor_usd', 'pct_total', 'categoria_nombre', 'exposicion']].copy()
    df_display.columns = ['Ticker', 'Descripción', 'Cantidad', 'Valor ARS', 'Valor USD', '% Total', 'Categoría', 'Exposición']
    df_display['Valor ARS'] = df_display['Valor ARS'].apply(lambda x: format_currency(x, show_full=True))
    df_display['Valor USD'] = df_display['Valor USD'].apply(lambda x: f"USD {x:,.2f}".replace(",", "."))
    df_display['% Total'] = df_display['% Total'].apply(lambda x: f"{x:.2f}%")
    df_display['Cantidad'] = df_display['Cantidad'].apply(lambda x: f"{x:,.0f}" if x > 0 else "-")

    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # Top 10 activos
    st.markdown("#### 🏆 Top 10 Activos")
    df_top10 = df_show.head(10).copy()

    fig_top = px.bar(
        df_top10,
        x='ticker',
        y='pct_total',
        title='Top 10 Activos por % del Portfolio',
        color='categoria',
        color_discrete_map=CATEGORY_COLORS,
        text=df_top10['pct_total'].apply(lambda x: f"{x:.1f}%")
    )
    fig_top.update_traces(textposition='outside')
    fig_top.update_layout(xaxis_title="Ticker", yaxis_title="% del Total")
    st.plotly_chart(fig_top, use_container_width=True)

    # ==========================================================================
    # ACTIVOS SIN CLASIFICAR
    # ==========================================================================

    otros = df_master[df_master['categoria'] == 'OTROS']
    if len(otros) > 0:
        st.markdown("---")
        st.warning(f"⚠️ {len(otros)} activos sin clasificar")

        df_otros = otros[['ticker', 'descripcion', 'valor']].copy()
        df_otros.columns = ['Ticker', 'Descripción', 'Valor']
        st.dataframe(df_otros, use_container_width=True, hide_index=True)

    # ==========================================================================
    # DESCARGAR CSV
    # ==========================================================================

    st.markdown("---")
    st.header("💾 Exportar")

    col1, col2 = st.columns(2)

    with col1:
        csv = df_master.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Descargar CSV completo",
            data=csv,
            file_name=f"portfolio_{datetime.now():%Y%m%d_%H%M%S}.csv",
            mime="text/csv"
        )

    with col2:
        csv_summary = df_summary.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Descargar Resumen",
            data=csv_summary,
            file_name=f"portfolio_resumen_{datetime.now():%Y%m%d_%H%M%S}.csv",
            mime="text/csv"
        )

    # ==========================================================================
    # RESUMEN DE TODAS LAS CARTERAS (desde Google Sheets)
    # ==========================================================================

    st.markdown("---")
    st.header("📊 Resumen de Todas las Carteras")

    try:
        tracker = PortfolioTracker()
        df_all_portfolios = tracker.get_all_portfolios_summary()

        if not df_all_portfolios.empty:
            # Métricas agregadas
            valor_total_all = df_all_portfolios['valor_total'].sum()
            num_carteras = len(df_all_portfolios)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("💰 Valor Total Consolidado", format_currency(valor_total_all))
            with col2:
                st.metric("📁 Carteras Monitoreadas", num_carteras)
            with col3:
                ultima_actualizacion = df_all_portfolios['fecha'].max()
                st.metric("📅 Última Actualización", ultima_actualizacion)

            # Tabla resumen
            st.markdown("#### Detalle por Cliente")

            df_display_all = df_all_portfolios.copy()
            df_display_all['valor_total'] = df_display_all['valor_total'].astype(float).apply(lambda x: format_currency(x, show_full=True))
            df_display_all['variacion_vs_anterior_pct'] = df_display_all['variacion_vs_anterior_pct'].apply(
                lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A"
            )
            df_display_all.columns = ['Comitente', 'Nombre', 'Valor Total', 'Fecha', 'Var. vs Anterior']

            st.dataframe(df_display_all, use_container_width=True, hide_index=True)

            # Gráfico de distribución
            fig_dist = px.pie(
                df_all_portfolios,
                values='valor_total',
                names='nombre',
                title='Distribución del Patrimonio Total por Cliente',
                hole=0.4
            )
            st.plotly_chart(fig_dist, use_container_width=True)

        else:
            st.info("No hay datos históricos disponibles en Google Sheets. Procesa archivos para comenzar.")

    except Exception as e:
        st.warning(f"No se pudo cargar el resumen de carteras: {e}")


if __name__ == "__main__":
    main()
