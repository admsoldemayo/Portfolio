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
import gc  # Para liberar memoria

from auth import require_auth

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
from filename_parser import parse_filename

# Paths
PROJECT_ROOT = Path(__file__).parent
INPUT_DIR = PROJECT_ROOT / "data" / "input"

# =============================================================================
# CONFIGURACIÓN DE LA PÁGINA
# =============================================================================

st.set_page_config(
    page_title="Portfolio Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Auth gate
require_auth()

# Logout button in sidebar
with st.sidebar:
    if st.button("Cerrar sesion"):
        st.logout()

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


def get_input_files():
    """Obtiene lista de archivos Excel en data/input/"""
    if not INPUT_DIR.exists():
        return []
    files = list(INPUT_DIR.glob("*.xlsx")) + list(INPUT_DIR.glob("*.xls"))
    return sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)


def get_input_files_with_metadata():
    """Obtiene archivos con su metadata parseada (comitente, fecha, nombre)"""
    files = get_input_files()
    result = []
    for f in files:
        meta = parse_filename(str(f))
        result.append({
            'path': f,
            'filename': f.name,
            'comitente': meta.get('comitente'),
            'nombre': meta.get('nombre'),
            'fecha': meta.get('fecha'),
            'mod_time': datetime.fromtimestamp(f.stat().st_mtime)
        })
    return result


def get_comitente_display_name(comitente: str) -> str:
    """Obtiene nombre legible del comitente"""
    if comitente in KNOWN_PORTFOLIOS:
        return f"{comitente} - {KNOWN_PORTFOLIOS[comitente].get('nombre', '')}"
    return comitente


def process_local_file(file_path: Path) -> pd.DataFrame:
    """Procesa un archivo local y retorna DataFrame clasificado."""
    try:
        broker_format = detect_broker_format(str(file_path))

        if broker_format == "iol_stonex":
            df = parse_iol_stonex_format(str(file_path))
        else:
            df_raw = read_excel_safe(str(file_path))
            df = standardize_dataframe(df_raw, file_path.name)

        if df.empty:
            return pd.DataFrame()

        # Extraer metadata del nombre del archivo
        meta = parse_filename(str(file_path))
        comitente = meta.get('comitente')
        nombre_cliente = meta.get('nombre', '')
        fecha_archivo = meta.get('fecha')

        # Si no hay fecha en el nombre, usar fecha de modificación del archivo
        if not fecha_archivo:
            fecha_archivo = datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d')

        # Agregar columnas requeridas para save_to_sheets
        df['comitente'] = comitente
        df['nombre_cliente'] = nombre_cliente
        df['fecha_archivo'] = fecha_archivo

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

        df['fuente'] = file_path.name
        df['fecha_proceso'] = datetime.now().isoformat()

        return df
    except Exception as e:
        st.error(f"Error procesando {file_path.name}: {e}")
        return pd.DataFrame()


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

    # =========================================================================
    # SECCIÓN PRINCIPAL - Subir y Procesar Archivos
    # =========================================================================
    st.markdown("---")
    st.subheader("🚀 Actualizar Carteras")

    # Drag & Drop prominente para subir archivos nuevos
    uploaded_new_files = st.file_uploader(
        "📂 Arrastrá archivos nuevos aquí",
        type=['xlsx', 'xls'],
        accept_multiple_files=True,
        key="main_uploader",
        help="Los archivos se guardan en data/input/ y se procesan automáticamente"
    )

    # Si hay archivos nuevos subidos, guardarlos y procesarlos
    if uploaded_new_files:
        st.markdown("---")
        st.info(f"📥 **{len(uploaded_new_files)} archivos nuevos** listos para procesar")

        col_save, col_preview = st.columns([1, 2])

        with col_preview:
            with st.expander("Ver archivos subidos", expanded=True):
                for uf in uploaded_new_files:
                    meta = parse_filename(uf.name)
                    nombre = meta.get('nombre') or meta.get('comitente') or 'Desconocido'
                    fecha = meta.get('fecha') or 'Sin fecha'
                    st.caption(f"• **{nombre}** ({fecha}) - {uf.name}")

        with col_save:
            procesar_nuevos = st.button(
                "⚡ GUARDAR Y PROCESAR",
                type="primary",
                use_container_width=True,
                help="Guarda los archivos en data/input/ y actualiza Google Sheets"
            )

        if procesar_nuevos:
            st.markdown("---")

            # 1. Guardar archivos en data/input/
            st.subheader("💾 Guardando archivos...")
            INPUT_DIR.mkdir(parents=True, exist_ok=True)

            saved_files = []
            for uf in uploaded_new_files:
                file_path = INPUT_DIR / uf.name
                with open(file_path, 'wb') as f:
                    f.write(uf.getvalue())
                saved_files.append(file_path)
                st.caption(f"✅ {uf.name}")

            st.success(f"📁 {len(saved_files)} archivos guardados en data/input/")

            # 2. Procesar y guardar archivos UNO POR UNO (para no exceder memoria)
            st.subheader("⚙️ Procesando y guardando...")
            progress = st.progress(0)
            status_text = st.empty()
            results_container = st.container()

            all_results = {}
            exitos = 0
            errores = 0

            for i, file_path in enumerate(saved_files):
                meta = parse_filename(str(file_path))
                nombre_display = meta.get('nombre') or meta.get('comitente') or file_path.name
                status_text.text(f"Procesando: {nombre_display}...")

                try:
                    # Procesar archivo
                    df = process_local_file(file_path)

                    if not df.empty:
                        # Guardar inmediatamente en Sheets (no acumular en memoria)
                        result = save_to_sheets(df, auto_save=True)
                        all_results.update(result)

                        # Contar éxitos/errores
                        for comitente, res in result.items():
                            if 'error' not in res:
                                exitos += 1
                                with results_container:
                                    st.caption(f"✅ {nombre_display}")
                            else:
                                errores += 1
                                with results_container:
                                    st.caption(f"❌ {nombre_display}: {res['error']}")

                        # Liberar memoria inmediatamente
                        del df
                        del result

                except Exception as e:
                    errores += 1
                    with results_container:
                        st.caption(f"❌ {nombre_display}: {str(e)}")

                # Forzar liberación de memoria después de cada archivo
                gc.collect()
                progress.progress((i + 1) / len(saved_files))

            progress.empty()
            status_text.empty()

            # Resumen final
            st.markdown("---")
            if exitos > 0:
                st.success(f"✅ **{exitos} carteras actualizadas exitosamente**")
            if errores > 0:
                st.warning(f"⚠️ {errores} archivos con errores")

            sheets_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
            st.markdown(f"📊 [**Ver en Google Sheets**]({sheets_url})")

            if exitos > 0:
                st.balloons()

            if st.button("🔄 Recargar para ver datos actualizados"):
                st.rerun()

            return  # Terminar después de procesar nuevos

    # =========================================================================
    # Archivos existentes en data/input/
    # =========================================================================
    files_with_meta = get_input_files_with_metadata()

    if files_with_meta:
        st.markdown("---")
        st.markdown("#### 📁 Archivos en data/input/")

        # Extraer fechas y comitentes únicos
        fechas_disponibles = sorted(set(f['fecha'] for f in files_with_meta if f['fecha']), reverse=True)
        comitentes_disponibles = sorted(set(f['comitente'] for f in files_with_meta if f['comitente']))

        # Selectores en columnas
        col_fecha, col_comitentes = st.columns(2)

        with col_fecha:
            # Selector de fecha
            if fechas_disponibles:
                fecha_default = fechas_disponibles[0] if fechas_disponibles else None
                fecha_seleccionada = st.selectbox(
                    "📅 Fecha de archivos",
                    options=["Todas las fechas"] + fechas_disponibles,
                    index=1 if fecha_default else 0,
                    help="Filtra archivos por fecha del nombre del archivo"
                )
            else:
                fecha_seleccionada = "Todas las fechas"
                st.warning("No se detectaron fechas en los nombres de archivos")

        with col_comitentes:
            # Selector de comitentes
            if comitentes_disponibles:
                comitentes_options = [get_comitente_display_name(c) for c in comitentes_disponibles]
                comitentes_seleccionados = st.multiselect(
                    "👥 Comitentes a procesar",
                    options=comitentes_options,
                    default=comitentes_options,
                    help="Selecciona qué comitentes actualizar"
                )
                # Convertir display names de vuelta a comitentes
                comitentes_ids = [c.split(" - ")[0] for c in comitentes_seleccionados]
            else:
                comitentes_ids = []
                st.warning("No se detectaron comitentes en los nombres de archivos")

        # Filtrar archivos según selección
        archivos_filtrados = []
        for f in files_with_meta:
            # Filtro de fecha
            if fecha_seleccionada != "Todas las fechas":
                if f['fecha'] != fecha_seleccionada:
                    continue
            # Filtro de comitentes
            if comitentes_ids and f['comitente'] not in comitentes_ids:
                continue
            archivos_filtrados.append(f)

        # Mostrar archivos que se van a procesar
        st.markdown("---")
        col_btn, col_info = st.columns([1, 2])

        with col_btn:
            procesar_clicked = st.button(
                f"🚀 PROCESAR ({len(archivos_filtrados)})",
                type="primary",
                use_container_width=True,
                disabled=len(archivos_filtrados) == 0,
                help="Procesa los archivos seleccionados y guarda en Google Sheets"
            )

        with col_info:
            if archivos_filtrados:
                fecha_txt = fecha_seleccionada if fecha_seleccionada != "Todas las fechas" else "todas"
                st.success(f"📁 **{len(archivos_filtrados)} archivos** seleccionados (fecha: {fecha_txt})")
                with st.expander("Ver archivos a procesar"):
                    for f in archivos_filtrados:
                        nombre_display = f['nombre'] or f['comitente'] or 'Desconocido'
                        st.caption(f"• {nombre_display} ({f['fecha']}) - {f['filename']}")
            else:
                st.warning("No hay archivos que coincidan con los filtros")

        # Procesar si se clickeó el botón
        if procesar_clicked and archivos_filtrados:
            st.markdown("---")
            st.subheader("⚙️ Procesando y guardando (uno por uno para ahorrar memoria)...")

            progress_bar = st.progress(0)
            status_text = st.empty()
            results_container = st.container()

            all_results = {}
            exitos = 0
            errores = 0

            for i, file_info in enumerate(archivos_filtrados):
                file_path = file_info['path']
                nombre_display = file_info['nombre'] or file_info['comitente'] or 'Desconocido'
                status_text.text(f"Procesando: {nombre_display} ({file_info['fecha']})")

                try:
                    # Procesar archivo
                    df = process_local_file(file_path)

                    if not df.empty:
                        # Guardar inmediatamente (no acumular en memoria)
                        result = save_to_sheets(df, auto_save=True)
                        all_results.update(result)

                        # Contar resultados
                        for comitente, res in result.items():
                            if 'error' not in res:
                                exitos += 1
                                var = res.get('variacion_pct', 'N/A')
                                with results_container:
                                    st.caption(f"✅ {nombre_display}: {var}")
                            else:
                                errores += 1
                                with results_container:
                                    st.caption(f"❌ {nombre_display}: {res['error']}")

                        # Liberar memoria
                        del df
                        del result
                    else:
                        errores += 1
                        with results_container:
                            st.caption(f"⚠️ {nombre_display}: archivo vacío")

                except Exception as e:
                    errores += 1
                    with results_container:
                        st.caption(f"❌ {nombre_display}: {str(e)}")

                # Forzar liberación de memoria
                gc.collect()
                progress_bar.progress((i + 1) / len(archivos_filtrados))

            status_text.empty()
            progress_bar.empty()

            # Resumen final
            st.markdown("---")
            if exitos > 0:
                st.success(f"✅ **{exitos} carteras actualizadas correctamente**")
            if errores > 0:
                st.warning(f"⚠️ {errores} archivos con errores o vacíos")

            # Link a Google Sheets
            sheets_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}"
            st.markdown(f"📊 [**Ver en Google Sheets**]({sheets_url})")

            if exitos > 0:
                st.balloons()

            # Botón para recargar
            if st.button("🔄 Recargar página"):
                st.rerun()

            return  # Terminar aquí después de procesar

    # Navegación rápida
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("**📁 Portfolio Individual**\nAnaliza carteras por cliente con comparación vs objetivo")
    with col2:
        st.info("**📈 Historial**\nVisualiza evolución temporal y rentabilidad")
    with col3:
        st.info("**⚙️ Configuración**\nEdita perfiles de alocación y overrides")

    # Sidebar - Info y categorías
    with st.sidebar:
        st.markdown("### 📊 Categorías de Activos")
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
            st.info("No hay datos cargados. Arrastrá archivos Excel arriba para comenzar.")

    except Exception as e:
        st.warning(f"No se pudieron cargar los datos: {e}")
        st.exception(e)


if __name__ == "__main__":
    main()
