"""
Google Sheets Manager - Gestión de datos en la nube
====================================================
Maneja la conexión y operaciones CRUD con Google Sheets.
"""

import os
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import httplib2
from google_auth_httplib2 import AuthorizedHttp

from config import (
    CREDENTIALS_FILE,
    TOKEN_FILE,
    SPREADSHEET_NAME,
    SPREADSHEET_ID,
    SHEET_CARTERAS,
    SHEET_PERFILES,
    SHEET_CUSTOM,
    SHEET_HISTORIAL,
    SHEET_SNAPSHOTS,
    SHEET_TICKER_MAPPINGS,
    SHEET_DETALLE_ACTIVOS,
    SHEET_CUSTOM_CATEGORIES,
    SHEET_SECTOR_MAPPINGS,
    SHEET_PERFILES_CUSTOM,
    DEFAULT_PROFILES,
    KNOWN_PORTFOLIOS,
    CATEGORY_COLORS,
)

logger = logging.getLogger(__name__)

# Scopes necesarios (deben coincidir con el token existente)
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
]


class SheetsManager:
    """Gestor de Google Sheets para el sistema de carteras."""

    def __init__(self):
        self.creds = None
        self.sheets_service = None
        self.drive_service = None
        self.spreadsheet_id = SPREADSHEET_ID  # Usar ID desde config
        # Rate limiting para writes a Google Sheets (límite: 60 req/min)
        self._last_write_time = 0
        self._write_delay = 1.0  # segundos mínimos entre writes
        self._retry_log = []  # registro de reintentos por rate limit
        self._authenticate()

    def _authenticate(self):
        """
        Autenticación con Google API.

        Soporta dos modos:
        1. Variables de entorno (para Render/producción):
           - GOOGLE_TOKEN: JSON string del token (refresh token)
        2. Archivos locales (para desarrollo):
           - credentials.json
           - token.json
        """
        # Modo 1: Variables de entorno (Render/producción)
        google_token_env = os.environ.get('GOOGLE_TOKEN')

        # Debug: mostrar si la variable existe
        logger.info(f"GOOGLE_TOKEN env var exists: {google_token_env is not None}")
        if google_token_env:
            logger.info(f"GOOGLE_TOKEN length: {len(google_token_env)}")
            logger.info(f"GOOGLE_TOKEN starts with: {google_token_env[:50] if len(google_token_env) > 50 else google_token_env}")

        if google_token_env and google_token_env.strip().startswith('{'):
            # Usar token desde variable de entorno
            logger.info("Usando credenciales desde variable de entorno GOOGLE_TOKEN")
            try:
                token_data = json.loads(google_token_env)
                self.creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            except Exception as e:
                logger.error(f"Error parseando GOOGLE_TOKEN: {e}")
                self.creds = None

        # Modo 2: Archivo token.json local (desarrollo)
        elif TOKEN_FILE.exists():
            logger.info("Usando credenciales desde archivo token.json")
            self.creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

        # Validar y refrescar si es necesario
        if not self.creds or not self.creds.valid:
            # Intentar refrescar si tenemos refresh_token
            if self.creds and self.creds.refresh_token:
                try:
                    logger.info("Refrescando token expirado...")
                    self.creds.refresh(Request())
                    logger.info("Token refrescado exitosamente")

                    # Guardar token actualizado solo si estamos en modo archivo local
                    if not google_token_env and TOKEN_FILE.exists():
                        with open(TOKEN_FILE, 'w') as token:
                            token.write(self.creds.to_json())
                except Exception as e:
                    logger.error(f"Error refrescando token: {e}")
                    if google_token_env:
                        raise RuntimeError(
                            f"Error refrescando GOOGLE_TOKEN: {e}. "
                            "Genera un nuevo token localmente y actualiza la variable de entorno."
                        )
                    raise
            else:
                # No hay refresh_token, necesitamos autenticar desde cero
                if google_token_env and google_token_env.strip().startswith('{'):
                    # En producción sin refresh_token válido
                    raise RuntimeError(
                        "GOOGLE_TOKEN no tiene refresh_token válido. "
                        "Genera un nuevo token localmente y actualiza la variable de entorno."
                    )
                elif not CREDENTIALS_FILE.exists():
                    raise FileNotFoundError(
                        f"No se encontró {CREDENTIALS_FILE}. "
                        "Copia credentials.json desde el proyecto de Sol de Mayo, "
                        "o configura la variable de entorno GOOGLE_TOKEN."
                    )
                else:
                    # Desarrollo: flujo OAuth interactivo
                    logger.info("Iniciando flujo OAuth interactivo...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(CREDENTIALS_FILE), SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)

                    # Guardar token para próximas sesiones
                    with open(TOKEN_FILE, 'w') as token:
                        token.write(self.creds.to_json())

                    # Mostrar el token para configurar en Render
                    logger.info("=" * 60)
                    logger.info("TOKEN GENERADO - Copia esto para GOOGLE_TOKEN en Render:")
                    logger.info("=" * 60)
                    logger.info(self.creds.to_json())
                    logger.info("=" * 60)

        # Crear HTTP clients separados para evitar errores SSL en entornos multi-thread (Streamlit)
        # httplib2 no es thread-safe, así que cada servicio necesita su propio client
        http_sheets = httplib2.Http()
        authed_http_sheets = AuthorizedHttp(self.creds, http=http_sheets)
        self.sheets_service = build('sheets', 'v4', http=authed_http_sheets, cache_discovery=False)

        http_drive = httplib2.Http()
        authed_http_drive = AuthorizedHttp(self.creds, http=http_drive)
        self.drive_service = build('drive', 'v3', http=authed_http_drive, cache_discovery=False)

        logger.info("Autenticación con Google exitosa")

    def _throttled_execute(self, request, operation_name="write"):
        """
        Ejecuta un request a la API de Sheets con rate limiting y retry.

        - Espera mínimo 1s entre writes para no exceder 60 req/min
        - En caso de 429 (rate limit), reintenta hasta 3 veces con backoff exponencial
        - Registra reintentos en self._retry_log

        Args:
            request: Objeto request de la API de Google Sheets (pre-.execute())
            operation_name: Nombre descriptivo para logging

        Returns:
            Resultado de request.execute()

        Raises:
            HttpError: Si falla después de todos los reintentos
        """
        # Rate limiting: asegurar mínimo self._write_delay entre writes
        elapsed = time.time() - self._last_write_time
        if elapsed < self._write_delay:
            time.sleep(self._write_delay - elapsed)

        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                result = request.execute()
                self._last_write_time = time.time()
                if attempt > 0:
                    self._retry_log.append({
                        'operation': operation_name,
                        'attempts': attempt + 1,
                        'status': 'success'
                    })
                    logger.info(
                        f"  Retry exitoso para '{operation_name}' "
                        f"(intento {attempt + 1})"
                    )
                return result
            except HttpError as e:
                if e.resp.status == 429 and attempt < max_retries:
                    wait_time = 5 * (2 ** attempt)  # 5s, 10s, 20s
                    logger.warning(
                        f"  Rate limit (429) en '{operation_name}'. "
                        f"Reintentando en {wait_time}s "
                        f"(intento {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(wait_time)
                    self._last_write_time = time.time()
                else:
                    if e.resp.status == 429:
                        self._retry_log.append({
                            'operation': operation_name,
                            'attempts': max_retries + 1,
                            'status': 'failed',
                            'error': str(e)
                        })
                        logger.error(
                            f"  Rate limit DEFINITIVO en '{operation_name}' "
                            f"tras {max_retries + 1} intentos"
                        )
                    raise

    def get_retry_log(self) -> List[Dict]:
        """Retorna el registro de reintentos por rate limit."""
        return list(self._retry_log)

    def clear_retry_log(self):
        """Limpia el registro de reintentos."""
        self._retry_log = []

    def get_or_create_spreadsheet(self) -> str:
        """Obtiene o crea el spreadsheet principal."""
        # Buscar spreadsheet existente
        try:
            results = self.drive_service.files().list(
                q=f"name='{SPREADSHEET_NAME}' and mimeType='application/vnd.google-apps.spreadsheet'",
                spaces='drive',
                fields='files(id, name)'
            ).execute()

            files = results.get('files', [])
            if files:
                self.spreadsheet_id = files[0]['id']
                logger.info(f"Spreadsheet encontrado: {self.spreadsheet_id}")
                return self.spreadsheet_id

        except HttpError as e:
            logger.warning(f"Error buscando spreadsheet: {e}")

        # Crear nuevo spreadsheet
        spreadsheet = {
            'properties': {'title': SPREADSHEET_NAME},
            'sheets': [
                {'properties': {'title': SHEET_CARTERAS}},
                {'properties': {'title': SHEET_PERFILES}},
                {'properties': {'title': SHEET_CUSTOM}},
                {'properties': {'title': SHEET_HISTORIAL}},
                {'properties': {'title': SHEET_SNAPSHOTS}},
            ]
        }

        result = self.sheets_service.spreadsheets().create(
            body=spreadsheet,
            fields='spreadsheetId'
        ).execute()

        self.spreadsheet_id = result.get('spreadsheetId')
        logger.info(f"Spreadsheet creado: {self.spreadsheet_id}")

        # Inicializar con datos por defecto
        self._initialize_default_data()

        return self.spreadsheet_id

    def _initialize_default_data(self):
        """Inicializa las hojas con datos por defecto."""
        # Headers y datos para carteras_maestro
        carteras_data = [
            ['comitente', 'nombre', 'perfil_base', 'activo'],
        ]
        for comitente, info in KNOWN_PORTFOLIOS.items():
            carteras_data.append([comitente, info['nombre'], info['perfil'], 'TRUE'])

        self._write_range(SHEET_CARTERAS, 'A1', carteras_data)

        # Headers y datos para perfiles_alocacion
        perfiles_data = [
            ['perfil', 'categoria', 'objetivo_pct'],
        ]
        for perfil, categorias in DEFAULT_PROFILES.items():
            for cat, pct in categorias.items():
                perfiles_data.append([perfil, cat, pct])

        self._write_range(SHEET_PERFILES, 'A1', perfiles_data)

        # Headers para alocacion_custom
        custom_data = [['comitente', 'categoria', 'objetivo_pct']]
        self._write_range(SHEET_CUSTOM, 'A1', custom_data)

        # Headers para historial_tenencias
        historial_data = [[
            'fecha', 'comitente', 'nombre', 'categoria',
            'valor', 'pct_cartera', 'valor_total_cartera'
        ]]
        self._write_range(SHEET_HISTORIAL, 'A1', historial_data)

        # Headers para snapshots_totales
        snapshots_data = [[
            'fecha', 'comitente', 'nombre', 'valor_total',
            'variacion_pct', 'variacion_absoluta'
        ]]
        self._write_range(SHEET_SNAPSHOTS, 'A1', snapshots_data)

        logger.info("Datos iniciales creados en spreadsheet")

    def _write_range(self, sheet: str, range_start: str, values: List[List]):
        """Escribe valores en un rango (con rate limiting y retry)."""
        range_name = f"{sheet}!{range_start}"
        body = {'values': values}

        request = self.sheets_service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body=body
        )
        self._throttled_execute(request, f"write_range({sheet})")

    def _append_rows(self, sheet: str, values: List[List]):
        """Agrega filas al final de una hoja (con rate limiting y retry)."""
        range_name = f"{sheet}!A:Z"
        body = {'values': values}

        request = self.sheets_service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body=body
        )
        self._throttled_execute(request, f"append_rows({sheet})")

    def _read_all(self, sheet: str) -> List[Dict]:
        """Lee todos los datos de una hoja como lista de diccionarios."""
        range_name = f"{sheet}!A:Z"

        result = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=range_name
        ).execute()

        values = result.get('values', [])
        if not values or len(values) < 2:
            return []

        headers = values[0]
        data = []
        for row in values[1:]:
            # Extender fila si tiene menos columnas que headers
            row_extended = row + [''] * (len(headers) - len(row))
            data.append(dict(zip(headers, row_extended)))

        return data

    # =========================================================================
    # CARTERAS
    # =========================================================================

    def get_all_portfolios(self) -> List[Dict]:
        """Obtiene todas las carteras registradas."""
        return self._read_all(SHEET_CARTERAS)

    def get_portfolio(self, comitente: str) -> Optional[Dict]:
        """Obtiene una cartera por comitente."""
        portfolios = self.get_all_portfolios()
        comitente_str = str(comitente).strip()
        for p in portfolios:
            if str(p.get('comitente', '')).strip() == comitente_str:
                return p
        return None

    def add_portfolio(self, comitente: str, nombre: str, perfil: str = 'moderado'):
        """Agrega una nueva cartera."""
        self._append_rows(SHEET_CARTERAS, [[comitente, nombre, perfil, 'TRUE']])
        logger.info(f"Cartera agregada: {comitente} - {nombre}")

    # =========================================================================
    # PERFILES DE ALOCACIÓN
    # =========================================================================

    def get_profile_allocation(self, perfil: str) -> Dict[str, float]:
        """Obtiene la alocación objetivo de un perfil."""
        data = self._read_all(SHEET_PERFILES)
        allocation = {}
        for row in data:
            if row.get('perfil') == perfil:
                cat = row.get('categoria')
                pct = float(row.get('objetivo_pct', 0))
                allocation[cat] = pct
        return allocation

    def get_custom_allocation(self, comitente: str) -> Dict[str, float]:
        """Obtiene overrides de alocación para un cliente específico."""
        data = self._read_all(SHEET_CUSTOM)
        allocation = {}
        comitente_str = str(comitente).strip()
        for row in data:
            if str(row.get('comitente', '')).strip() == comitente_str:
                cat = row.get('categoria')
                pct = float(row.get('objetivo_pct', 0))
                allocation[cat] = pct
        return allocation

    def get_target_allocation(self, comitente: str) -> Dict[str, float]:
        """
        Obtiene la alocación objetivo final para un cliente.
        Combina el perfil base con los overrides custom.
        """
        portfolio = self.get_portfolio(comitente)
        if not portfolio:
            # Si no existe, usar perfil moderado por defecto
            return self.get_profile_allocation('moderado')

        perfil = portfolio.get('perfil_base', 'moderado')
        base_allocation = self.get_profile_allocation(perfil)
        custom_allocation = self.get_custom_allocation(comitente)

        # Merge: custom sobreescribe base
        final_allocation = {**base_allocation, **custom_allocation}
        return final_allocation

    def set_custom_allocation(self, comitente: str, categoria: str, objetivo_pct: float):
        """Establece un override de alocación para un cliente."""
        # Primero verificar si ya existe
        data = self._read_all(SHEET_CUSTOM)
        comitente_str = str(comitente).strip()
        for i, row in enumerate(data):
            if str(row.get('comitente', '')).strip() == comitente_str and row.get('categoria') == categoria:
                # Actualizar existente (fila i+2 porque hay header)
                range_name = f"{SHEET_CUSTOM}!C{i+2}"
                self.sheets_service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name,
                    valueInputOption='USER_ENTERED',
                    body={'values': [[objetivo_pct]]}
                ).execute()
                return

        # Si no existe, agregar nueva fila
        self._append_rows(SHEET_CUSTOM, [[comitente, categoria, objetivo_pct]])

    def set_custom_allocation_batch(self, comitente: str, allocations: Dict[str, float]):
        """
        Establece toda la alocación custom para un cliente de una vez.
        Más eficiente que llamar set_custom_allocation múltiples veces.

        Args:
            comitente: Número de comitente
            allocations: Dict con {categoria: porcentaje}
        """
        comitente_str = str(comitente).strip()

        # 1. Leer datos actuales
        data = self._read_all(SHEET_CUSTOM)

        # 2. Encontrar filas del comitente y filas de otros
        other_rows = []
        for row in data:
            if str(row.get('comitente', '')).strip() != comitente_str:
                other_rows.append([
                    row.get('comitente', ''),
                    row.get('categoria', ''),
                    row.get('objetivo_pct', 0)
                ])

        # 3. Crear nuevas filas para este comitente
        new_rows = []
        for cat, pct in allocations.items():
            new_rows.append([comitente_str, cat, pct])

        # 4. Combinar: otras filas + nuevas filas del comitente
        all_rows = other_rows + new_rows

        # 5. Reescribir toda la hoja (header + datos)
        header = [['comitente', 'categoria', 'objetivo_pct']]
        all_data = header + all_rows

        # Limpiar hoja y escribir todo
        self.sheets_service.spreadsheets().values().clear(
            spreadsheetId=self.spreadsheet_id,
            range=f"{SHEET_CUSTOM}!A:C"
        ).execute()

        if all_data:
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{SHEET_CUSTOM}!A1",
                valueInputOption='USER_ENTERED',
                body={'values': all_data}
            ).execute()

        logger.info(f"Alocación batch guardada para {comitente}: {len(new_rows)} categorías")

    # =========================================================================
    # HISTORIAL
    # =========================================================================

    def save_snapshot(self, fecha: str, comitente: str, nombre: str,
                      categoria_data: List[Dict], valor_total: float):
        """
        Guarda un snapshot de la cartera.
        Si ya existe un snapshot para la misma fecha+comitente, lo reemplaza
        (evita duplicación al reprocesar).

        Args:
            fecha: Fecha del snapshot (YYYY-MM-DD)
            comitente: Número de comitente
            nombre: Nombre del cliente
            categoria_data: Lista de {categoria, valor, pct}
            valor_total: Valor total de la cartera
        """
        # Deduplicación: borrar datos previos para esta fecha+comitente
        self._delete_snapshot_for_date(fecha, comitente)

        # Guardar detalle por categoría
        historial_rows = []
        for cat in categoria_data:
            historial_rows.append([
                fecha,
                comitente,
                nombre,
                cat['categoria'],
                cat['valor'],
                cat['pct'],
                valor_total
            ])

        if historial_rows:
            self._append_rows(SHEET_HISTORIAL, historial_rows)

        # Calcular variación vs snapshot anterior
        variacion_pct = None
        variacion_abs = None

        prev_snapshot = self.get_last_snapshot(comitente)
        if prev_snapshot:
            prev_valor = float(prev_snapshot.get('valor_total', 0))
            if prev_valor > 0:
                variacion_abs = valor_total - prev_valor
                variacion_pct = (variacion_abs / prev_valor) * 100

        # Guardar snapshot total
        self._append_rows(SHEET_SNAPSHOTS, [[
            fecha,
            comitente,
            nombre,
            valor_total,
            variacion_pct if variacion_pct is not None else '',
            variacion_abs if variacion_abs is not None else ''
        ]])

        logger.info(f"Snapshot guardado: {comitente} - {fecha} - ${valor_total:,.2f}")

    def _date_matches(self, stored_fecha: str, target_fecha: str) -> bool:
        """
        Compara una fecha almacenada en Sheets con una fecha objetivo YYYY-MM-DD.
        Sheets puede almacenar la fecha como serial number (ej: 46071)
        o como string (ej: '2026-02-19').
        """
        stored = str(stored_fecha).strip()
        target = str(target_fecha).strip()

        # Comparación directa
        if stored == target:
            return True

        # Intentar convertir serial number de Sheets a fecha
        try:
            serial = float(stored)
            date = pd.to_datetime(serial, origin='1899-12-30', unit='D')
            return date.strftime('%Y-%m-%d') == target
        except (ValueError, TypeError):
            return False

    def _read_columns_lightweight(self, sheet: str, columns: str) -> List[List]:
        """
        Lee solo columnas específicas de un sheet (ej: 'A:B').
        Mucho más liviano en memoria que _read_all que lee A:Z.
        """
        result = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"{sheet}!{columns}"
        ).execute()
        return result.get('values', [])

    def _delete_snapshot_for_date(self, fecha: str, comitente: str):
        """
        Elimina snapshots existentes para una fecha+comitente específicos.
        Borra de SHEET_HISTORIAL y SHEET_SNAPSHOTS para evitar duplicación.
        Usa lectura liviana (solo columnas A:B) para no consumir memoria.
        """
        comitente_str = str(comitente).strip()
        fecha_str = str(fecha).strip()

        # 1. Limpiar historial_tenencias (columnas: A=fecha, B=comitente)
        try:
            rows = self._read_columns_lightweight(SHEET_HISTORIAL, 'A:B')
            if len(rows) > 1:  # tiene header + datos
                ranges_to_clear = []
                for i, row in enumerate(rows[1:], start=2):  # skip header, base 1
                    if len(row) < 2:
                        continue
                    row_fecha = str(row[0]).strip()
                    row_comitente = str(row[1]).strip()
                    if row_comitente == comitente_str and self._date_matches(row_fecha, fecha_str):
                        ranges_to_clear.append(
                            f"{SHEET_HISTORIAL}!A{i}:G{i}"
                        )

                if ranges_to_clear:
                    logger.info(
                        f"Dedup: borrando {len(ranges_to_clear)} filas de "
                        f"historial para {comitente} fecha {fecha}"
                    )
                    request = self.sheets_service.spreadsheets().values().batchClear(
                        spreadsheetId=self.spreadsheet_id,
                        body={'ranges': ranges_to_clear}
                    )
                    self._throttled_execute(
                        request, f"dedup_historial({comitente})"
                    )
        except HttpError as e:
            logger.warning(f"Error limpiando historial duplicado: {e}")

        # 2. Limpiar snapshots_totales (columnas: A=fecha, B=comitente)
        try:
            rows = self._read_columns_lightweight(SHEET_SNAPSHOTS, 'A:B')
            if len(rows) > 1:
                ranges_to_clear = []
                for i, row in enumerate(rows[1:], start=2):
                    if len(row) < 2:
                        continue
                    row_fecha = str(row[0]).strip()
                    row_comitente = str(row[1]).strip()
                    if row_comitente == comitente_str and self._date_matches(row_fecha, fecha_str):
                        ranges_to_clear.append(
                            f"{SHEET_SNAPSHOTS}!A{i}:F{i}"
                        )

                if ranges_to_clear:
                    logger.info(
                        f"Dedup: borrando {len(ranges_to_clear)} filas de "
                        f"snapshots para {comitente} fecha {fecha}"
                    )
                    request = self.sheets_service.spreadsheets().values().batchClear(
                        spreadsheetId=self.spreadsheet_id,
                        body={'ranges': ranges_to_clear}
                    )
                    self._throttled_execute(
                        request, f"dedup_snapshots({comitente})"
                    )
        except HttpError as e:
            logger.warning(f"Error limpiando snapshots duplicados: {e}")

    def get_last_snapshot(self, comitente: str) -> Optional[Dict]:
        """Obtiene el último snapshot de una cartera."""
        data = self._read_all(SHEET_SNAPSHOTS)
        # Filtrar por comitente y ordenar por fecha
        comitente_str = str(comitente).strip()
        snapshots = [d for d in data if str(d.get('comitente', '')).strip() == comitente_str]
        if not snapshots:
            return None

        # Ordenar por fecha descendente
        snapshots.sort(key=lambda x: x.get('fecha', ''), reverse=True)
        return snapshots[0]

    def get_portfolio_history(self, comitente: str) -> List[Dict]:
        """Obtiene todo el historial de snapshots de una cartera."""
        data = self._read_all(SHEET_SNAPSHOTS)
        comitente_str = str(comitente).strip()
        snapshots = [d for d in data if str(d.get('comitente', '')).strip() == comitente_str]
        snapshots.sort(key=lambda x: x.get('fecha', ''))
        return snapshots

    def get_category_history(self, comitente: str, categoria: str) -> List[Dict]:
        """Obtiene el historial de una categoría específica."""
        data = self._read_all(SHEET_HISTORIAL)
        comitente_str = str(comitente).strip()
        history = [
            d for d in data
            if str(d.get('comitente', '')).strip() == comitente_str and d.get('categoria') == categoria
        ]
        history.sort(key=lambda x: x.get('fecha', ''))
        return history

    def get_historial_tenencias(self) -> pd.DataFrame:
        """Obtiene todos los datos de historial_tenencias como DataFrame."""
        data = self._read_all(SHEET_HISTORIAL)
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)

    def get_snapshots_totales(self) -> pd.DataFrame:
        """Obtiene todos los datos de snapshots_totales como DataFrame."""
        data = self._read_all(SHEET_SNAPSHOTS)
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)

    def get_carteras_maestro(self) -> pd.DataFrame:
        """Obtiene todos los datos de carteras_maestro como DataFrame."""
        data = self._read_all(SHEET_CARTERAS)
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)

    def get_perfiles_alocacion(self) -> pd.DataFrame:
        """Obtiene todos los datos de perfiles_alocacion como DataFrame."""
        data = self._read_all(SHEET_PERFILES)
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)

    def get_alocacion_custom(self) -> pd.DataFrame:
        """Obtiene todos los datos de alocacion_custom como DataFrame."""
        data = self._read_all(SHEET_CUSTOM)
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)

    # =========================================================================
    # MAPEOS DE TICKERS
    # =========================================================================

    def get_custom_ticker_mappings(self) -> Dict[str, str]:
        """Obtiene los mapeos custom de tickers desde Google Sheets."""
        try:
            data = self._read_all(SHEET_TICKER_MAPPINGS)
            mappings = {}
            for row in data:
                ticker = row.get('ticker', '').upper().strip()
                categoria = row.get('categoria', '')
                if ticker and categoria:
                    mappings[ticker] = categoria
            return mappings
        except HttpError as e:
            if 'Unable to parse range' in str(e):
                # La hoja no existe, crearla
                self._create_ticker_mappings_sheet()
                return {}
            logger.warning(f"Error leyendo mapeos de tickers: {e}")
            return {}

    def _create_ticker_mappings_sheet(self):
        """Crea la hoja de mapeos de tickers si no existe."""
        try:
            # Agregar nueva hoja
            requests = [{
                'addSheet': {
                    'properties': {
                        'title': SHEET_TICKER_MAPPINGS
                    }
                }
            }]
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={'requests': requests}
            ).execute()

            # Agregar headers
            self._write_range(SHEET_TICKER_MAPPINGS, 'A1', [['ticker', 'categoria', 'descripcion']])
            logger.info(f"Hoja {SHEET_TICKER_MAPPINGS} creada exitosamente")
        except HttpError as e:
            if 'already exists' in str(e):
                logger.info(f"Hoja {SHEET_TICKER_MAPPINGS} ya existe")
            else:
                logger.error(f"Error creando hoja de mapeos: {e}")

    def save_custom_ticker_mapping(self, ticker: str, categoria: str, descripcion: str = "") -> bool:
        """
        Guarda un mapeo custom de ticker a categoría.

        Args:
            ticker: Símbolo del activo
            categoria: Categoría destino
            descripcion: Descripción opcional

        Returns:
            True si se guardó exitosamente
        """
        try:
            ticker = ticker.upper().strip()

            # Verificar si ya existe
            data = self._read_all(SHEET_TICKER_MAPPINGS)
            for i, row in enumerate(data):
                if row.get('ticker', '').upper().strip() == ticker:
                    # Actualizar existente (fila i+2 por header)
                    range_name = f"{SHEET_TICKER_MAPPINGS}!B{i+2}:C{i+2}"
                    self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=range_name,
                        valueInputOption='USER_ENTERED',
                        body={'values': [[categoria, descripcion]]}
                    ).execute()
                    logger.info(f"Mapeo actualizado: {ticker} -> {categoria}")
                    return True

            # Agregar nuevo
            self._append_rows(SHEET_TICKER_MAPPINGS, [[ticker, categoria, descripcion]])
            logger.info(f"Mapeo agregado: {ticker} -> {categoria}")
            return True

        except HttpError as e:
            if 'Unable to parse range' in str(e):
                # Crear hoja y reintentar
                self._create_ticker_mappings_sheet()
                self._append_rows(SHEET_TICKER_MAPPINGS, [[ticker, categoria, descripcion]])
                return True
            logger.error(f"Error guardando mapeo de ticker: {e}")
            return False

    def delete_custom_ticker_mapping(self, ticker: str) -> bool:
        """Elimina un mapeo custom de ticker."""
        try:
            ticker = ticker.upper().strip()
            data = self._read_all(SHEET_TICKER_MAPPINGS)

            for i, row in enumerate(data):
                if row.get('ticker', '').upper().strip() == ticker:
                    # Limpiar la fila (no podemos eliminar fácilmente)
                    range_name = f"{SHEET_TICKER_MAPPINGS}!A{i+2}:C{i+2}"
                    self.sheets_service.spreadsheets().values().clear(
                        spreadsheetId=self.spreadsheet_id,
                        range=range_name
                    ).execute()
                    logger.info(f"Mapeo eliminado: {ticker}")
                    return True

            return False
        except HttpError as e:
            logger.error(f"Error eliminando mapeo de ticker: {e}")
            return False

    # =========================================================================
    # DETALLE DE ACTIVOS (TICKER LEVEL)
    # =========================================================================

    def _create_detalle_activos_sheet(self):
        """Crea la hoja de detalle de activos si no existe."""
        try:
            requests = [{
                'addSheet': {
                    'properties': {
                        'title': SHEET_DETALLE_ACTIVOS
                    }
                }
            }]
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={'requests': requests}
            ).execute()

            # Headers (incluyendo sector después de categoria)
            headers = [['fecha', 'comitente', 'nombre', 'ticker', 'descripcion',
                       'cantidad', 'precio', 'valor', 'categoria', 'sector', 'tc_mep', 'tc_ccl']]
            self._write_range(SHEET_DETALLE_ACTIVOS, 'A1', headers)
            logger.info(f"Hoja {SHEET_DETALLE_ACTIVOS} creada exitosamente")
        except HttpError as e:
            if 'already exists' in str(e):
                logger.info(f"Hoja {SHEET_DETALLE_ACTIVOS} ya existe")
            else:
                logger.error(f"Error creando hoja de detalle: {e}")

    def save_detalle_activos(self, fecha: str, comitente: str, nombre: str,
                             activos: List[Dict], tc_mep: float = 0, tc_ccl: float = 0) -> bool:
        """
        Guarda el detalle de activos (nivel ticker) para un comitente.

        Args:
            fecha: Fecha del snapshot (YYYY-MM-DD)
            comitente: Número de comitente
            nombre: Nombre del cliente
            activos: Lista de dicts con ticker, descripcion, cantidad, precio, valor, categoria, sector
            tc_mep: Tipo de cambio MEP
            tc_ccl: Tipo de cambio CCL

        Returns:
            True si se guardó exitosamente
        """
        try:
            # Primero borrar datos anteriores de este comitente
            self._delete_detalle_activos(comitente)

            # Preparar filas (incluyendo sector)
            rows = []
            for activo in activos:
                rows.append([
                    fecha,
                    comitente,
                    nombre,
                    activo.get('ticker', ''),
                    activo.get('descripcion', ''),
                    activo.get('cantidad', 0),
                    activo.get('precio', 0),
                    activo.get('valor', 0),
                    activo.get('categoria', 'OTROS'),
                    activo.get('sector', 'N/A'),
                    tc_mep,
                    tc_ccl
                ])

            if rows:
                self._append_rows(SHEET_DETALLE_ACTIVOS, rows)
                logger.info(f"Guardados {len(rows)} activos para {comitente}")

            return True

        except HttpError as e:
            if 'Unable to parse range' in str(e):
                self._create_detalle_activos_sheet()
                return self.save_detalle_activos(fecha, comitente, nombre, activos, tc_mep, tc_ccl)
            logger.error(f"Error guardando detalle de activos: {e}")
            return False

    def _delete_detalle_activos(self, comitente: str):
        """Elimina los activos anteriores de un comitente (batch clear)."""
        try:
            # Leer solo columna B (comitente) - mucho más liviano que _read_all
            rows = self._read_columns_lightweight(SHEET_DETALLE_ACTIVOS, 'B:B')
            if len(rows) <= 1:
                return

            # Encontrar filas a eliminar
            comitente_str = str(comitente).strip()
            ranges_to_clear = []
            for i, row in enumerate(rows[1:], start=2):  # skip header, base 1
                if row and str(row[0]).strip() == comitente_str:
                    ranges_to_clear.append(
                        f"{SHEET_DETALLE_ACTIVOS}!A{i}:L{i}"
                    )

            if not ranges_to_clear:
                logger.info(f"No hay filas previas para eliminar de {comitente}")
                return

            logger.info(
                f"Eliminando {len(ranges_to_clear)} filas de "
                f"detalle_activos para {comitente} (batch clear)"
            )

            # Batch clear: 1 sola llamada API en vez de N individuales
            request = self.sheets_service.spreadsheets().values().batchClear(
                spreadsheetId=self.spreadsheet_id,
                body={'ranges': ranges_to_clear}
            )
            self._throttled_execute(
                request, f"batch_clear_detalle({comitente})"
            )

        except HttpError as e:
            logger.warning(f"Error eliminando activos anteriores: {e}")

    def get_detalle_activos(self, comitente: str, fecha: str = None) -> pd.DataFrame:
        """
        Obtiene el detalle de activos para un comitente.

        Args:
            comitente: Número de comitente
            fecha: Fecha específica (YYYY-MM-DD). Si es None, devuelve la más reciente.

        Returns:
            DataFrame con ticker, descripcion, cantidad, precio, valor, categoria, tc_mep, tc_ccl
        """
        try:
            data = self._read_all(SHEET_DETALLE_ACTIVOS)
            if not data:
                return pd.DataFrame()

            # Filtrar por comitente (convertir ambos a string para comparación consistente)
            comitente_str = str(comitente).strip()
            filtered = [row for row in data if str(row.get('comitente', '')).strip() == comitente_str]
            if not filtered:
                return pd.DataFrame()

            df = pd.DataFrame(filtered)

            # Convertir valores numéricos
            numeric_cols = ['cantidad', 'precio', 'valor', 'tc_mep', 'tc_ccl']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            # Filtrar por fecha (la más reciente si no se especifica)
            if 'fecha' in df.columns:
                if fecha:
                    df = df[df['fecha'] == fecha]
                else:
                    # Obtener la fecha más reciente
                    fechas = df['fecha'].unique()
                    if len(fechas) > 0:
                        fecha_mas_reciente = sorted(fechas, reverse=True)[0]
                        df = df[df['fecha'] == fecha_mas_reciente]

            return df

        except HttpError as e:
            if 'Unable to parse range' in str(e):
                return pd.DataFrame()
            logger.error(f"Error obteniendo detalle de activos: {e}")
            return pd.DataFrame()

    def get_tc_for_comitente(self, comitente: str) -> Dict[str, float]:
        """
        Obtiene el TC guardado para un comitente.

        Returns:
            Dict con 'tc_mep' y 'tc_ccl'
        """
        df = self.get_detalle_activos(comitente)
        if df.empty:
            return {'tc_mep': 1150.0, 'tc_ccl': 1150.0}

        tc_mep = df['tc_mep'].iloc[0] if 'tc_mep' in df.columns else 1150.0
        tc_ccl = df['tc_ccl'].iloc[0] if 'tc_ccl' in df.columns else 1150.0

        return {
            'tc_mep': float(tc_mep) if tc_mep > 0 else 1150.0,
            'tc_ccl': float(tc_ccl) if tc_ccl > 0 else 1150.0
        }

    def get_all_tc(self) -> Dict[str, Dict[str, float]]:
        """
        Obtiene el TC de todos los comitentes.

        Returns:
            Dict {comitente: {'tc_mep': x, 'tc_ccl': y}}
        """
        try:
            data = self._read_all(SHEET_DETALLE_ACTIVOS)
            if not data:
                return {}

            result = {}
            for row in data:
                comitente = row.get('comitente')
                if comitente and comitente not in result:
                    tc_mep = float(row.get('tc_mep', 0) or 0)
                    tc_ccl = float(row.get('tc_ccl', 0) or 0)
                    result[comitente] = {
                        'tc_mep': tc_mep if tc_mep > 0 else 1150.0,
                        'tc_ccl': tc_ccl if tc_ccl > 0 else 1150.0
                    }

            return result

        except Exception as e:
            logger.warning(f"Error obteniendo TCs: {e}")
            return {}

    def clear_sheet(self, sheet_name: str) -> bool:
        """
        Borra todos los datos de una hoja específica (excepto el header).

        Args:
            sheet_name: Nombre de la hoja a limpiar

        Returns:
            True si se limpió exitosamente, False si hubo error
        """
        try:
            # Obtener el rango completo de la hoja
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A1:Z"
            ).execute()

            values = result.get('values', [])

            if len(values) <= 1:
                # Solo hay header o está vacía
                logger.info(f"Hoja {sheet_name} ya está vacía")
                return True

            # Borrar desde la fila 2 en adelante (mantener header)
            num_rows = len(values)
            clear_range = f"{sheet_name}!A2:Z{num_rows}"

            self.sheets_service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=clear_range
            ).execute()

            logger.info(f"Hoja {sheet_name} limpiada: {num_rows - 1} filas eliminadas")
            return True

        except HttpError as e:
            logger.error(f"Error limpiando hoja {sheet_name}: {e}")
            return False

    def clear_all_data(self) -> bool:
        """
        Borra todos los datos de todas las hojas de datos (mantiene headers y configuración).

        Returns:
            True si todo se limpió exitosamente
        """
        sheets_to_clear = [SHEET_HISTORIAL, SHEET_SNAPSHOTS, SHEET_CUSTOM]

        success = True
        for sheet in sheets_to_clear:
            if not self.clear_sheet(sheet):
                success = False

        return success

    # =========================================================================
    # CATEGORÍAS CUSTOM
    # =========================================================================

    def _create_custom_categories_sheet(self):
        """Crea la hoja de categorías custom si no existe."""
        try:
            requests = [{
                'addSheet': {
                    'properties': {
                        'title': SHEET_CUSTOM_CATEGORIES
                    }
                }
            }]
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={'requests': requests}
            ).execute()

            # Headers
            headers = [['nombre', 'display_name', 'color', 'exposicion', 'activo']]
            self._write_range(SHEET_CUSTOM_CATEGORIES, 'A1', headers)
            logger.info(f"Hoja {SHEET_CUSTOM_CATEGORIES} creada exitosamente")
        except HttpError as e:
            if 'already exists' in str(e):
                logger.info(f"Hoja {SHEET_CUSTOM_CATEGORIES} ya existe")
            else:
                logger.error(f"Error creando hoja de categorías: {e}")

    def get_custom_categories(self) -> list:
        """
        Obtiene lista de nombres de categorías custom.

        Returns:
            Lista de nombres de categorías
        """
        try:
            data = self._read_all(SHEET_CUSTOM_CATEGORIES)
            return [row.get('nombre') for row in data
                    if row.get('nombre') and row.get('activo', 'TRUE').upper() == 'TRUE']
        except HttpError as e:
            if 'Unable to parse range' in str(e):
                self._create_custom_categories_sheet()
                return []
            logger.warning(f"Error leyendo categorías custom: {e}")
            return []

    def get_custom_categories_full(self) -> List[Dict]:
        """
        Obtiene todas las categorías custom con sus detalles.

        Returns:
            Lista de dicts con nombre, display_name, color, exposicion
        """
        try:
            data = self._read_all(SHEET_CUSTOM_CATEGORIES)
            return [row for row in data
                    if row.get('nombre') and row.get('activo', 'TRUE').upper() == 'TRUE']
        except HttpError as e:
            if 'Unable to parse range' in str(e):
                self._create_custom_categories_sheet()
                return []
            logger.warning(f"Error leyendo categorías custom: {e}")
            return []

    def save_custom_category(self, nombre: str, display_name: str = None,
                              color: str = None, exposicion: str = "EXTERIOR") -> bool:
        """
        Guarda una categoría custom.

        Args:
            nombre: Nombre interno (ej: "BONOS_CORPORATIVOS")
            display_name: Nombre para mostrar (ej: "Bonos Corporativos")
            color: Color hex para gráficos (ej: "#FF5733")
            exposicion: "ARGENTINA" o "EXTERIOR"

        Returns:
            True si se guardó exitosamente
        """
        try:
            nombre = nombre.upper().strip().replace(" ", "_")
            display_name = display_name or nombre.replace("_", " ").title()
            color = color or "#808080"

            # Verificar si ya existe
            data = self._read_all(SHEET_CUSTOM_CATEGORIES)
            for i, row in enumerate(data):
                if row.get('nombre', '').upper().strip() == nombre:
                    # Actualizar existente
                    range_name = f"{SHEET_CUSTOM_CATEGORIES}!B{i+2}:E{i+2}"
                    self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=range_name,
                        valueInputOption='USER_ENTERED',
                        body={'values': [[display_name, color, exposicion, 'TRUE']]}
                    ).execute()
                    logger.info(f"Categoría actualizada: {nombre}")
                    return True

            # Agregar nueva
            self._append_rows(SHEET_CUSTOM_CATEGORIES,
                            [[nombre, display_name, color, exposicion, 'TRUE']])
            logger.info(f"Categoría agregada: {nombre}")
            return True

        except HttpError as e:
            if 'Unable to parse range' in str(e):
                self._create_custom_categories_sheet()
                self._append_rows(SHEET_CUSTOM_CATEGORIES,
                                [[nombre, display_name, color, exposicion, 'TRUE']])
                return True
            logger.error(f"Error guardando categoría: {e}")
            return False

    def delete_custom_category(self, nombre: str) -> bool:
        """Desactiva una categoría custom (soft delete)."""
        try:
            nombre = nombre.upper().strip()
            data = self._read_all(SHEET_CUSTOM_CATEGORIES)

            for i, row in enumerate(data):
                if row.get('nombre', '').upper().strip() == nombre:
                    # Marcar como inactiva
                    range_name = f"{SHEET_CUSTOM_CATEGORIES}!E{i+2}"
                    self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=range_name,
                        valueInputOption='USER_ENTERED',
                        body={'values': [['FALSE']]}
                    ).execute()
                    logger.info(f"Categoría desactivada: {nombre}")
                    return True

            return False
        except HttpError as e:
            logger.error(f"Error eliminando categoría: {e}")
            return False

    def get_category_color(self, categoria: str) -> str:
        """
        Obtiene el color de una categoría (base o custom).

        Args:
            categoria: Nombre de la categoría

        Returns:
            Color hex
        """
        # Primero buscar en colores base
        if categoria in CATEGORY_COLORS:
            return CATEGORY_COLORS[categoria]

        # Buscar en custom
        try:
            custom_cats = self.get_custom_categories_full()
            for cat in custom_cats:
                if cat.get('nombre') == categoria:
                    return cat.get('color', '#808080')
        except Exception:
            pass

        return '#808080'  # Default gray

    def get_available_dates(self) -> List[str]:
        """
        Obtiene lista de fechas únicas disponibles en historial.

        Returns:
            Lista de fechas ordenadas descendente
        """
        try:
            df = self.get_historial_tenencias()
            if df.empty:
                return []

            # Convertir fecha
            df['fecha'] = pd.to_numeric(df['fecha'], errors='coerce')
            df['fecha'] = pd.to_datetime(df['fecha'], origin='1899-12-30', unit='D', errors='coerce')
            df['fecha'] = df['fecha'].dt.strftime('%Y-%m-%d')

            # Obtener fechas únicas ordenadas
            fechas = sorted(df['fecha'].dropna().unique(), reverse=True)
            return list(fechas)

        except Exception as e:
            logger.warning(f"Error obteniendo fechas: {e}")
            return []

    def get_data_by_date(self, fecha: str) -> pd.DataFrame:
        """
        Obtiene datos de historial para una fecha específica.

        Args:
            fecha: Fecha en formato YYYY-MM-DD

        Returns:
            DataFrame con datos de esa fecha
        """
        try:
            df = self.get_historial_tenencias()
            if df.empty:
                return pd.DataFrame()

            # Convertir fecha
            df['fecha'] = pd.to_numeric(df['fecha'], errors='coerce')
            df['fecha'] = pd.to_datetime(df['fecha'], origin='1899-12-30', unit='D', errors='coerce')
            df['fecha_str'] = df['fecha'].dt.strftime('%Y-%m-%d')

            # Filtrar por fecha
            df_filtered = df[df['fecha_str'] == fecha].copy()

            # Convertir valores numéricos
            numeric_cols = ['valor', 'pct_cartera', 'valor_total_cartera']
            for col in numeric_cols:
                if col in df_filtered.columns:
                    df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce').fillna(0)

            return df_filtered

        except Exception as e:
            logger.warning(f"Error obteniendo datos por fecha: {e}")
            return pd.DataFrame()

    # =========================================================================
    # ACTUALIZACIÓN INMEDIATA DE CLASIFICACIÓN
    # =========================================================================

    def update_activo_classification(self, comitente: str, ticker: str,
                                      categoria: str = None, sector: str = None) -> bool:
        """
        Actualiza la clasificación de un activo en detalle_activos inmediatamente.
        Esto permite que los cambios se vean reflejados sin reprocesar el Excel.

        Args:
            comitente: Número de comitente
            ticker: Ticker del activo a actualizar
            categoria: Nueva categoría (opcional)
            sector: Nuevo sector (opcional)

        Returns:
            True si se actualizó correctamente
        """
        try:
            data = self._read_all(SHEET_DETALLE_ACTIVOS)
            if not data:
                return False

            comitente_str = str(comitente).strip()
            ticker_upper = ticker.upper().strip()
            updated = False

            for i, row in enumerate(data):
                row_comitente = str(row.get('comitente', '')).strip()
                row_ticker = row.get('ticker', '').upper().strip()

                if row_comitente == comitente_str and row_ticker == ticker_upper:
                    # Actualizar categoría si se proporciona (columna I = 9)
                    if categoria:
                        range_name = f"{SHEET_DETALLE_ACTIVOS}!I{i+2}"
                        self.sheets_service.spreadsheets().values().update(
                            spreadsheetId=self.spreadsheet_id,
                            range=range_name,
                            valueInputOption='USER_ENTERED',
                            body={'values': [[categoria]]}
                        ).execute()
                        logger.info(f"Categoría actualizada: {ticker} -> {categoria}")

                    # Actualizar sector si se proporciona (columna J = 10)
                    if sector:
                        range_name = f"{SHEET_DETALLE_ACTIVOS}!J{i+2}"
                        self.sheets_service.spreadsheets().values().update(
                            spreadsheetId=self.spreadsheet_id,
                            range=range_name,
                            valueInputOption='USER_ENTERED',
                            body={'values': [[sector]]}
                        ).execute()
                        logger.info(f"Sector actualizado: {ticker} -> {sector}")

                    updated = True

            return updated

        except HttpError as e:
            logger.error(f"Error actualizando clasificación: {e}")
            return False

    # =========================================================================
    # MAPEOS DE SECTOR
    # =========================================================================

    def _create_sector_mappings_sheet(self):
        """Crea la hoja sector_mappings si no existe."""
        try:
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={
                    'requests': [{
                        'addSheet': {
                            'properties': {'title': SHEET_SECTOR_MAPPINGS}
                        }
                    }]
                }
            ).execute()

            # Agregar headers
            self._append_rows(SHEET_SECTOR_MAPPINGS,
                            [['ticker', 'sector', 'descripcion']])
            logger.info(f"Hoja {SHEET_SECTOR_MAPPINGS} creada")

        except HttpError as e:
            if 'already exists' in str(e):
                logger.debug(f"Hoja {SHEET_SECTOR_MAPPINGS} ya existe")
            else:
                raise

    def get_custom_sector_mappings(self) -> Dict[str, str]:
        """
        Obtiene los mapeos personalizados de sector desde Google Sheets.

        Returns:
            Dict con ticker -> sector
        """
        try:
            data = self._read_all(SHEET_SECTOR_MAPPINGS)
            mappings = {}
            for row in data:
                ticker = row.get('ticker', '').upper().strip()
                sector = row.get('sector', '').upper().strip()
                if ticker and sector:
                    mappings[ticker] = sector
            return mappings

        except HttpError as e:
            if 'Unable to parse range' in str(e):
                return {}
            logger.warning(f"Error leyendo mapeos de sector: {e}")
            return {}

    def save_custom_sector_mapping(self, ticker: str, sector: str,
                                    descripcion: str = "") -> bool:
        """
        Guarda o actualiza un mapeo personalizado de sector.

        Args:
            ticker: Símbolo del activo
            sector: Sector a asignar
            descripcion: Descripción opcional

        Returns:
            True si se guardó correctamente
        """
        try:
            ticker = ticker.upper().strip()
            sector = sector.upper().strip()

            data = self._read_all(SHEET_SECTOR_MAPPINGS)

            # Buscar si ya existe
            for i, row in enumerate(data):
                if row.get('ticker', '').upper().strip() == ticker:
                    # Actualizar existente
                    range_name = f"{SHEET_SECTOR_MAPPINGS}!B{i+2}:C{i+2}"
                    self.sheets_service.spreadsheets().values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=range_name,
                        valueInputOption='USER_ENTERED',
                        body={'values': [[sector, descripcion]]}
                    ).execute()
                    logger.info(f"Mapeo de sector actualizado: {ticker} -> {sector}")
                    return True

            # Agregar nuevo
            self._append_rows(SHEET_SECTOR_MAPPINGS,
                            [[ticker, sector, descripcion]])
            logger.info(f"Mapeo de sector guardado: {ticker} -> {sector}")
            return True

        except HttpError as e:
            if 'Unable to parse range' in str(e):
                self._create_sector_mappings_sheet()
                self._append_rows(SHEET_SECTOR_MAPPINGS,
                                [[ticker, sector, descripcion]])
                return True
            logger.error(f"Error guardando mapeo de sector: {e}")
            return False

    # =========================================================================
    # PERFILES CUSTOM (Perfiles de alocación guardados por el usuario)
    # =========================================================================

    def _create_perfiles_custom_sheet(self):
        """Crea la hoja perfiles_custom si no existe."""
        try:
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={
                    'requests': [{
                        'addSheet': {
                            'properties': {'title': SHEET_PERFILES_CUSTOM}
                        }
                    }]
                }
            ).execute()

            # Agregar headers
            headers = [['nombre', 'categoria', 'objetivo_pct', 'creado_por', 'fecha_creacion']]
            self._write_range(SHEET_PERFILES_CUSTOM, 'A1', headers)
            logger.info(f"Hoja {SHEET_PERFILES_CUSTOM} creada")

        except HttpError as e:
            if 'already exists' in str(e):
                logger.debug(f"Hoja {SHEET_PERFILES_CUSTOM} ya existe")
            else:
                raise

    def get_custom_profiles(self) -> List[str]:
        """
        Obtiene lista de nombres de perfiles custom disponibles.

        Returns:
            Lista de nombres de perfiles únicos
        """
        try:
            data = self._read_all(SHEET_PERFILES_CUSTOM)
            # Obtener nombres únicos
            nombres = set()
            for row in data:
                nombre = row.get('nombre', '').strip()
                if nombre:
                    nombres.add(nombre)
            return sorted(list(nombres))

        except HttpError as e:
            if 'Unable to parse range' in str(e):
                return []
            logger.warning(f"Error leyendo perfiles custom: {e}")
            return []

    def get_custom_profile_allocation(self, nombre: str) -> Dict[str, float]:
        """
        Obtiene la alocación de un perfil custom específico.

        Args:
            nombre: Nombre del perfil

        Returns:
            Dict con {categoria: porcentaje}
        """
        try:
            data = self._read_all(SHEET_PERFILES_CUSTOM)
            allocation = {}
            nombre_lower = nombre.lower().strip()

            for row in data:
                if row.get('nombre', '').lower().strip() == nombre_lower:
                    cat = row.get('categoria', '')
                    pct = float(row.get('objetivo_pct', 0))
                    if cat:
                        allocation[cat] = pct

            return allocation

        except HttpError as e:
            if 'Unable to parse range' in str(e):
                return {}
            logger.warning(f"Error leyendo perfil custom {nombre}: {e}")
            return {}

    def save_custom_profile(self, nombre: str, allocations: Dict[str, float],
                           creado_por: str = "") -> bool:
        """
        Guarda un perfil de alocación custom.

        Args:
            nombre: Nombre del perfil (ej: "Felipe Lopez", "Perfil Agro")
            allocations: Dict con {categoria: porcentaje}
            creado_por: Nombre/ID de quien lo creó (opcional)

        Returns:
            True si se guardó correctamente
        """
        try:
            nombre = nombre.strip()
            fecha = datetime.now().strftime('%Y-%m-%d %H:%M')

            # 1. Leer datos actuales
            try:
                data = self._read_all(SHEET_PERFILES_CUSTOM)
            except HttpError:
                self._create_perfiles_custom_sheet()
                data = []

            # 2. Filtrar filas que NO son de este perfil
            other_rows = []
            nombre_lower = nombre.lower()
            for row in data:
                if row.get('nombre', '').lower().strip() != nombre_lower:
                    other_rows.append([
                        row.get('nombre', ''),
                        row.get('categoria', ''),
                        row.get('objetivo_pct', 0),
                        row.get('creado_por', ''),
                        row.get('fecha_creacion', '')
                    ])

            # 3. Crear nuevas filas para este perfil
            new_rows = []
            for cat, pct in allocations.items():
                if pct > 0:  # Solo guardar categorías con porcentaje > 0
                    new_rows.append([nombre, cat, pct, creado_por, fecha])

            # 4. Combinar y reescribir toda la hoja
            all_rows = other_rows + new_rows
            header = [['nombre', 'categoria', 'objetivo_pct', 'creado_por', 'fecha_creacion']]
            all_data = header + all_rows

            # Limpiar hoja y escribir todo
            self.sheets_service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=f"{SHEET_PERFILES_CUSTOM}!A:E"
            ).execute()

            if all_data:
                self.sheets_service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{SHEET_PERFILES_CUSTOM}!A1",
                    valueInputOption='USER_ENTERED',
                    body={'values': all_data}
                ).execute()

            logger.info(f"Perfil custom '{nombre}' guardado con {len(new_rows)} categorías")
            return True

        except HttpError as e:
            if 'Unable to parse range' in str(e):
                self._create_perfiles_custom_sheet()
                return self.save_custom_profile(nombre, allocations, creado_por)
            logger.error(f"Error guardando perfil custom: {e}")
            return False

    def delete_custom_profile(self, nombre: str) -> bool:
        """
        Elimina un perfil custom.

        Args:
            nombre: Nombre del perfil a eliminar

        Returns:
            True si se eliminó correctamente
        """
        try:
            data = self._read_all(SHEET_PERFILES_CUSTOM)
            nombre_lower = nombre.lower().strip()

            # Filtrar filas que NO son de este perfil
            remaining_rows = []
            deleted = False
            for row in data:
                if row.get('nombre', '').lower().strip() != nombre_lower:
                    remaining_rows.append([
                        row.get('nombre', ''),
                        row.get('categoria', ''),
                        row.get('objetivo_pct', 0),
                        row.get('creado_por', ''),
                        row.get('fecha_creacion', '')
                    ])
                else:
                    deleted = True

            if not deleted:
                return False

            # Reescribir la hoja
            header = [['nombre', 'categoria', 'objetivo_pct', 'creado_por', 'fecha_creacion']]
            all_data = header + remaining_rows

            self.sheets_service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=f"{SHEET_PERFILES_CUSTOM}!A:E"
            ).execute()

            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{SHEET_PERFILES_CUSTOM}!A1",
                valueInputOption='USER_ENTERED',
                body={'values': all_data}
            ).execute()

            logger.info(f"Perfil custom '{nombre}' eliminado")
            return True

        except HttpError as e:
            logger.error(f"Error eliminando perfil custom: {e}")
            return False


# Singleton para reutilizar conexión
_sheets_manager = None


def get_sheets_manager(force_new: bool = False) -> SheetsManager:
    """
    Obtiene instancia singleton del manager.

    Args:
        force_new: Si True, crea una nueva instancia ignorando el singleton.
                   Útil si hay errores de conexión SSL.
    """
    global _sheets_manager
    if _sheets_manager is None or force_new:
        _sheets_manager = SheetsManager()
        _sheets_manager.get_or_create_spreadsheet()
    return _sheets_manager


def reset_sheets_manager():
    """
    Resetea el singleton del manager.
    Útil para recuperarse de errores SSL en Streamlit.
    """
    global _sheets_manager
    _sheets_manager = None
    logger.info("SheetsManager reseteado")


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Inicializando conexión con Google Sheets...")
    manager = get_sheets_manager()

    print(f"\nSpreadsheet ID: {manager.spreadsheet_id}")
    print(f"URL: https://docs.google.com/spreadsheets/d/{manager.spreadsheet_id}")

    print("\nCarteras registradas:")
    for p in manager.get_all_portfolios():
        print(f"  - {p['comitente']}: {p['nombre']} ({p['perfil_base']})")

    print("\nAlocación objetivo para 34491:")
    alloc = manager.get_target_allocation('34491')
    for cat, pct in sorted(alloc.items(), key=lambda x: -x[1]):
        print(f"  - {cat}: {pct}%")
