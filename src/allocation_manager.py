"""
Allocation Manager - Comparación de alocaciones objetivo vs actual
===================================================================
Calcula desviaciones y genera sugerencias de rebalanceo.
"""

import pandas as pd
from typing import Dict, List, Tuple
from sheets_manager import get_sheets_manager


class AllocationManager:
    """Gestiona comparación de alocaciones objetivo vs actual."""

    def __init__(self):
        self.sheets_manager = get_sheets_manager()

    def get_target_allocation(self, comitente: str) -> Dict[str, float]:
        """
        Obtiene la alocación objetivo para un cliente.
        Combina perfil base + overrides custom.
        """
        return self.sheets_manager.get_target_allocation(comitente)

    def calculate_current_allocation(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Calcula la alocación actual (% por categoría).

        Args:
            df: DataFrame con columnas 'categoria' y 'valor'

        Returns:
            Dict con categoria -> % del total
        """
        if df.empty:
            return {}

        total = df['valor'].sum()
        if total == 0:
            return {}

        allocation = {}
        for cat in df['categoria'].unique():
            cat_valor = df[df['categoria'] == cat]['valor'].sum()
            allocation[cat] = (cat_valor / total) * 100

        return allocation

    def compare_allocations(
        self,
        current: Dict[str, float],
        target: Dict[str, float]
    ) -> pd.DataFrame:
        """
        Compara alocación actual vs objetivo.

        Returns:
            DataFrame con columnas:
            - categoria
            - actual_pct
            - objetivo_pct
            - desviacion (puntos porcentuales)
            - desviacion_relativa (%)
            - status (OK / SOBRE / BAJO)
        """
        # Obtener todas las categorías (union de ambos)
        all_categories = set(current.keys()) | set(target.keys())

        rows = []
        for cat in sorted(all_categories):
            actual = current.get(cat, 0)
            objetivo = target.get(cat, 0)
            desviacion = actual - objetivo

            # Calcular desviación relativa
            if objetivo > 0:
                desv_rel = (desviacion / objetivo) * 100
            else:
                desv_rel = 0 if desviacion == 0 else 999

            # Determinar status
            if abs(desviacion) <= 5:  # Tolerancia de 5 puntos porcentuales
                status = "OK"
            elif desviacion > 0:
                status = "SOBRE"
            else:
                status = "BAJO"

            rows.append({
                'categoria': cat,
                'actual_pct': actual,
                'objetivo_pct': objetivo,
                'desviacion': desviacion,
                'desviacion_relativa': desv_rel,
                'status': status
            })

        df_comp = pd.DataFrame(rows)

        # Ordenar por desviación absoluta descendente
        df_comp['desv_abs'] = df_comp['desviacion'].abs()
        df_comp = df_comp.sort_values('desv_abs', ascending=False)
        df_comp = df_comp.drop('desv_abs', axis=1)

        return df_comp

    def generate_rebalance_suggestions(
        self,
        df_comparison: pd.DataFrame,
        total_valor: float
    ) -> List[Dict]:
        """
        Genera sugerencias de rebalanceo.

        Args:
            df_comparison: DataFrame de compare_allocations
            total_valor: Valor total de la cartera

        Returns:
            Lista de dict con 'accion', 'categoria', 'monto_sugerido'
        """
        suggestions = []

        for _, row in df_comparison.iterrows():
            if row['status'] == 'OK':
                continue

            desv = row['desviacion']
            cat = row['categoria']

            # Calcular monto a ajustar
            monto_ajuste = abs(desv / 100 * total_valor)

            if row['status'] == 'SOBRE':
                suggestions.append({
                    'accion': 'VENDER',
                    'categoria': cat,
                    'monto_sugerido': monto_ajuste,
                    'desviacion_pct': desv
                })
            elif row['status'] == 'BAJO':
                suggestions.append({
                    'accion': 'COMPRAR',
                    'categoria': cat,
                    'monto_sugerido': monto_ajuste,
                    'desviacion_pct': desv
                })

        return suggestions

    def analyze_portfolio(
        self,
        df: pd.DataFrame,
        comitente: str
    ) -> Tuple[Dict, pd.DataFrame, List[Dict]]:
        """
        Análisis completo de una cartera.

        Args:
            df: DataFrame con las posiciones del cliente
            comitente: Número de comitente

        Returns:
            Tuple de:
            - target_allocation (dict)
            - comparison_df (DataFrame)
            - suggestions (list)
        """
        # Obtener objetivo
        target = self.get_target_allocation(comitente)

        # Calcular actual
        current = self.calculate_current_allocation(df)

        # Comparar
        comparison = self.compare_allocations(current, target)

        # Generar sugerencias
        total_valor = df['valor'].sum()
        suggestions = self.generate_rebalance_suggestions(comparison, total_valor)

        return target, comparison, suggestions


# =============================================================================
# TESTS
# =============================================================================

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    # Crear datos de prueba
    test_data = {
        'categoria': ['SPY', 'SPY', 'MERV', 'LETRAS', 'GLD', 'LIQUIDEZ'],
        'valor': [300000, 200000, 150000, 100000, 80000, 50000],
        'ticker': ['SPY', 'QQQ', 'YPFD', 'AL30', 'GLD', 'USD']
    }
    df_test = pd.DataFrame(test_data)

    # Test con comitente 34491 (perfil agresivo)
    manager = AllocationManager()

    print("=" * 70)
    print("TEST DE ALLOCATION MANAGER - Comitente 34491")
    print("=" * 70)
    print()

    target, comparison, suggestions = manager.analyze_portfolio(df_test, '34491')

    print("Alocación Objetivo:")
    for cat, pct in sorted(target.items(), key=lambda x: -x[1]):
        print(f"  {cat:15} {pct:>6.1f}%")

    print()
    print("Comparación Actual vs Objetivo:")
    print(comparison.to_string(index=False))

    print()
    print("Sugerencias de Rebalanceo:")
    for sugg in suggestions:
        accion = sugg['accion']
        cat = sugg['categoria']
        monto = sugg['monto_sugerido']
        desv = sugg['desviacion_pct']
        print(f"  {accion:8} {cat:15} ${monto:>12,.0f}  (desviación: {desv:+.1f}%)")

    print()
    print("=" * 70)
