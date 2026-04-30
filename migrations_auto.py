from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


# Pequeñas migraciones automáticas para SQLite en desarrollo.
# No reemplaza Alembic: evita tener que borrar la DB cuando añadimos columnas simples.

def ensure_columns(engine: Engine) -> None:
    with engine.connect() as conn:
        # Ensure core new tables exist. In production prefer Alembic.
        _ensure_tables(conn)

        cols = _table_columns(conn, "fenotipos")

        _add_col_if_missing(conn, cols, "fenotipos", "flor_doble", "BOOLEAN NOT NULL DEFAULT 0")
        _add_col_if_missing(conn, cols, "fenotipos", "longitud_flor_cm", "FLOAT")
        _add_col_if_missing(conn, cols, "fenotipos", "altura_vara_floral_cm", "FLOAT")

        conn.commit()


def _ensure_tables(conn) -> None:
    existing = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}

    if "loci_referencia" not in existing:
        conn.execute(
            text(
                """
                CREATE TABLE loci_referencia (
                    id INTEGER PRIMARY KEY,
                    codigo VARCHAR(50) NOT NULL,
                    nombre_completo VARCHAR(200),
                    categoria VARCHAR(50) NOT NULL,
                    alelos_posibles TEXT,
                    tipo_herencia VARCHAR(50) NOT NULL,
                    interacciona_con TEXT,
                    nivel_evidencia VARCHAR(50) NOT NULL,
                    pigmento_producido VARCHAR(50),
                    referencia_cientifica TEXT,
                    notas TEXT,
                    CONSTRAINT uq_loci_referencia_codigo UNIQUE (codigo)
                )
                """
            )
        )

    if "genotipos_planta" not in existing:
        conn.execute(
            text(
                """
                CREATE TABLE genotipos_planta (
                    id INTEGER PRIMARY KEY,
                    planta_id INTEGER NOT NULL,
                    locus_id INTEGER NOT NULL,
                    alelo_1 VARCHAR(50) NOT NULL DEFAULT '?',
                    alelo_2 VARCHAR(50) NOT NULL DEFAULT '?',
                    alelo_3 VARCHAR(50),
                    alelo_4 VARCHAR(50),
                    genotipo_display VARCHAR(200),
                    fenotipo_esperado TEXT,
                    confianza VARCHAR(50) NOT NULL,
                    metodo_inferencia VARCHAR(50) NOT NULL,
                    fuente_evidencia TEXT,
                    fecha_inferencia DATE,
                    inferido_por_cruce_id INTEGER,
                    notas TEXT,
                    CONSTRAINT uq_genotipos_planta_planta_locus UNIQUE (planta_id, locus_id)
                )
                """
            )
        )

    if "epistasia_observada" not in existing:
        conn.execute(
            text(
                """
                CREATE TABLE epistasia_observada (
                    id INTEGER PRIMARY KEY,
                    planta_id INTEGER NOT NULL,
                    locus_epistatico_id INTEGER NOT NULL,
                    locus_hipostatico_id INTEGER NOT NULL,
                    efecto_observado TEXT,
                    confirmado BOOLEAN NOT NULL DEFAULT 0,
                    cruce_confirmacion_id INTEGER,
                    notas TEXT
                )
                """
            )
        )


def _table_columns(conn, table: str) -> set[str]:
    res = conn.execute(text(f"PRAGMA table_info({table})"))
    return {row[1] for row in res.fetchall()}


def _add_col_if_missing(conn, cols: set[str], table: str, col: str, ddl_type: str) -> None:
    if col in cols:
        return
    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl_type}"))
