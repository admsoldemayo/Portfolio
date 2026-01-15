# Solución de Errores Comunes

## 🔧 Cambios Aplicados

### ✅ Problema 1: Formato de Números Incorrecto

**Síntoma:** Los números aparecían sin separadores: `786793740`

**Solución:** Actualicé la función `format_currency` en todas las páginas para usar formato argentino:
- **Separador de miles:** punto (.)
- **Decimales:** coma (,)

**Resultado:** Ahora los números se ven como `$786.793.740` o `$786,79M`

---

### ✅ Problema 2: Error de Autenticación Google Sheets

**Síntoma:** `google.auth.exceptions.RefreshError: ('invalid_scope: Bad Request'...)`

**Causa:** El token.json tenía scopes diferentes a los del código

**Solución:**
1. Eliminé el token.json antiguo
2. Actualicé los scopes en `sheets_manager.py` de `drive` a `drive.file`
3. Regeneré el token con los scopes correctos

**Acción requerida:**
Necesitás completar la autenticación una vez. Para esto:

```bash
cd C:\Users\felip\OneDrive\Desktop\claude.md\portfolio-automation
python authenticate.py
```

Esto va a:
1. Abrir tu navegador
2. Pedirte que selecciones la cuenta **flopez@soldemayosa.com**
3. Autorizar permisos de Google Sheets y Drive
4. Guardar el token nuevo

**Una sola vez** y nunca más va a pedir autenticación.

---

### ✅ Problema 3: No Guarda Datos en Google Sheets

**Causa:** Error de autenticación impedía acceso

**Solución:** Al resolver el problema de autenticación, el guardado automático va a funcionar

---

## 🚀 Cómo Iniciar el Portal Ahora

### Opción 1: Script Automático (Recomendado)

Hacé doble clic en:
```
INICIO_RAPIDO.bat
```

Este script:
- Verifica que tengas autenticación
- Si no, te guía para autenticar
- Inicia el portal automáticamente

### Opción 2: Manual

```bash
cd C:\Users\felip\OneDrive\Desktop\claude.md\portfolio-automation

# Si no tenés token.json, autenticar primero:
python authenticate.py

# Iniciar portal:
python -m streamlit run app.py
```

---

## 📊 Verificar que Todo Funciona

1. Abrí http://localhost:8501
2. Subí un archivo Excel de broker
3. Verificá que:
   - ✅ Los números se ven con formato correcto ($123.456.789)
   - ✅ El checkbox "Guardar automáticamente en Google Sheets" esté activado
   - ✅ Aparezca el mensaje "✅ Snapshots guardados: X carteras"
   - ✅ En "Portfolio Individual" se vean los datos
   - ✅ En "Historial" aparezcan las carteras

---

## 🔍 Si Todavía Hay Errores

### Error: "invalid_scope"

**Solución:**
```bash
cd C:\Users\felip\OneDrive\Desktop\claude.md\portfolio-automation
del token.json
python authenticate.py
```

### Error: "Spreadsheet not found"

**Verificar:** El SPREADSHEET_ID en `src/config.py` debe ser:
```python
SPREADSHEET_ID = "1lxCrSAdkPgJ6BBIzS02H3TMwcGOeb7L85C-WbVzH76Y"
```

### Error: "Module not found"

**Instalar dependencias:**
```bash
pip install streamlit plotly pandas openpyxl google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

---

## 📞 Estado Actual

- ✅ Formato de números: CORREGIDO
- ⏳ Autenticación: ESPERANDO CONFIRMACIÓN DEL USUARIO
- ⏳ Guardado en Sheets: SE ACTIVARÁ AL COMPLETAR AUTENTICACIÓN

---

**Última actualización:** 2026-01-12 16:15
