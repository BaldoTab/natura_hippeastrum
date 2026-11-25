"""migrate legacy genetic data

Revision ID: b41c7d2e9a10
Revises: 63eac04c0e1c
Create Date: 2026-11-25 13:35:00.000000

"""
from __future__ import annotations

import datetime as dt

from alembic import op
from sqlalchemy import text


revision = "b41c7d2e9a10"
down_revision = "63eac04c0e1c"
branch_labels = None
depends_on = None

MIGRATION_TIME = dt.datetime(2026, 11, 25)
MOLECULAR_CODES = {"HpMYB1", "CHS", "CHI", "F3H", "DFR", "ANS", "F3pH", "HpbHLH1"}
LEGACY_GENOTYPE_COLUMNS = {
    "gen_R": "R",
    "gen_Y": "Y",
    "gen_W": "W",
    "gen_P": "P",
    "gen_D": "D",
    "gen_HpMYB1": "HpMYB1",
}


def _prepare_loci(bind) -> None:
    rows = bind.execute(text("SELECT id, codigo FROM loci_referencia")).mappings().all()
    for row in rows:
        entity = "Gen_molecular" if row["codigo"] in MOLECULAR_CODES else "Locus_clasico"
        bind.execute(
            text(
                """
                UPDATE loci_referencia
                SET tipo_entidad = :entity,
                    nombres_alternativos = COALESCE(nombres_alternativos, '[]'),
                    estado_curacion = :estado,
                    version = 1
                WHERE id = :id
                """
            ),
            {"entity": entity, "estado": "Pendiente_revision", "id": row["id"]},
        )


def _insert_claim(
    bind,
    *,
    locus_id: int,
    code: str,
    claim_type: str,
    statement: str,
    estado: str,
    limitations: str,
) -> None:
    exists = bind.execute(
        text("SELECT 1 FROM afirmaciones_referencia WHERE codigo_estable = :code"),
        {"code": code},
    ).scalar_one_or_none()
    if exists:
        return
    bind.execute(
        text(
            """
            INSERT INTO afirmaciones_referencia (
                locus_id, codigo_estable, tipo, texto, especie_alcance, contexto,
                estado, version, revisado_por, fecha_revision, notas_limitaciones,
                fecha_creacion, fecha_actualizacion
            ) VALUES (
                :locus_id, :code, :tipo, :texto, 'Hippeastrum', :contexto,
                :estado, 1, NULL, NULL, :limitaciones,
                :creado, :actualizado
            )
            """
        ),
        {
            "locus_id": locus_id,
            "code": code,
            "tipo": claim_type,
            "texto": statement,
            "contexto": "Importado del catálogo anterior a la curación por afirmaciones",
            "estado": estado,
            "limitaciones": limitations,
            "creado": MIGRATION_TIME,
            "actualizado": MIGRATION_TIME,
        },
    )


def _import_locus_claims(bind) -> None:
    rows = bind.execute(
        text(
            """
            SELECT id, codigo, nombre_completo, alelos_posibles, interacciona_con,
                   tipo_herencia, nivel_evidencia, referencia_cientifica, notas
            FROM loci_referencia
            ORDER BY id
            """
        )
    ).mappings().all()
    for row in rows:
        code = row["codigo"]
        if code in MOLECULAR_CODES:
            claim_type = "Ruta_bioquimica" if code in {"CHS", "CHI", "F3H", "DFR", "ANS", "F3pH"} else "Funcion"
        else:
            claim_type = "Asociacion_fenotipica"
        details = [
            f"Nombre heredado: {row['nombre_completo'] or code}",
            f"alelos_posibles={row['alelos_posibles'] or 'sin datos'}",
            f"interacciona_con={row['interacciona_con'] or 'sin datos'}",
            f"tipo_herencia={row['tipo_herencia'] or 'sin datos'}",
        ]
        limitations = (
            f"Evidencia legacy: {row['nivel_evidencia'] or 'sin dato'}. "
            f"Referencia legacy: {row['referencia_cientifica'] or 'sin fuente'}. "
            "Esta afirmación se conserva para revisión y no se considera validada."
        )
        _insert_claim(
            bind,
            locus_id=row["id"],
            code=f"legacy-locus-{code}",
            claim_type=claim_type,
            statement="; ".join(details),
            estado="Pendiente_revision",
            limitations=limitations,
        )


def _legacy_gene_statement(row) -> str:
    parts = [f"Carácter heredado: {row['caracter_controlado'] or 'sin dato'}"]
    if row["alelo_dominante"]:
        parts.append(f"alelo dominante={row['alelo_dominante']}")
    if row["alelo_recesivo"]:
        parts.append(f"alelo recesivo={row['alelo_recesivo']}")
    if row["tipo_herencia"]:
        parts.append(f"herencia={row['tipo_herencia']}")
    return "; ".join(parts)


def _import_gene_claims(bind) -> None:
    loci = {
        row["codigo"]: row["id"]
        for row in bind.execute(text("SELECT id, codigo FROM loci_referencia")).mappings()
    }
    rows = bind.execute(text("SELECT * FROM genes_referencia ORDER BY id")).mappings().all()
    for row in rows:
        gene = row["gen"]
        if gene == "CHS/CHI/F3H/DFR/ANS":
            codes = ["CHS", "CHI", "F3H", "DFR", "ANS"]
        else:
            codes = [gene]
        for code in codes:
            locus_id = loci.get(code)
            if locus_id is None:
                continue
            claim_type = "Funcion" if code == "HpMYB1" else "Ruta_bioquimica" if code in MOLECULAR_CODES else "Asociacion_fenotipica"
            estado = "Disputado" if code in {"D", "HpMYB1"} else "Pendiente_revision"
            statement = _legacy_gene_statement(row)
            if gene == "CHS/CHI/F3H/DFR/ANS":
                statement = f"Miembro de la ruta agregada heredada CHS/CHI/F3H/DFR/ANS. {statement}"
            limitations = (
                f"Evidencia legacy: {row['nivel_evidencia'] or 'sin dato'}. "
                f"Notas legacy: {row['notas'] or 'sin notas'}. "
                "No se ha convertido esta afirmación en una regla de predicción."
            )
            _insert_claim(
                bind,
                locus_id=locus_id,
                code=f"legacy-gen-{code}",
                claim_type=claim_type,
                statement=statement,
                estado=estado,
                limitations=limitations,
            )


def _legacy_confidence(value: str | None) -> str:
    return {
        "Confirmado_lab": "Confirmado_lab",
        "Alta": "Alta_observacion",
        "Media": "Media_inferido",
        "Baja": "Baja_visual",
    }.get(value or "", "Desconocido")


def _legacy_method(value: str | None) -> str:
    text_value = (value or "").lower()
    if "segreg" in text_value:
        return "Segregacion_F2"
    if "cruce" in text_value or "f1" in text_value:
        return "Resultado_cruce_F1"
    return "Observacion_fenotipo"


def _import_legacy_genotypes(bind) -> None:
    loci = {
        row["codigo"]: row["id"]
        for row in bind.execute(text("SELECT id, codigo FROM loci_referencia")).mappings()
    }
    rows = bind.execute(text("SELECT * FROM genotipos ORDER BY id")).mappings().all()
    for row in rows:
        for column, code in LEGACY_GENOTYPE_COLUMNS.items():
            original = row[column]
            locus_id = loci.get(code)
            if not original or locus_id is None:
                continue
            exists = bind.execute(
                text("SELECT 1 FROM genotipos_planta WHERE planta_id = :planta_id AND locus_id = :locus_id"),
                {"planta_id": row["planta_id"], "locus_id": locus_id},
            ).scalar_one_or_none()
            if exists:
                continue
            if len(original) == 2 and original[0] == original[1] and original.isalpha():
                allele_1, allele_2 = original[0], original[1]
                ambiguity_note = ""
            else:
                allele_1 = allele_2 = "?"
                ambiguity_note = " El texto ambiguo no se convirtió en alelos."
            source = f"Migración legacy genotipos.id={row['id']}"
            notes = f"Valor original conservado: {original}.{ambiguity_note}"
            if row["notas"]:
                notes += f" Notas legacy: {row['notas']}"
            bind.execute(
                text(
                    """
                    INSERT INTO genotipos_planta (
                        planta_id, locus_id, alelo_1, alelo_2, alelo_3, alelo_4,
                        genotipo_display, fenotipo_esperado, confianza, metodo_inferencia,
                        fuente_evidencia, fecha_inferencia, inferido_por_cruce_id, notas
                    ) VALUES (
                        :planta_id, :locus_id, :alelo_1, :alelo_2, NULL, NULL,
                        :display, NULL, :confianza, :metodo,
                        :fuente, :fecha, NULL, :notas
                    )
                    """
                ),
                {
                    "planta_id": row["planta_id"],
                    "locus_id": locus_id,
                    "alelo_1": allele_1,
                    "alelo_2": allele_2,
                    "display": original,
                    "confianza": _legacy_confidence(row["confianza"]),
                    "metodo": _legacy_method(row["fuente_inferencia"]),
                    "fuente": source,
                    "fecha": row["fecha_actualizacion"],
                    "notas": notes,
                },
            )


def upgrade() -> None:
    bind = op.get_bind()
    _prepare_loci(bind)
    _import_locus_claims(bind)
    _import_gene_claims(bind)
    _import_legacy_genotypes(bind)


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(text("DELETE FROM genotipos_planta WHERE fuente_evidencia LIKE 'Migración legacy genotipos.id=%'"))
    bind.execute(text("DELETE FROM afirmaciones_referencia WHERE codigo_estable LIKE 'legacy-%'"))
