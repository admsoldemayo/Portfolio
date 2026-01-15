"""
Script simple de autenticación con Google
"""

import os
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
]

PROJECT_ROOT = Path(__file__).parent
CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
TOKEN_FILE = PROJECT_ROOT / "token.json"

print("=" * 60)
print("AUTENTICACIÓN CON GOOGLE")
print("=" * 60)
print()

if not CREDENTIALS_FILE.exists():
    print(f"ERROR: No se encontró {CREDENTIALS_FILE}")
    exit(1)

print("Iniciando flujo de autenticación...")
print()
print("Se abrirá tu navegador en unos segundos.")
print("Si no se abre automáticamente, copiá y pegá la URL que aparezca.")
print()

flow = InstalledAppFlow.from_client_secrets_file(
    str(CREDENTIALS_FILE),
    SCOPES
)

# Esto abre el navegador automáticamente
creds = flow.run_local_server(port=0)

# Guardar token
with open(TOKEN_FILE, 'w') as token:
    token.write(creds.to_json())

print()
print("=" * 60)
print("OK - AUTENTICACION EXITOSA")
print("=" * 60)
print(f"Token guardado en: {TOKEN_FILE}")
print()
print("Ahora podes ejecutar: py src/sheets_manager.py")
print()
