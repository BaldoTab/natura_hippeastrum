# Hippeastrum App (local)

Webapp local para gestionar un programa de hibridación de *Hippeastrum*.

## Requisitos

- Python 3.11+
- SQLite

## Instalación

Desde la carpeta del proyecto:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

En Windows (PowerShell):

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Base de datos y migraciones

La aplicación usa SQLite y crea `hippeastrum.db` en la carpeta del proyecto. Para utilizar otro archivo SQLite, define `HIPPEASTRUM_DATABASE_URL` antes de arrancar la aplicación o ejecutar Alembic:

```bash
export HIPPEASTRUM_DATABASE_URL="sqlite:///./otra-base.db"
```

El arranque aplica automáticamente las migraciones pendientes con Alembic y sincroniza el catálogo científico versionado. También puedes ejecutarlas manualmente:

```bash
python -m alembic upgrade head
python -m alembic current
python -m alembic check
```

Antes de actualizar una base existente, haz una copia de seguridad. No reviertas migraciones sin una copia: `alembic downgrade` puede eliminar datos importados o estructuras creadas.

## Primera ejecución

- Se crean las tablas mediante Alembic.
- Se importa el catálogo científico desde `data/reference_catalog.json`.
- Se insertan plantas y registros de ejemplo, sin asignar genotipos clásicos inventados a partir del fenotipo.

## Arranque

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- En el PC: `http://127.0.0.1:8000/`
- En el móvil, en la misma LAN: `http://IP_LOCAL_DEL_PC:8000/`

## Referencia genética

`data/reference_catalog.json` es la fuente versionada del catálogo de loci, afirmaciones y evidencias. Al editar el catálogo:

1. Mantén la trazabilidad de cada afirmación revisada: fuente científica, localización exacta, revisor y fecha.
2. No uses homología, inferencia, expresión o correlación como prueba de causalidad, herencia o epistasis.
3. Conserva los símbolos clásicos disputados separados de los genes moleculares.
4. Incrementa la versión del catálogo cuando cambie su contenido.
5. Ejecuta las pruebas y sincroniza una copia de la base antes de aplicarla a la base de trabajo.

La aplicación valida el catálogo al cargarlo y al sincronizarlo. Los estados `Revisado` y `Aceptado` requieren evidencia científica cargada y metadatos de revisión.

## Pruebas

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Las pruebas cubren migraciones, conservación de datos legacy, validación científica, filtros y fichas de referencia, y persistencia de genotipos desde formularios.

## Backup manual rápido

Detén la aplicación y copia:

- `hippeastrum.db` (o la base configurada en `HIPPEASTRUM_DATABASE_URL`).
- `static/photos/`.
- `data/reference_catalog.json`, si has realizado cambios locales.

## Fotos y logs

- Originales: `static/photos/`
- Miniaturas: `static/thumbnails/`
- Log: `app.log`
