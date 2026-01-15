# Portfolio Automation System - Sol de Mayo

Sistema automatizado de gestión y análisis de carteras de inversión para múltiples clientes.

## 🎯 Características

- **Procesamiento Automático**: Lee archivos Excel de brokers (IOL, StoneX, PPI, Balanz)
- **Clasificación Inteligente**: Clasifica 200+ activos en 11 categorías
- **Perfiles de Alocación**: Define objetivos personalizados por cliente
- **Análisis de Desviaciones**: Compara alocación actual vs objetivo
- **Sugerencias de Rebalanceo**: Calcula montos específicos para ajustar la cartera
- **Historial Completo**: Almacena evolución temporal en Google Sheets
- **Análisis de Rentabilidad**: Calcula retornos totales y por categoría
- **Interfaz Web**: Dashboard interactivo con Streamlit

## 📁 Estructura del Proyecto

```
portfolio-automation/
├── src/                          # Código fuente
│   ├── asset_mapper.py           # Clasificación de activos
│   ├── filename_parser.py        # Extracción de metadata
│   ├── ingest.py                 # Pipeline de procesamiento
│   ├── sheets_manager.py         # Integración con Google Sheets
│   ├── allocation_manager.py     # Comparación actual vs objetivo
│   ├── portfolio_tracker.py      # Historial y rentabilidad
│   └── config.py                 # Configuración centralizada
│
├── pages/                        # Páginas de Streamlit
│   ├── 1_Portfolio_Individual.py # Análisis por cliente
│   ├── 2_Historial.py           # Evolución temporal
│   └── 3_Configuracion.py       # Edición de perfiles
│
├── app.py                        # Interfaz web principal
├── authenticate.py               # Script de autenticación
│
├── data/                         # Datos locales
│   ├── input/                   # Archivos Excel de entrada
│   ├── output/                  # CSVs procesados
│   └── history/                 # Histórico local
│
├── logs/                         # Logs del sistema
├── credentials.json              # OAuth credentials (Google Cloud)
├── token.json                    # Token de autenticación (generado)
└── README.md                     # Este archivo
```

## 🚀 Instalación

### 1. Requisitos Previos

- Python 3.8 o superior
- Cuenta de Google con acceso a Google Sheets API
- Credenciales OAuth 2.0 de Google Cloud Platform

### 2. Instalar Dependencias

```bash
pip install pandas openpyxl google-auth google-auth-oauthlib google-api-python-client streamlit plotly
```

O instalar desde requirements.txt (si existe):

```bash
pip install -r requirements.txt
```

### 3. Configurar Google Sheets

#### Crear Proyecto en Google Cloud Console

1. Ir a [Google Cloud Console](https://console.cloud.google.com/)
2. Crear un nuevo proyecto (ej: "Portfolio Tracker")
3. Habilitar APIs:
   - Google Sheets API
   - Google Drive API

#### Crear Credenciales OAuth 2.0

1. En el proyecto, ir a **APIs y servicios > Credenciales**
2. Crear credenciales > **ID de cliente de OAuth 2.0**
3. Tipo de aplicación: **Aplicación de escritorio**
4. Descargar el JSON de credenciales
5. Guardar como `credentials.json` en la raíz del proyecto

#### Autenticar la Primera Vez

```bash
cd portfolio-automation
python authenticate.py
```

Esto abrirá un navegador para autorizar el acceso. Tras completar:
- Se genera `token.json` (no compartir ni versionar)
- El sistema puede acceder a Google Sheets automáticamente

### 4. Verificar Configuración

Abrir `src/config.py` y verificar:

```python
SPREADSHEET_ID = "1lxCrSAdkPgJ6BBIzS02H3TMwcGOeb7L85C-WbVzH76Y"
```

Este es el ID del Google Sheets donde se almacenan los datos.

## 📊 Uso del Sistema

### Opción 1: Interfaz Web (Recomendado)

```bash
streamlit run app.py
```

Esto abre un navegador con la interfaz completa:

#### **Página Principal (Dashboard)**
- Subir archivos Excel de brokers
- Ver clasificación automática de activos
- Opción de guardar snapshots en Google Sheets
- Resumen consolidado de todas las carteras

#### **Portfolio Individual**
- Seleccionar cliente específico
- Ver alocación actual vs objetivo
- Gráficos comparativos (barras, pie charts)
- Tabla de desviaciones por categoría
- Sugerencias de rebalanceo (montos específicos)

#### **Historial**
- Ver evolución temporal del valor total
- Calcular rentabilidad por periodo (YTD, MTD, 1M, 3M, 6M, 1Y)
- Rentabilidad por categoría
- Comparar múltiples snapshots

#### **Configuración**
- Editar perfiles base (conservador, moderado, agresivo)
- Definir overrides custom por cliente
- Ver carteras configuradas
- Verificar conexión con Google Sheets

### Opción 2: Línea de Comandos

#### Procesar un archivo específico

```bash
cd src
python ingest.py "../data/input/Tenencias-34491_LOPEZ_JUAN ANTONIO-2026-01-10.xlsx"
```

#### Procesar todos los archivos en `data/input/`

```bash
cd src
python ingest.py
```

Esto genera:
- `data/output/portfolio_master.csv` (última versión)
- `data/history/portfolio_YYYYMMDD_HHMMSS.csv` (copia histórica)
- Guarda snapshots en Google Sheets automáticamente

### Opción 3: Usar Módulos en Python

```python
from ingest import process_single_file
from allocation_manager import AllocationManager
from portfolio_tracker import PortfolioTracker

# Procesar archivo
df = process_single_file("path/to/tenencias.xlsx")

# Analizar alocación
manager = AllocationManager()
target, comparison, suggestions = manager.analyze_portfolio(df, comitente='34491')

# Calcular rentabilidad
tracker = PortfolioTracker()
returns = tracker.calculate_returns(comitente='34491')
```

## 🏷️ Categorías de Activos

El sistema clasifica automáticamente en 11 categorías:

| Categoría | Descripción | Ejemplos |
|-----------|-------------|----------|
| **SPY** | USA/Tech | SPY, QQQ, NVDA, AAPL, MSFT, GOOGL |
| **MERV** | Argentina | YPFD, GGAL, PAMP, ALUA, CRES |
| **LETRAS** | Renta Fija | AL30, GD30, LECAPs, ONs, cheques |
| **GLD** | Oro | GLD, Barrick (B), IAU |
| **SLV** | Plata | SLV |
| **CRYPTO_BTC** | Bitcoin | IBIT, FBTC, BTC |
| **CRYPTO_ETH** | Ethereum | EETH, ETH |
| **BRASIL** | Brasil | EWZ |
| **EXTRAS_COBRE** | Commodities | COPX (cobre), URA (uranio) |
| **LIQUIDEZ** | Efectivo | USD, ARS, USD.C, FCIs money market |
| **OTROS** | Sin clasificar | Revisar manualmente |

### Agregar Nuevos Tickers

Editar `src/asset_mapper.py`:

```python
ASSET_CATEGORIES = {
    # ...
    "NUEVO_TICKER": "SPY",  # Agregar aquí
}
```

## 👥 Carteras Configuradas

| Comitente | Nombre | Perfil |
|-----------|--------|--------|
| 34462 | LOPEZ ROJAS PEDRO | Moderado |
| 34469 | LOPEZ ROJAS JUAN IGNACIO | Agresivo |
| 243999 | Lopez Rojas Felipe | Agresivo |
| 242928 | Lopez Rojas Manuela | Conservador |
| 34489 | ROJAS CLARIA MARIANA | Moderado |
| 34491 | LOPEZ JUAN ANTONIO | Agresivo |
| 247585 | SOL DE MAYO SA | Moderado |
| 247262 | SANTO DOMINGO SRL | Moderado |

### Perfiles de Alocación

#### Conservador
- LIQUIDEZ: 40%
- LETRAS: 35%
- GLD: 15%
- SPY: 10%

#### Moderado
- SPY: 25%
- LETRAS: 25%
- MERV: 20%
- GLD: 15%
- LIQUIDEZ: 15%

#### Agresivo
- SPY: 35%
- MERV: 25%
- CRYPTO_BTC: 15%
- GLD: 10%
- LETRAS: 10%
- LIQUIDEZ: 5%

## 📈 Flujo de Trabajo Típico

### 1. Recibir Archivos por WhatsApp

Los archivos deben tener este formato de nombre:

```
Tenencias-{comitente}_{NOMBRE}-{YYYY-MM-DD}.xlsx
```

Ejemplo:
```
Tenencias-34491_LOPEZ_JUAN ANTONIO-2026-01-10.xlsx
```

### 2. Procesar Archivos

Subir a la interfaz web o copiar a `data/input/` y ejecutar:

```bash
cd src
python ingest.py
```

### 3. Verificar Clasificación

- Revisar la sección "ACTIVOS SIN CLASIFICAR" en el output
- Si hay activos en categoría "OTROS", agregar reglas en `asset_mapper.py`

### 4. Análisis

- **Portfolio Individual**: Ver desviaciones vs objetivo
- **Historial**: Analizar rentabilidad periodo a periodo
- **Configuración**: Ajustar perfiles si es necesario

## 🔧 Configuración Avanzada

### Cambiar Tolerancia de Desviación

En `src/allocation_manager.py` línea 82:

```python
if abs(desviacion) <= 5:  # Tolerancia de 5 puntos porcentuales
    status = "OK"
```

### Personalizar Colores de Categorías

En `src/config.py`:

```python
CATEGORY_COLORS = {
    "SPY": "#3366CC",
    "MERV": "#109618",
    # ... editar aquí
}
```

### Agregar Nueva Cartera

En `src/config.py`:

```python
KNOWN_PORTFOLIOS = {
    # ...
    "999999": {"nombre": "NUEVO CLIENTE", "perfil": "moderado"},
}
```

## 📊 Google Sheets - Estructura

El sistema utiliza 5 hojas en un único spreadsheet:

### 1. carteras_maestro
Registro de carteras y perfiles asignados.

| comitente | nombre | perfil_base | activo |
|-----------|--------|-------------|--------|
| 34491 | LOPEZ JUAN ANTONIO | agresivo | TRUE |

### 2. perfiles_alocacion
Definición de perfiles base.

| perfil | categoria | porcentaje |
|--------|-----------|------------|
| agresivo | SPY | 35 |
| agresivo | MERV | 25 |

### 3. alocacion_custom
Overrides personalizados por cliente (opcional).

| comitente | categoria | porcentaje_custom |
|-----------|-----------|-------------------|
| 34491 | SPY | 40 |

### 4. historial_tenencias
Histórico detallado por categoría.

| fecha | comitente | nombre | categoria | valor | valor_total_cartera |
|-------|-----------|--------|-----------|-------|---------------------|
| 2026-01-10 | 34491 | LOPEZ JUAN ANTONIO | SPY | 500000 | 880000 |

### 5. snapshots_totales
Evolución del valor total por cliente.

| fecha | comitente | nombre | valor_total | variacion_vs_anterior_pct |
|-------|-----------|--------|-------------|---------------------------|
| 2026-01-10 | 34491 | LOPEZ JUAN ANTONIO | 880000 | +2.5 |

## ⚠️ Troubleshooting

### Error: "invalid_scope"

**Causa**: Token existente tiene scopes diferentes.

**Solución**:
```bash
# Eliminar token y volver a autenticar
rm token.json
python authenticate.py
```

### Error: "Google Sheets API has not been used"

**Causa**: API no habilitada en Google Cloud.

**Solución**:
1. Ir a [Google Cloud Console](https://console.cloud.google.com/)
2. Habilitar **Google Sheets API** y **Google Drive API**

### Activos No Clasificados

Si aparecen muchos activos en categoría "OTROS":

1. Revisar el output para ver qué tickers no se reconocen
2. Editar `src/asset_mapper.py` y agregar los tickers
3. Volver a procesar los archivos

### Desviaciones No Calculadas

Si no aparecen comparaciones:

1. Verificar que el comitente esté en `KNOWN_PORTFOLIOS` (config.py)
2. Verificar que exista el perfil en `perfiles_alocacion` (Google Sheets)
3. Ejecutar tests: `python src/allocation_manager.py`

## 🔐 Seguridad

- ❌ **NO versionar** `credentials.json` ni `token.json` en Git
- ❌ **NO compartir** el `SPREADSHEET_ID` públicamente
- ✅ Mantener credenciales en carpeta local protegida
- ✅ Usar `.gitignore` para excluir archivos sensibles

```gitignore
credentials.json
token.json
*.log
data/input/*.xlsx
data/output/*.csv
```

## 📝 Mantenimiento

### Backup de Google Sheets

Recomendado: hacer copias periódicas del spreadsheet.

```
File > Make a copy > "Portfolio Tracker - Backup YYYY-MM-DD"
```

### Logs

Los logs se guardan automáticamente en `logs/`:

```bash
tail -f logs/portfolio_YYYYMMDD.log
```

### Testing

Cada módulo tiene tests integrados:

```bash
cd src
python asset_mapper.py       # Test clasificación
python allocation_manager.py # Test comparaciones
python portfolio_tracker.py  # Test historial
```

## 🚀 Próximas Mejoras

- [ ] Alertas automáticas por email cuando desviación > 10%
- [ ] Integración con APIs de precios en tiempo real
- [ ] Exportar reportes PDF personalizados
- [ ] Dashboard consolidado multi-familia
- [ ] Benchmark contra índices (S&P500, Merval, etc.)

## 📞 Soporte

Para consultas o problemas, contactar:
- Email: flopez@soldemayosa.com
- Sistema desarrollado para Sol de Mayo

---

**Portfolio Automation System v1.0**
Última actualización: 2026-01-12
