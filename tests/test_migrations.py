from __future__ import annotations

import datetime as dt
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from migration_utils import run_migrations


APP_DIR = Path(__file__).resolve().parents[1]
BASELINE = "2f66a81fecde"
SCHEMA = "63eac04c0e1c"


def _config(engine) -> Config:
    config = Config(str(APP_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(APP_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", engine.url.render_as_string(hide_password=False))
    return config


def test_fresh_database_upgrades_to_head(engine):
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA integrity_check")).scalar_one() == "ok"
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "b41c7d2e9a10"
        tables = set(inspect(connection).get_table_names())
        assert {"fuentes_cientificas", "afirmaciones_referencia", "afirmaciones_fuente"} <= tables
        assert {"genotipos", "genotipos_planta", "loci_referencia"} <= tables
        fenotipo_columns = {column["name"] for column in inspect(connection).get_columns("fenotipos")}
        assert "hex_color_base" in fenotipo_columns


def test_legacy_data_migrates_without_inventing_alleles(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    config = _config(engine)
    command.upgrade(config, BASELINE)
    now = dt.datetime(2026, 1, 1)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO loci_referencia (
                    codigo, nombre_completo, categoria, alelos_posibles, tipo_herencia,
                    interacciona_con, nivel_evidencia, referencia_cientifica, notas
                ) VALUES
                    ('R', 'Gen R', 'Color_estructural', NULL, 'Dominante_simple', NULL, 'Media', NULL, 'Seed'),
                    ('W', 'Gen W', 'Regulador_color', NULL, 'Epistatico_dominante', NULL, 'Media', NULL, 'Seed')
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO genes_referencia (gen, caracter_controlado, tipo_herencia, nivel_evidencia, notas)
                VALUES ('R', 'Antocianinas', 'Dominante', 'Baja', 'Seed')
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO plantas (
                    id, codigo, generacion, estado, ploidy_sospecha, ploidy_confirmado,
                    num_ejemplares_fisicos, bulbillos_separados, fecha_creacion, fecha_actualizacion
                ) VALUES (
                    1, 'HP-001', 'F0', 'Bueno', 'Desconocido', 0, 1, 0, :now, :now
                )
                """
            ),
            {"now": now},
        )
        connection.execute(
            text(
                """
                INSERT INTO genotipos (
                    id, planta_id, gen_R, gen_W, ploidy_inferida, confianza, fecha_actualizacion
                ) VALUES (1, 1, 'RR probable', 'ww', 'Desconocido', 'Baja', :date)
                """
            ),
            {"date": dt.date(2026, 1, 1)},
        )

    run_migrations(engine)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM genotipos")).scalar_one() == 1
        assert connection.execute(text("SELECT COUNT(*) FROM afirmaciones_referencia")).scalar_one() == 3
        rows = connection.execute(
            text("SELECT locus_id, alelo_1, alelo_2, genotipo_display FROM genotipos_planta ORDER BY locus_id")
        ).all()
        assert rows == [(1, "?", "?", "RR probable"), (2, "w", "w", "ww")]

    command.downgrade(config, SCHEMA)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM genotipos")).scalar_one() == 1
        assert connection.execute(text("SELECT COUNT(*) FROM afirmaciones_referencia")).scalar_one() == 0
        assert connection.execute(text("SELECT COUNT(*) FROM genotipos_planta")).scalar_one() == 0

    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM genotipos_planta")).scalar_one() == 2
        assert connection.execute(text("PRAGMA integrity_check")).scalar_one() == "ok"
    engine.dispose()
