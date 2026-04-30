# Hippeastrum App (local)

Webapp local para gestionar un programa de hibridación de *Hippeastrum*.

## Requisitos

- Python 3.11+

## Instalación

### Crear entorno virtual (recomendado)

Desde la carpeta `hippeastrum_app/`:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

En Windows (PowerShell):

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

```bash
pip install -r requirements.txt
```

## Primera ejecución

La primera vez:

- Se crea `hippeastrum.db` (SQLite) en la carpeta del proyecto.
- Se crean las tablas (modo desarrollo) y se insertan datos seed (genes de referencia + plantas ejemplo + CR-001 + tarea).

## Arranque

Ejecuta desde la carpeta `hippeastrum_app/`:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Luego abre:

- En el PC: `http://127.0.0.1:8000/`
- En el móvil (misma LAN): `http://IP_LOCAL_DEL_PC:8000/`

## Fotos

- Originales: `static/photos/`
- Miniaturas: `static/thumbnails/`

## Logs

- Archivo: `app.log`

## Backup manual rápido

- Copia `hippeastrum.db` y la carpeta `static/photos/`.
