# Guía de Guardado en Google Sheets

## 🎯 ¿Cómo funciona el guardado automático?

El sistema está configurado para **guardar automáticamente** todos los archivos Excel que subas en Google Sheets, funcionando como una base de datos completa.

---

## 📋 Flujo Paso a Paso

### 1. **Subir Archivo Excel**

En la página principal (http://localhost:8501):
- Arrastra o selecciona archivos Excel (.xlsx, .xls)
- El checkbox **"💾 Guardar automáticamente en Google Sheets"** debe estar **ACTIVADO** (viene activado por defecto)

### 2. **Procesamiento Automático**

El sistema ejecuta automáticamente:

```
Excel → Extraer Metadata → Clasificar Activos → Guardar en Sheets
```

**a) Extracción de Metadata** (`filename_parser.py`)
- Del nombre del archivo extrae:
  - **Comitente**: ej. 34491
  - **Nombre**: ej. LOPEZ JUAN ANTONIO
  - **Fecha**: ej. 2026-01-10

**Formato esperado del archivo:**
```
Tenencias-{comitente}_{NOMBRE}-{YYYY-MM-DD}.xlsx
```

**Ejemplos válidos:**
```
Tenencias-34491_LOPEZ_JUAN ANTONIO-2026-01-10.xlsx
Tenencias-243999_Lopez Rojas Felipe-2026-01-13.xlsx
Tenencias-34462_LOPEZ_ROJAS_PEDRO-2026-01-13 (1).xlsx  ← Acepta duplicados (1), (2), etc.
```

**b) Clasificación de Activos** (`asset_mapper.py`)
- Cada ticker se clasifica en una de 11 categorías:
  - SPY (USA/Tech)
  - MERV (Argentina)
  - LETRAS (Renta Fija)
  - GLD (Oro)
  - SLV (Plata)
  - CRYPTO_BTC
  - CRYPTO_ETH
  - BRASIL
  - EXTRAS_COBRE
  - LIQUIDEZ
  - OTROS (sin clasificar)

**c) Guardado en Google Sheets** (`save_to_sheets()` en `ingest.py`)

Se guardan **DOS tipos de registros**:

#### 📊 Hoja: `historial_tenencias`
Guarda el **detalle completo** por categoría:

| fecha | comitente | nombre | categoria | valor | valor_total_cartera |
|-------|-----------|--------|-----------|-------|---------------------|
| 2026-01-10 | 34491 | LOPEZ JUAN ANTONIO | SPY | 350000 | 880000 |
| 2026-01-10 | 34491 | LOPEZ JUAN ANTONIO | MERV | 200000 | 880000 |
| 2026-01-10 | 34491 | LOPEZ JUAN ANTONIO | GLD | 150000 | 880000 |
| ... | ... | ... | ... | ... | ... |

#### 📈 Hoja: `snapshots_totales`
Guarda el **resumen** con valor total:

| fecha | comitente | nombre | valor_total | variacion_vs_anterior_pct |
|-------|-----------|--------|-------------|---------------------------|
| 2026-01-10 | 34491 | LOPEZ JUAN ANTONIO | 880000 | +2.5 |

La **variación** se calcula automáticamente comparando con el snapshot anterior de ese mismo cliente.

### 3. **Confirmación Visual**

Después de procesar, verás:

✅ **Mensaje de éxito:**
```
✅ Todos los snapshots guardados exitosamente: 1 cartera(s)
```

📊 **Tabla de detalles:**
| Comitente | Nombre | Estado | Detalle |
|-----------|--------|--------|---------|
| 34491 | LOPEZ JUAN ANTONIO | ✅ Guardado | Variación: +2.5% |

🔗 **Link directo a Google Sheets:**
```
📊 Ver datos en Google Sheets
```

---

## ✅ Verificar que se Guardó Correctamente

### Opción 1: Desde el Portal

1. Ir a **"Portfolio Individual"**
2. Seleccionar el cliente del dropdown
3. Si se guardó correctamente:
   - ✅ Verás el análisis de alocación
   - ✅ Gráficos comparativos
   - ✅ Sugerencias de rebalanceo

4. Ir a **"Historial"**
5. Seleccionar el cliente
6. Si se guardó correctamente:
   - ✅ Verás la evolución temporal
   - ✅ Gráfico de valor total
   - ✅ Tabla de snapshots

### Opción 2: Desde Google Sheets

1. Abrí el link que aparece después de guardar
2. O ve directamente a:
   ```
   https://docs.google.com/spreadsheets/d/1lxCrSAdkPgJ6BBIzS02H3TMwcGOeb7L85C-WbVzH76Y
   ```
3. Verifica las hojas:
   - **historial_tenencias**: debe tener filas nuevas con la fecha de hoy
   - **snapshots_totales**: debe tener un registro por cada cliente procesado

### Opción 3: Página de Administración

1. Ir a **"Administración"** (nueva página)
2. Ver sección **"Estado del Sistema"**:
   - **Registros en historial_tenencias**: debe aumentar
   - **Snapshots totales**: debe aumentar
   - **Fecha más reciente**: debe ser la de hoy

3. Ver sección **"Últimos Registros Guardados"**:
   - Debe aparecer el snapshot recién guardado

---

## 🔧 Herramientas de Administración

En la nueva página **"Administración"** encontrarás:

### 🧪 Simular Datos
Genera datos de prueba automáticamente:
- 10 snapshots por cada una de las 8 carteras
- Datos de los últimos 30 días
- Valores aleatorios según el perfil de cada cliente

**Útil para:**
- Testing del sistema
- Ver cómo se ven los gráficos con datos históricos
- Probar funcionalidad sin tener archivos Excel reales

### 🗑️ Borrar Datos
**⚠️ PRECAUCIÓN:** Elimina TODOS los datos de:
- historial_tenencias
- snapshots_totales
- alocacion_custom

**Cómo usarlo:**
1. Marcar el checkbox "Confirmo que quiero borrar todos los datos"
2. Click en "BORRAR TODOS LOS DATOS"
3. Los headers se mantienen, solo se borran los registros

**Útil para:**
- Limpiar datos de prueba
- Empezar de cero
- Testing

### 🔄 Refrescar Datos
Recarga las estadísticas para ver el estado actualizado del sistema.

### 🐛 Herramientas de Debug
Expander que muestra el contenido RAW de todas las hojas de Google Sheets.

**Útil para:**
- Ver exactamente qué hay en cada hoja
- Debuggear problemas
- Verificar que los datos se guardaron correctamente

---

## ❌ Problemas Comunes

### No se guardan los datos

**Síntoma:** Checkbox activado pero no aparece mensaje de éxito

**Causas posibles:**

1. **Nombre de archivo incorrecto**
   - ❌ `portfolio-juan.xlsx`
   - ❌ `Tenencias-JUAN-2026.xlsx`
   - ✅ `Tenencias-34491_LOPEZ_JUAN ANTONIO-2026-01-10.xlsx`

2. **Comitente no reconocido**
   - El comitente debe estar en `config.py` en `KNOWN_PORTFOLIOS`
   - Si es un cliente nuevo, agregarlo primero

3. **Error de autenticación**
   - Ver mensaje de error detallado
   - Si dice "invalid_scope", ejecutar: `python authenticate.py`

4. **Archivo sin metadata**
   - Verificar que el nombre tenga el formato correcto
   - Ver el expander "Ver detalles del guardado" para más info

### Se guarda pero no aparece en Portfolio Individual

**Causa:** Necesitas refrescar la página

**Solución:**
- Presiona F5 o Ctrl+R
- O navega a otra página y vuelve

### Aparece "No hay datos históricos para el comitente X"

**Causa:** El snapshot se guardó pero todavía no se sincronizó

**Solución:**
1. Ir a **Administración**
2. Ver "Últimos Registros Guardados"
3. Verificar que aparece el comitente
4. Volver a Portfolio Individual y refrescar

---

## 🎯 Resumen del Flujo Completo

```
1. Usuario sube Excel
   ↓
2. Sistema extrae metadata del filename
   ↓
3. Sistema clasifica activos en categorías
   ↓
4. Sistema guarda en Google Sheets:
   - historial_tenencias (detalle por categoría)
   - snapshots_totales (resumen con valor total)
   ↓
5. Usuario ve confirmación visual
   ↓
6. Usuario puede:
   - Ver análisis en Portfolio Individual
   - Ver evolución en Historial
   - Verificar en Google Sheets directamente
   - Ver registros en Administración
```

---

## 📊 Google Sheets como Base de Datos

Google Sheets funciona como la **base de datos central** del sistema:

✅ **Ventajas:**
- Accesible desde cualquier lugar
- Editable manualmente si hace falta
- Backup automático de Google
- Historial de cambios
- Compartible con el equipo

✅ **Estructura:**
- **5 hojas** con propósitos específicos
- **Headers fijos** que no se borran
- **Datos ordenados** por fecha y comitente
- **Validación automática** de perfiles y carteras

✅ **Sincronización:**
- Cada vez que subís un Excel → se guarda en Sheets
- El portal lee de Sheets → siempre datos actualizados
- Múltiples usuarios pueden ver los mismos datos

---

## 🚀 Mejores Prácticas

1. **Mantener formato de nombre de archivo:**
   - Usar siempre el formato `Tenencias-{comitente}_{NOMBRE}-{YYYY-MM-DD}.xlsx`
   - Evita caracteres especiales raros

2. **Subir archivos regularmente:**
   - Mensual, quincenal, o cuando recibas nuevos reportes
   - Esto construye el historial para análisis de rentabilidad

3. **Verificar después de subir:**
   - Chequear el mensaje de confirmación
   - Ver que el comitente aparece en la lista

4. **Hacer backup de Google Sheets:**
   - Google lo hace automáticamente
   - Pero podés hacer copias manuales: File > Make a copy

5. **Usar Administración para testing:**
   - Generar datos simulados para probar
   - Limpiar cuando termines de testear

---

**Última actualización:** 2026-01-12
