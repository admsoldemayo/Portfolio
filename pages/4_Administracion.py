"""
Administración - Gestión de Datos
==================================
Herramientas para limpiar, simular y verificar datos en Google Sheets.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys
from datetime import datetime, timedelta
import random

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import KNOWN_PORTFOLIOS, DEFAULT_PROFILES, CATEGORIES, CATEGORY_COLORS
from sheets_manager import get_sheets_manager
from portfolio_tracker import PortfolioTracker
from asset_mapper import get_all_categories, get_category_display_name

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

st.set_page_config(
    page_title="Administración",
    page_icon="🔧",
    layout="wide"
)

# =============================================================================
# FUNCIONES
# =============================================================================

def clear_all_data():
    """Borra todos los datos de las hojas de Google Sheets."""
    try:
        sheets = get_sheets_manager()

        # Limpiar cada hoja
        sheets.clear_sheet('historial_tenencias')
        sheets.clear_sheet('snapshots_totales')
        sheets.clear_sheet('alocacion_custom')

        return True, "✅ Todos los datos fueron eliminados exitosamente"
    except Exception as e:
        return False, f"❌ Error al borrar datos: {e}"


def generate_mock_data():
    """Genera datos de prueba para testing."""
    try:
        tracker = PortfolioTracker()

        # Generar snapshots para los últimos 30 días
        base_date = datetime.now()
        carteras_generadas = 0

        # Para cada cartera conocida
        for comitente, info in KNOWN_PORTFOLIOS.items():
            nombre = info['nombre']

            # Generar 10 snapshots históricos
            for days_ago in range(30, 0, -3):  # Cada 3 días
                fecha = (base_date - timedelta(days=days_ago)).strftime('%Y-%m-%d')

                # Generar valores aleatorios por categoría
                categoria_data = {}
                valor_base = random.randint(500_000, 2_000_000)

                # Distribuir según perfil
                perfil = info['perfil']
                allocation = DEFAULT_PROFILES.get(perfil, DEFAULT_PROFILES['moderado'])

                for cat, pct in allocation.items():
                    # Agregar variación aleatoria ±20%
                    variacion = random.uniform(0.8, 1.2)
                    valor = (valor_base * pct / 100) * variacion
                    categoria_data[cat] = valor

                # Crear DataFrame de prueba
                df_test = pd.DataFrame([
                    {'categoria': cat, 'ticker': f'MOCK_{cat}', 'valor': val}
                    for cat, val in categoria_data.items()
                ])

                # Guardar snapshot
                tracker.save_snapshot(
                    df=df_test,
                    comitente=comitente,
                    nombre=nombre,
                    fecha=fecha
                )

                carteras_generadas += 1

        return True, f"✅ Datos simulados generados: {carteras_generadas} snapshots para {len(KNOWN_PORTFOLIOS)} carteras"

    except Exception as e:
        return False, f"❌ Error generando datos: {e}"


def verify_sheets_connection():
    """Verifica la conexión con Google Sheets."""
    try:
        sheets = get_sheets_manager()

        # Intentar leer las hojas
        df_carteras = sheets.get_carteras_maestro()
        df_perfiles = sheets.get_perfiles_alocacion()

        info = {
            'Conexión': '✅ Activa',
            'Carteras configuradas': len(df_carteras) if not df_carteras.empty else 0,
            'Perfiles configurados': df_perfiles['perfil'].nunique() if not df_perfiles.empty else 0,
            'Spreadsheet ID': sheets.spreadsheet_id
        }

        return True, info

    except Exception as e:
        return False, {'Error': str(e)}


def get_data_stats():
    """Obtiene estadísticas de los datos almacenados."""
    try:
        sheets = get_sheets_manager()

        df_hist = sheets.get_historial_tenencias()
        df_snaps = sheets.get_snapshots_totales()
        df_custom = sheets.get_alocacion_custom()

        stats = {
            'Registros en historial_tenencias': len(df_hist),
            'Snapshots totales': len(df_snaps),
            'Carteras con datos': df_hist['comitente'].nunique() if not df_hist.empty else 0,
            'Fecha más antigua': df_hist['fecha'].min() if not df_hist.empty else 'N/A',
            'Fecha más reciente': df_hist['fecha'].max() if not df_hist.empty else 'N/A',
            'Overrides custom': len(df_custom)
        }

        return stats

    except Exception as e:
        return {'Error': str(e)}


# =============================================================================
# INTERFAZ PRINCIPAL
# =============================================================================

st.title("🔧 Administración del Sistema")
st.markdown("*Herramientas para gestionar datos en Google Sheets*")

# =============================================================================
# SECCIÓN 1: ESTADO DEL SISTEMA
# =============================================================================

st.markdown("---")
st.header("📊 Estado del Sistema")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Conexión con Google Sheets")

    success, result = verify_sheets_connection()

    if success:
        for key, value in result.items():
            st.metric(key, value)
    else:
        st.error(f"Error de conexión: {result}")

with col2:
    st.subheader("Estadísticas de Datos")

    stats = get_data_stats()

    for key, value in stats.items():
        if key != 'Error':
            st.metric(key, value)
        else:
            st.error(f"Error: {value}")

# =============================================================================
# SECCIÓN 2: OPERACIONES DE DATOS
# =============================================================================

st.markdown("---")
st.header("🛠️ Operaciones de Datos")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🧪 Simular Datos")

    st.markdown("""
    Genera datos de prueba para testing:
    - 10 snapshots por cartera
    - Últimos 30 días
    - Valores aleatorios según perfil
    """)

    if st.button("🎲 Generar Datos de Prueba", type="primary", use_container_width=True):
        with st.spinner("Generando datos simulados..."):
            success, message = generate_mock_data()

            if success:
                st.success(message)
                st.balloons()
            else:
                st.error(message)

with col2:
    st.subheader("🗑️ Borrar Datos")

    st.markdown("""
    **⚠️ PRECAUCIÓN:**
    Esto eliminará TODOS los datos de:
    - Historial de tenencias
    - Snapshots totales
    - Alocaciones custom
    """)

    # Checkbox de confirmación
    confirm_delete = st.checkbox("Confirmo que quiero borrar todos los datos", key="confirm_delete")

    if st.button(
        "🗑️ BORRAR TODOS LOS DATOS",
        type="secondary",
        disabled=not confirm_delete,
        use_container_width=True
    ):
        with st.spinner("Borrando datos..."):
            success, message = clear_all_data()

            if success:
                st.success(message)
                st.info("Refresca la página para ver los cambios")
            else:
                st.error(message)

with col3:
    st.subheader("🔄 Refrescar Datos")

    st.markdown("""
    Recarga las estadísticas y verifica el estado actual del sistema.
    """)

    if st.button("🔄 Refrescar", use_container_width=True):
        st.rerun()

# =============================================================================
# SECCIÓN 3: GESTIÓN DE CATEGORÍAS
# =============================================================================

st.markdown("---")
st.header("📁 Gestión de Categorías")

col_cat1, col_cat2 = st.columns([1, 2])

with col_cat1:
    st.subheader("➕ Nueva Categoría")

    with st.form("nueva_categoria"):
        cat_nombre = st.text_input(
            "Nombre interno",
            placeholder="BONOS_CORPORATIVOS",
            help="Usar MAYÚSCULAS con guiones bajos"
        )
        cat_display = st.text_input(
            "Nombre para mostrar",
            placeholder="Bonos Corporativos"
        )
        cat_color = st.color_picker("Color", "#808080")
        cat_exposicion = st.selectbox(
            "Exposición",
            ["ARGENTINA", "EXTERIOR"],
            help="Clasificación por exposición geográfica"
        )

        submitted = st.form_submit_button("Crear Categoría", use_container_width=True)

        if submitted and cat_nombre:
            try:
                sheets = get_sheets_manager()
                success = sheets.save_custom_category(
                    cat_nombre.upper().strip().replace(" ", "_"),
                    cat_display or cat_nombre.replace("_", " ").title(),
                    cat_color,
                    cat_exposicion
                )
                if success:
                    st.success(f"✅ Categoría '{cat_nombre}' creada")
                    st.rerun()
                else:
                    st.error("Error al crear categoría")
            except Exception as e:
                st.error(f"Error: {e}")

with col_cat2:
    st.subheader("📋 Categorías Existentes")

    # Mostrar categorías base
    st.markdown("**Categorías del Sistema:**")

    base_cats = []
    for cat in CATEGORIES:
        color = CATEGORY_COLORS.get(cat, "#808080")
        display = get_category_display_name(cat)
        base_cats.append({
            "Nombre": cat,
            "Display": display,
            "Color": color,
            "Tipo": "Base"
        })

    df_cats = pd.DataFrame(base_cats)

    # Agregar categorías custom
    try:
        sheets = get_sheets_manager()
        custom_cats = sheets.get_custom_categories_full()

        for cat in custom_cats:
            df_cats = pd.concat([df_cats, pd.DataFrame([{
                "Nombre": cat.get('nombre'),
                "Display": cat.get('display_name'),
                "Color": cat.get('color'),
                "Tipo": f"Custom ({cat.get('exposicion', 'N/A')})"
            }])], ignore_index=True)
    except Exception:
        pass

    st.dataframe(df_cats, use_container_width=True, hide_index=True)

# =============================================================================
# SECCIÓN 4: CARGA DE ARCHIVOS
# =============================================================================

st.markdown("---")
st.header("📤 Carga de Archivos de Tenencias")

uploaded_files = st.file_uploader(
    "Arrastrá archivos Excel de tenencias aquí",
    type=['xlsx', 'xls'],
    accept_multiple_files=True,
    help="Formato: Tenencias-{comitente}_{NOMBRE}-{YYYY-MM-DD}.xlsx"
)

if uploaded_files:
    st.info(f"📁 {len(uploaded_files)} archivo(s) cargado(s)")

    # Importar el procesador
    try:
        from ingest import process_excel_file, save_to_sheets

        if st.button("🚀 Procesar Archivos", type="primary", use_container_width=True):
            with st.spinner("Procesando archivos..."):
                results = []

                for file in uploaded_files:
                    try:
                        # Guardar temporalmente
                        temp_path = Path(f".tmp/{file.name}")
                        temp_path.parent.mkdir(exist_ok=True)
                        temp_path.write_bytes(file.getvalue())

                        # Procesar
                        result = process_excel_file(str(temp_path))

                        if result:
                            comitente = result.get('comitente')
                            activos = result.get('activos', [])
                            results.append({
                                'archivo': file.name,
                                'comitente': comitente,
                                'activos': len(activos),
                                'status': '✅'
                            })
                        else:
                            results.append({
                                'archivo': file.name,
                                'comitente': 'N/A',
                                'activos': 0,
                                'status': '❌ Error'
                            })

                        # Limpiar temporal
                        temp_path.unlink(missing_ok=True)

                    except Exception as e:
                        results.append({
                            'archivo': file.name,
                            'comitente': 'N/A',
                            'activos': 0,
                            'status': f'❌ {str(e)[:30]}'
                        })

                # Guardar en sheets
                if results:
                    try:
                        save_to_sheets()
                        st.success("✅ Datos guardados en Google Sheets")
                    except Exception as e:
                        st.warning(f"⚠️ Procesado pero error al guardar: {e}")

                # Mostrar resultados
                df_results = pd.DataFrame(results)
                st.dataframe(df_results, use_container_width=True, hide_index=True)

    except ImportError as e:
        st.error(f"Error importando módulo: {e}")

# =============================================================================
# SECCIÓN 5: VERIFICACIÓN DE GUARDADO
# =============================================================================

st.markdown("---")
st.header("✅ Verificación de Guardado desde Excel")

st.markdown("""
### Cómo funciona el guardado automático:

1. **Subes un archivo Excel** en la página principal
2. El sistema **extrae metadata** del nombre del archivo:
   - Comitente (ej: 34491)
   - Nombre del cliente (ej: LOPEZ JUAN ANTONIO)
   - Fecha (ej: 2026-01-10)

3. **Clasifica los activos** en 11 categorías

4. **Guarda automáticamente en Google Sheets** (si el checkbox está activado):
   - `historial_tenencias`: Detalle por categoría y ticker
   - `snapshots_totales`: Valor total y variación vs anterior

### Para verificar que se guardó:

1. Sube un archivo Excel en la página principal
2. Espera el mensaje "✅ Snapshots guardados: X carteras"
3. Ve a la página **Portfolio Individual** o **Historial**
4. Selecciona el cliente correspondiente
5. Verifica que aparezcan los datos

### Formato de nombre de archivo requerido:

```
Tenencias-{comitente}_{NOMBRE}-{YYYY-MM-DD}.xlsx
```

**Ejemplo:**
```
Tenencias-34491_LOPEZ_JUAN ANTONIO-2026-01-10.xlsx
```
""")

# Mostrar últimos registros guardados
st.markdown("---")
st.subheader("📋 Últimos Registros Guardados")

try:
    sheets = get_sheets_manager()
    df_snaps = sheets.get_snapshots_totales()

    if not df_snaps.empty:
        # Ordenar por fecha descendente
        df_snaps = df_snaps.sort_values('fecha', ascending=False)

        # Mostrar últimos 10
        df_display = df_snaps.head(10)[['fecha', 'comitente', 'nombre', 'valor_total', 'variacion_vs_anterior_pct']]

        # Formatear
        df_display['valor_total'] = df_display['valor_total'].apply(lambda x: f"${x:,.0f}".replace(",", "."))
        df_display['variacion_vs_anterior_pct'] = df_display['variacion_vs_anterior_pct'].apply(
            lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A"
        )

        df_display.columns = ['Fecha', 'Comitente', 'Nombre', 'Valor Total', 'Variación']

        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("No hay registros guardados todavía. Sube un archivo Excel en la página principal.")

except Exception as e:
    st.error(f"Error cargando registros: {e}")

# =============================================================================
# SECCIÓN 4: HERRAMIENTAS DE DEBUG
# =============================================================================

st.markdown("---")
st.header("🐛 Herramientas de Debug")

with st.expander("Ver contenido de Google Sheets (raw)"):
    try:
        sheets = get_sheets_manager()

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "carteras_maestro",
            "perfiles_alocacion",
            "alocacion_custom",
            "historial_tenencias (últimos 50)",
            "snapshots_totales"
        ])

        with tab1:
            df = sheets.get_carteras_maestro()
            if not df.empty:
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Hoja vacía")

        with tab2:
            df = sheets.get_perfiles_alocacion()
            if not df.empty:
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Hoja vacía")

        with tab3:
            df = sheets.get_alocacion_custom()
            if not df.empty:
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Hoja vacía")

        with tab4:
            df = sheets.get_historial_tenencias()
            if not df.empty:
                st.dataframe(df.tail(50), use_container_width=True)
            else:
                st.info("Hoja vacía")

        with tab5:
            df = sheets.get_snapshots_totales()
            if not df.empty:
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Hoja vacía")

    except Exception as e:
        st.error(f"Error cargando datos: {e}")

# =============================================================================
# FOOTER
# =============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
🔧 Panel de Administración - Portfolio Automation System v1.0<br>
Usa estas herramientas con precaución
</div>
""", unsafe_allow_html=True)
