"""
Portfolio Tracker - Historial y cálculo de rentabilidad
========================================================
Gestiona snapshots históricos y calcula métricas de performance.
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from sheets_manager import get_sheets_manager
import logging

logger = logging.getLogger(__name__)


class PortfolioTracker:
    """Gestiona historial de carteras y cálculo de rentabilidad."""

    def __init__(self):
        self.sheets_manager = get_sheets_manager()

    def save_snapshot(
        self,
        df: pd.DataFrame,
        comitente: str,
        nombre: str,
        fecha: Optional[str] = None
    ) -> Dict:
        """
        Guarda snapshot de cartera en Google Sheets.

        Args:
            df: DataFrame con columnas 'categoria', 'ticker', 'valor'
            comitente: Número de comitente
            nombre: Nombre del cliente
            fecha: Fecha en formato YYYY-MM-DD (default: hoy)

        Returns:
            Dict con resultado del guardado y variación vs anterior
        """
        if fecha is None:
            fecha = datetime.now().strftime('%Y-%m-%d')

        # Calcular totales por categoría
        valor_total = df['valor'].sum()

        # Crear lista de dicts en el formato esperado por sheets_manager
        categoria_totales = df.groupby('categoria')['valor'].sum()
        categoria_data = []
        for cat, valor in categoria_totales.items():
            pct = (valor / valor_total * 100) if valor_total > 0 else 0
            categoria_data.append({
                'categoria': cat,
                'valor': valor,
                'pct': round(pct, 2)
            })

        # Guardar en Sheets (esto ya calcula variación internamente)
        self.sheets_manager.save_snapshot(
            fecha=fecha,
            comitente=comitente,
            nombre=nombre,
            categoria_data=categoria_data,
            valor_total=valor_total
        )

        logger.info(
            f"Snapshot guardado: {comitente} ({nombre}) - "
            f"${valor_total:,.0f} - {fecha}"
        )

        # Obtener variación vs snapshot anterior
        last_snap = self.sheets_manager.get_last_snapshot(comitente)
        variacion_pct = None
        if last_snap:
            prev_valor = float(last_snap.get('valor_total', 0))
            if prev_valor > 0:
                variacion_pct = ((valor_total - prev_valor) / prev_valor) * 100

        return {
            'fecha': fecha,
            'comitente': comitente,
            'nombre': nombre,
            'valor_total': valor_total,
            'categorias': len(categoria_data),
            'variacion_pct': variacion_pct
        }

    def get_portfolio_history(
        self,
        comitente: str,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Obtiene historial de snapshots de una cartera.

        Args:
            comitente: Número de comitente
            limit: Máximo número de registros (None = todos)

        Returns:
            DataFrame con columnas:
            - fecha, comitente, nombre, categoria, valor, valor_total_cartera
            Ordenado por fecha descendente
        """
        df_hist = self.sheets_manager.get_historial_tenencias()

        if df_hist.empty:
            return pd.DataFrame()

        # Convertir fecha - detectar formato (string ISO o número serial Excel)
        sample_fecha = df_hist['fecha'].iloc[0] if len(df_hist) > 0 else None
        if sample_fecha is not None:
            if isinstance(sample_fecha, str) and len(sample_fecha) == 10 and '-' in sample_fecha:
                df_hist['fecha'] = df_hist['fecha'].astype(str)
            else:
                df_hist['fecha'] = pd.to_numeric(df_hist['fecha'], errors='coerce')
                df_hist['fecha'] = pd.to_datetime(df_hist['fecha'], origin='1899-12-30', unit='D', errors='coerce')
                df_hist['fecha'] = df_hist['fecha'].dt.strftime('%Y-%m-%d')

        # Convertir valores numéricos
        df_hist['valor'] = pd.to_numeric(df_hist['valor'], errors='coerce')
        df_hist['valor_total_cartera'] = pd.to_numeric(df_hist['valor_total_cartera'], errors='coerce')

        # Convertir comitente a string para comparación consistente
        df_hist['comitente'] = df_hist['comitente'].astype(str).str.strip()
        comitente_str = str(comitente).strip()

        # Filtrar por comitente
        df_filtered = df_hist[df_hist['comitente'] == comitente_str].copy()

        # Ordenar por fecha descendente
        df_filtered = df_filtered.sort_values('fecha', ascending=False)

        if limit:
            df_filtered = df_filtered.head(limit)

        return df_filtered

    def get_latest_snapshot(self, comitente: str) -> Optional[Dict]:
        """
        Obtiene el último snapshot de una cartera.

        Returns:
            Dict con {'fecha', 'valor_total', 'por_categoria': {cat: valor}}
            o None si no hay historial
        """
        df_hist = self.get_portfolio_history(comitente, limit=1)

        if df_hist.empty:
            return None

        fecha = df_hist.iloc[0]['fecha']
        valor_total = df_hist.iloc[0]['valor_total_cartera']

        # Agrupar por categoría para ese snapshot
        df_snap = df_hist[df_hist['fecha'] == fecha]
        por_categoria = df_snap.groupby('categoria')['valor'].sum().to_dict()

        return {
            'fecha': fecha,
            'valor_total': valor_total,
            'por_categoria': por_categoria
        }

    def calculate_returns(
        self,
        comitente: str,
        fecha_inicio: Optional[str] = None,
        fecha_fin: Optional[str] = None
    ) -> Dict:
        """
        Calcula rentabilidad de una cartera entre dos fechas.

        Args:
            comitente: Número de comitente
            fecha_inicio: Fecha inicial (default: primer snapshot)
            fecha_fin: Fecha final (default: último snapshot)

        Returns:
            Dict con:
            - total_return_pct: Rentabilidad total (%)
            - total_return_abs: Ganancia/pérdida absoluta ($)
            - by_category: Dict {categoria: {'return_pct', 'return_abs'}}
            - fecha_inicio, fecha_fin
            - valor_inicio, valor_fin
        """
        df_hist = self.get_portfolio_history(comitente)

        if df_hist.empty or len(df_hist['fecha'].unique()) < 2:
            return {
                'error': 'No hay suficientes snapshots para calcular rentabilidad'
            }

        # Determinar fechas
        if fecha_fin is None:
            fecha_fin = df_hist['fecha'].max()
        if fecha_inicio is None:
            fecha_inicio = df_hist['fecha'].min()

        # Filtrar por rango
        df_inicio = df_hist[df_hist['fecha'] == fecha_inicio]
        df_fin = df_hist[df_hist['fecha'] == fecha_fin]

        if df_inicio.empty or df_fin.empty:
            return {
                'error': f'No hay datos para las fechas {fecha_inicio} / {fecha_fin}'
            }

        # Calcular totales
        valor_inicio = df_inicio.iloc[0]['valor_total_cartera']
        valor_fin = df_fin.iloc[0]['valor_total_cartera']

        total_return_abs = valor_fin - valor_inicio
        total_return_pct = (total_return_abs / valor_inicio * 100) if valor_inicio > 0 else 0

        # Calcular por categoría
        cat_inicio = df_inicio.groupby('categoria')['valor'].sum().to_dict()
        cat_fin = df_fin.groupby('categoria')['valor'].sum().to_dict()

        by_category = {}
        all_cats = set(cat_inicio.keys()) | set(cat_fin.keys())

        for cat in all_cats:
            val_inicio = cat_inicio.get(cat, 0)
            val_fin = cat_fin.get(cat, 0)

            ret_abs = val_fin - val_inicio
            ret_pct = (ret_abs / val_inicio * 100) if val_inicio > 0 else 0

            by_category[cat] = {
                'valor_inicio': val_inicio,
                'valor_fin': val_fin,
                'return_abs': ret_abs,
                'return_pct': ret_pct
            }

        return {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'valor_inicio': valor_inicio,
            'valor_fin': valor_fin,
            'total_return_abs': total_return_abs,
            'total_return_pct': total_return_pct,
            'by_category': by_category
        }

    def get_evolution_series(
        self,
        comitente: str,
        periodo: str = 'all'
    ) -> pd.DataFrame:
        """
        Obtiene serie temporal de evolución de valor total.

        Args:
            comitente: Número de comitente
            periodo: 'all', 'ytd', 'mtd', '1m', '3m', '6m', '1y'

        Returns:
            DataFrame con columnas 'fecha', 'valor_total'
            Ordenado por fecha ascendente
        """
        df_snapshots = self.sheets_manager.get_snapshots_totales()

        if df_snapshots.empty:
            return pd.DataFrame()

        # Convertir fecha - detectar formato (string ISO o número serial Excel)
        sample_fecha = df_snapshots['fecha'].iloc[0] if len(df_snapshots) > 0 else None
        if sample_fecha is not None:
            if isinstance(sample_fecha, str) and len(sample_fecha) == 10 and '-' in sample_fecha:
                df_snapshots['fecha'] = pd.to_datetime(df_snapshots['fecha'], format='%Y-%m-%d', errors='coerce')
            else:
                df_snapshots['fecha'] = pd.to_numeric(df_snapshots['fecha'], errors='coerce')
                df_snapshots['fecha'] = pd.to_datetime(df_snapshots['fecha'], origin='1899-12-30', unit='D', errors='coerce')

        # Convertir valor_total a numérico
        df_snapshots['valor_total'] = pd.to_numeric(df_snapshots['valor_total'], errors='coerce')

        # Convertir comitente a string para comparación consistente
        df_snapshots['comitente'] = df_snapshots['comitente'].astype(str).str.strip()
        comitente_str = str(comitente).strip()

        # Filtrar por comitente
        df_filtered = df_snapshots[df_snapshots['comitente'] == comitente_str].copy()

        if df_filtered.empty:
            return pd.DataFrame()

        # Aplicar filtro de periodo
        if periodo != 'all' and not df_filtered.empty:
            fecha_max = df_filtered['fecha'].max()

            if periodo == 'ytd':
                fecha_inicio = pd.Timestamp(year=fecha_max.year, month=1, day=1)
            elif periodo == 'mtd':
                fecha_inicio = pd.Timestamp(year=fecha_max.year, month=fecha_max.month, day=1)
            elif periodo == '1m':
                fecha_inicio = fecha_max - pd.DateOffset(months=1)
            elif periodo == '3m':
                fecha_inicio = fecha_max - pd.DateOffset(months=3)
            elif periodo == '6m':
                fecha_inicio = fecha_max - pd.DateOffset(months=6)
            elif periodo == '1y':
                fecha_inicio = fecha_max - pd.DateOffset(years=1)
            else:
                fecha_inicio = df_filtered['fecha'].min()

            df_filtered = df_filtered[df_filtered['fecha'] >= fecha_inicio]

        # Ordenar por fecha ascendente
        df_filtered = df_filtered.sort_values('fecha')

        return df_filtered[['fecha', 'valor_total']]

    def get_all_portfolios_summary(self) -> pd.DataFrame:
        """
        Obtiene resumen de todas las carteras (último snapshot de cada una).

        Returns:
            DataFrame con columnas:
            - comitente, nombre, valor_total, fecha, variacion_pct
            Ordenado por valor_total descendente
        """
        df_snapshots = self.sheets_manager.get_snapshots_totales()

        if df_snapshots.empty:
            return pd.DataFrame()

        # Convertir fecha - detectar formato (string ISO o número serial Excel)
        sample_fecha = df_snapshots['fecha'].iloc[0] if len(df_snapshots) > 0 else None
        if sample_fecha is not None:
            if isinstance(sample_fecha, str) and len(sample_fecha) == 10 and '-' in sample_fecha:
                df_snapshots['fecha'] = df_snapshots['fecha'].astype(str)
            else:
                df_snapshots['fecha'] = pd.to_numeric(df_snapshots['fecha'], errors='coerce')
                df_snapshots['fecha'] = pd.to_datetime(df_snapshots['fecha'], origin='1899-12-30', unit='D', errors='coerce')
                df_snapshots['fecha'] = df_snapshots['fecha'].dt.strftime('%Y-%m-%d')

        # Convertir valor_total a numérico
        df_snapshots['valor_total'] = pd.to_numeric(df_snapshots['valor_total'], errors='coerce')

        # Obtener último snapshot de cada cartera
        df_latest = df_snapshots.sort_values('fecha').groupby('comitente').last().reset_index()

        # Ordenar por valor total descendente
        df_latest = df_latest.sort_values('valor_total', ascending=False)

        # Renombrar columna para compatibilidad
        if 'variacion_pct' in df_latest.columns:
            df_latest = df_latest.rename(columns={'variacion_pct': 'variacion_vs_anterior_pct'})
        else:
            df_latest['variacion_vs_anterior_pct'] = None

        return df_latest[[
            'comitente',
            'nombre',
            'valor_total',
            'fecha',
            'variacion_vs_anterior_pct'
        ]]


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Crear datos de prueba
    test_data = {
        'categoria': ['SPY', 'SPY', 'MERV', 'LETRAS', 'GLD', 'LIQUIDEZ'],
        'ticker': ['SPY', 'QQQ', 'YPFD', 'AL30', 'GLD', 'USD'],
        'valor': [300000, 200000, 150000, 100000, 80000, 50000]
    }
    df_test = pd.DataFrame(test_data)

    tracker = PortfolioTracker()

    print("=" * 70)
    print("TEST DE PORTFOLIO TRACKER - Comitente 34491")
    print("=" * 70)
    print()

    # Test 1: Guardar snapshot
    print("1. Guardando snapshot...")
    result = tracker.save_snapshot(
        df=df_test,
        comitente='34491',
        nombre='LOPEZ JUAN ANTONIO',
        fecha='2026-01-12'
    )
    print(f"   Resultado: {result}")
    print()

    # Test 2: Obtener último snapshot
    print("2. Obteniendo último snapshot...")
    latest = tracker.get_latest_snapshot('34491')
    if latest:
        print(f"   Fecha: {latest['fecha']}")
        print(f"   Valor Total: ${latest['valor_total']:,.0f}")
        print(f"   Por Categoría:")
        for cat, val in sorted(latest['por_categoria'].items(), key=lambda x: -x[1]):
            print(f"     {cat:15} ${val:>12,.0f}")
    else:
        print("   No hay snapshots previos")
    print()

    # Test 3: Obtener historial
    print("3. Obteniendo historial (últimos 5 registros)...")
    df_hist = tracker.get_portfolio_history('34491', limit=5)
    if not df_hist.empty:
        print(df_hist[['fecha', 'categoria', 'valor', 'valor_total_cartera']].to_string(index=False))
    else:
        print("   No hay historial")
    print()

    # Test 4: Calcular rentabilidad
    print("4. Calculando rentabilidad...")
    returns = tracker.calculate_returns('34491')
    if 'error' not in returns:
        print(f"   Periodo: {returns['fecha_inicio']} a {returns['fecha_fin']}")
        print(f"   Valor Inicial: ${returns['valor_inicio']:,.0f}")
        print(f"   Valor Final: ${returns['valor_fin']:,.0f}")
        print(f"   Rentabilidad: {returns['total_return_pct']:+.2f}% (${returns['total_return_abs']:+,.0f})")
        print()
        print(f"   Por Categoría:")
        for cat, data in sorted(returns['by_category'].items(), key=lambda x: -x[1]['return_abs']):
            print(f"     {cat:15} {data['return_pct']:+7.2f}%  ${data['return_abs']:+12,.0f}")
    else:
        print(f"   {returns['error']}")
    print()

    # Test 5: Resumen de todas las carteras
    print("5. Resumen de todas las carteras...")
    df_summary = tracker.get_all_portfolios_summary()
    if not df_summary.empty:
        print(df_summary.to_string(index=False))
    else:
        print("   No hay datos")

    print()
    print("=" * 70)
