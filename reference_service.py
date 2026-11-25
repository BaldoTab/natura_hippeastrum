from __future__ import annotations

import datetime as dt
import enum
import json
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models import (
    AfirmacionFuente,
    AfirmacionReferencia,
    CategoriaLocusEnum,
    EstadoCuracionEnum,
    FuerzaEvidenciaEnum,
    FuenteCientifica,
    LocusReferencia,
    MetodoEvidenciaEnum,
    NivelEvidenciaEnum,
    RelacionFuenteEnum,
    TipoAfirmacionEnum,
    TipoEntidadLocusEnum,
    TipoFuenteEnum,
    TipoHerenciaEnum,
)


SOURCE_FIELDS = (
    "tipo",
    "autores",
    "titulo",
    "publicacion",
    "anio",
    "volumen",
    "numero",
    "paginas",
    "doi",
    "pmid",
    "url",
    "accession",
    "fecha_consulta",
    "notas",
)
CLAIM_FIELDS = (
    "tipo",
    "texto",
    "especie_alcance",
    "contexto",
    "estado",
    "revisado_por",
    "fecha_revision",
    "notas_limitaciones",
)
EVIDENCE_FIELDS = (
    "metodo_evidencia",
    "fuerza",
    "relacion",
    "localizacion_fuente",
    "cita_textual",
    "limitaciones",
)
PHENOTYPE_CLAIMS = {
    TipoAfirmacionEnum.Efecto_alelo.value,
    TipoAfirmacionEnum.Herencia.value,
    TipoAfirmacionEnum.Epistasis.value,
    TipoAfirmacionEnum.Asociacion_fenotipica.value,
}
REVIEWED_STATES = {
    EstadoCuracionEnum.Revisado.value,
    EstadoCuracionEnum.Aceptado.value,
}


def _json_value(value):
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    return value


def _date(value: str, label: str, errors: list[str]) -> dt.date | None:
    try:
        return dt.date.fromisoformat(value)
    except (TypeError, ValueError):
        errors.append(f"{label}: fecha ISO inválida")
        return None


def _enum(enum_type, value, label: str, errors: list[str]):
    try:
        return enum_type(value)
    except ValueError:
        errors.append(f"{label}: valor no permitido {value!r}")
        return None


def validate_reference_catalog(data: dict) -> None:
    errors: list[str] = []
    if not isinstance(data, dict):
        raise ValueError("El catálogo debe ser un objeto JSON")
    if not isinstance(data.get("version"), int) or data["version"] < 1:
        errors.append("version: debe ser un entero positivo")
    reviewed_at = data.get("revisado_el")
    if reviewed_at:
        _date(reviewed_at, "revisado_el", errors)

    sources: dict[str, dict] = {}
    for index, source in enumerate(data.get("fuentes", [])):
        label = f"fuentes[{index}]"
        key = source.get("clave")
        if not key:
            errors.append(f"{label}.clave: obligatorio")
            continue
        if key in sources:
            errors.append(f"{label}.clave: duplicado {key!r}")
        sources[key] = source
        _enum(TipoFuenteEnum, source.get("tipo"), f"{label}.tipo", errors)
        if not source.get("titulo"):
            errors.append(f"{label}.titulo: obligatorio")
        normalized_key = "".join(
            character
            for character in unicodedata.normalize("NFD", str(key).strip().lower())
            if unicodedata.category(character) != "Mn"
        )
        if normalized_key in {"homologia", "inferido", "seed"}:
            errors.append(f"{label}.clave: no es una referencia científica")
        source_type = source.get("tipo")
        if source_type != TipoFuenteEnum.Observacion_local.value and not any(
            source.get(field) for field in ("doi", "pmid", "url", "accession")
        ):
            errors.append(f"{label}: falta DOI, PMID, URL o accession")
        if source.get("url"):
            parsed = urlparse(source["url"])
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                errors.append(f"{label}.url: debe ser HTTP(S) válida")
            if not source.get("fecha_consulta"):
                errors.append(f"{label}.fecha_consulta: obligatoria cuando hay URL")
        if source.get("fecha_consulta"):
            _date(source["fecha_consulta"], f"{label}.fecha_consulta", errors)

    loci_codes: set[str] = set()
    claim_codes: set[str] = set()
    for locus_index, locus in enumerate(data.get("loci", [])):
        locus_label = f"loci[{locus_index}]"
        code = locus.get("codigo")
        if not code:
            errors.append(f"{locus_label}.codigo: obligatorio")
            continue
        if code in loci_codes:
            errors.append(f"{locus_label}.codigo: duplicado {code!r}")
        loci_codes.add(code)
        _enum(CategoriaLocusEnum, locus.get("categoria"), f"{locus_label}.categoria", errors)
        _enum(TipoEntidadLocusEnum, locus.get("tipo_entidad"), f"{locus_label}.tipo_entidad", errors)
        _enum(EstadoCuracionEnum, locus.get("estado_curacion"), f"{locus_label}.estado_curacion", errors)
        if not locus.get("nombre_completo"):
            errors.append(f"{locus_label}.nombre_completo: obligatorio")
        if not locus.get("especie_alcance"):
            errors.append(f"{locus_label}.especie_alcance: obligatorio")
        if not isinstance(locus.get("nombres_alternativos", []), list):
            errors.append(f"{locus_label}.nombres_alternativos: debe ser una lista")
        accepted_claims = 0
        reviewed_claims = 0

        for claim_index, claim in enumerate(locus.get("afirmaciones", [])):
            claim_label = f"{locus_label}.afirmaciones[{claim_index}]"
            claim_code = claim.get("codigo_estable")
            if not claim_code:
                errors.append(f"{claim_label}.codigo_estable: obligatorio")
                continue
            if claim_code in claim_codes:
                errors.append(f"{claim_label}.codigo_estable: duplicado {claim_code!r}")
            claim_codes.add(claim_code)
            _enum(TipoAfirmacionEnum, claim.get("tipo"), f"{claim_label}.tipo", errors)
            _enum(EstadoCuracionEnum, claim.get("estado"), f"{claim_label}.estado", errors)
            if not claim.get("texto"):
                errors.append(f"{claim_label}.texto: obligatorio")
            if not claim.get("especie_alcance"):
                errors.append(f"{claim_label}.especie_alcance: obligatorio")

            evidences = claim.get("evidencias", [])
            supporting: list[dict] = []
            for evidence_index, evidence in enumerate(evidences):
                evidence_label = f"{claim_label}.evidencias[{evidence_index}]"
                source_key = evidence.get("fuente")
                if source_key not in sources:
                    errors.append(f"{evidence_label}.fuente: no existe {source_key!r}")
                _enum(MetodoEvidenciaEnum, evidence.get("metodo_evidencia"), f"{evidence_label}.metodo_evidencia", errors)
                _enum(FuerzaEvidenciaEnum, evidence.get("fuerza"), f"{evidence_label}.fuerza", errors)
                _enum(RelacionFuenteEnum, evidence.get("relacion"), f"{evidence_label}.relacion", errors)
                if evidence.get("relacion") == RelacionFuenteEnum.Apoya.value:
                    supporting.append(evidence)

            if claim.get("estado") in REVIEWED_STATES:
                reviewed_claims += 1
            if claim.get("estado") == EstadoCuracionEnum.Aceptado.value:
                accepted_claims += 1
            if claim.get("estado") in REVIEWED_STATES:
                if not claim.get("revisado_por"):
                    errors.append(f"{claim_label}.revisado_por: obligatorio para aceptar")
                if not claim.get("fecha_revision"):
                    errors.append(f"{claim_label}.fecha_revision: obligatoria para aceptar")
                else:
                    _date(claim["fecha_revision"], f"{claim_label}.fecha_revision", errors)
                if not supporting:
                    errors.append(f"{claim_label}: una afirmación aceptada necesita evidencia que la apoye")
                for evidence in supporting:
                    if not evidence.get("localizacion_fuente"):
                        errors.append(f"{claim_label}: falta localización exacta en la fuente")
                if claim.get("tipo") in PHENOTYPE_CLAIMS and supporting and all(
                    evidence.get("metodo_evidencia") == MetodoEvidenciaEnum.Homologia.value for evidence in supporting
                ):
                    errors.append(f"{claim_label}: la homología no basta para aceptar una afirmación fenotípica")

        if locus.get("estado_curacion") == EstadoCuracionEnum.Aceptado.value and not accepted_claims:
            errors.append(f"{locus_label}: un locus aceptado necesita al menos una afirmación aceptada")
        if locus.get("estado_curacion") == EstadoCuracionEnum.Revisado.value and not reviewed_claims:
            errors.append(f"{locus_label}: un locus revisado necesita al menos una afirmación revisada o aceptada")

    if errors:
        raise ValueError("Catálogo genético inválido:\n- " + "\n- ".join(errors))


def load_reference_catalog(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_reference_catalog(data)
    return data


def _source_values(source: dict) -> dict:
    values = {field: source.get(field) for field in SOURCE_FIELDS}
    values["tipo"] = TipoFuenteEnum(values["tipo"])
    values["fecha_consulta"] = dt.date.fromisoformat(values["fecha_consulta"]) if values["fecha_consulta"] else None
    return values


def _claim_values(claim: dict, version: int) -> dict:
    values = {field: claim.get(field) for field in CLAIM_FIELDS}
    values["tipo"] = TipoAfirmacionEnum(values["tipo"])
    values["estado"] = EstadoCuracionEnum(values["estado"])
    values["fecha_revision"] = dt.date.fromisoformat(values["fecha_revision"]) if values["fecha_revision"] else None
    values["version"] = version
    return values


def _evidence_values(evidence: dict, source_id: int) -> dict:
    values = {field: evidence.get(field) for field in EVIDENCE_FIELDS}
    values["metodo_evidencia"] = MetodoEvidenciaEnum(values["metodo_evidencia"])
    values["fuerza"] = FuerzaEvidenciaEnum(values["fuerza"])
    values["relacion"] = RelacionFuenteEnum(values["relacion"])
    values["fuente_id"] = source_id
    return values


def sync_reference_catalog(session: Session, data: dict) -> None:
    validate_reference_catalog(data)
    version = data["version"]
    reviewed_at = dt.date.fromisoformat(data["revisado_el"]) if data.get("revisado_el") else None

    source_rows: dict[str, FuenteCientifica] = {}
    for source_data in data["fuentes"]:
        source = session.scalar(select(FuenteCientifica).where(FuenteCientifica.clave == source_data["clave"]))
        values = _source_values(source_data)
        if source is None:
            source = FuenteCientifica(clave=source_data["clave"], **values)
            session.add(source)
        else:
            for field, value in values.items():
                setattr(source, field, value)
        session.flush()
        source_rows[source_data["clave"]] = source

    for locus_data in data["loci"]:
        locus = session.scalar(select(LocusReferencia).where(LocusReferencia.codigo == locus_data["codigo"]))
        if locus is None:
            locus = LocusReferencia(
                codigo=locus_data["codigo"],
                nombre_completo=locus_data["nombre_completo"],
                categoria=CategoriaLocusEnum(locus_data["categoria"]),
                tipo_entidad=TipoEntidadLocusEnum(locus_data["tipo_entidad"]),
                nombres_alternativos=json.dumps(locus_data.get("nombres_alternativos", []), ensure_ascii=False),
                especie_alcance=locus_data["especie_alcance"],
                resumen=locus_data.get("resumen"),
                estado_curacion=EstadoCuracionEnum(locus_data["estado_curacion"]),
                version=version,
                fecha_ultima_revision=reviewed_at,
                tipo_herencia=TipoHerenciaEnum.Desconocido,
                nivel_evidencia=NivelEvidenciaEnum.Baja,
            )
            session.add(locus)
            session.flush()
        if version >= locus.version:
            locus.nombre_completo = locus_data["nombre_completo"]
            locus.categoria = CategoriaLocusEnum(locus_data["categoria"])
            locus.tipo_entidad = TipoEntidadLocusEnum(locus_data["tipo_entidad"])
            locus.nombres_alternativos = json.dumps(locus_data.get("nombres_alternativos", []), ensure_ascii=False)
            locus.especie_alcance = locus_data["especie_alcance"]
            locus.resumen = locus_data.get("resumen")
            locus.estado_curacion = EstadoCuracionEnum(locus_data["estado_curacion"])
            locus.tipo_herencia = TipoHerenciaEnum.Desconocido
            locus.nivel_evidencia = NivelEvidenciaEnum.Baja
            locus.version = version
            locus.fecha_ultima_revision = reviewed_at
        session.flush()
        if locus.version > version:
            continue

        for claim_data in locus_data["afirmaciones"]:
            claim = session.scalar(
                select(AfirmacionReferencia).where(AfirmacionReferencia.codigo_estable == claim_data["codigo_estable"])
            )
            values = _claim_values(claim_data, version)
            if claim is None:
                claim = AfirmacionReferencia(
                    locus_id=locus.id,
                    codigo_estable=claim_data["codigo_estable"],
                    **values,
                )
                session.add(claim)
            elif version > claim.version:
                for field, value in values.items():
                    setattr(claim, field, value)
            session.flush()
            if claim.version > version:
                continue

            existing = {evidence.fuente_id: evidence for evidence in claim.evidencias}
            desired_ids = {source_rows[item["fuente"]].id for item in claim_data["evidencias"]}
            if version > 1:
                for source_id in set(existing) - desired_ids:
                    session.delete(existing[source_id])
            for evidence_data in claim_data["evidencias"]:
                source = source_rows[evidence_data["fuente"]]
                evidence = existing.get(source.id)
                evidence_values = _evidence_values(evidence_data, source.id)
                if evidence is None:
                    claim.evidencias.append(AfirmacionFuente(**evidence_values))
                else:
                    for field, value in evidence_values.items():
                        setattr(evidence, field, value)

    session.commit()


def export_reference_catalog(session: Session) -> dict:
    loci = session.scalars(
        select(LocusReferencia)
        .options(
            selectinload(LocusReferencia.afirmaciones)
            .selectinload(AfirmacionReferencia.evidencias)
            .selectinload(AfirmacionFuente.fuente)
        )
        .order_by(LocusReferencia.codigo)
    ).all()
    sources: dict[str, dict] = {}
    exported_loci: list[dict] = []
    review_dates: list[dt.date] = []

    for locus in loci:
        if locus.fecha_ultima_revision:
            review_dates.append(locus.fecha_ultima_revision)
        aliases = json.loads(locus.nombres_alternativos) if locus.nombres_alternativos else []
        claims: list[dict] = []
        for claim in sorted(locus.afirmaciones, key=lambda item: (item.estado.value, item.codigo_estable)):
            if claim.fecha_revision:
                review_dates.append(claim.fecha_revision)
            evidences: list[dict] = []
            for evidence in claim.evidencias:
                source = evidence.fuente
                sources[source.clave] = {
                    "clave": source.clave,
                    **{field: _json_value(getattr(source, field)) for field in SOURCE_FIELDS},
                }
                evidences.append(
                    {
                        "fuente": source.clave,
                        **{field: _json_value(getattr(evidence, field)) for field in EVIDENCE_FIELDS},
                    }
                )
            claims.append(
                {
                    "codigo_estable": claim.codigo_estable,
                    **{field: _json_value(getattr(claim, field)) for field in CLAIM_FIELDS},
                    "evidencias": evidences,
                }
            )
        exported_loci.append(
            {
                "codigo": locus.codigo,
                "nombre_completo": locus.nombre_completo,
                "categoria": locus.categoria.value,
                "tipo_entidad": locus.tipo_entidad.value,
                "nombres_alternativos": aliases,
                "especie_alcance": locus.especie_alcance,
                "resumen": locus.resumen,
                "estado_curacion": locus.estado_curacion.value,
                "afirmaciones": claims,
            }
        )

    data = {
        "version": max((locus.version for locus in loci), default=1),
        "revisado_el": (max(review_dates) if review_dates else dt.date.today()).isoformat(),
        "revisado_por": "Curaduría local",
        "fuentes": [sources[key] for key in sorted(sources)],
        "loci": exported_loci,
    }
    validate_reference_catalog(data)
    return data


def validate_database_catalog(session: Session) -> None:
    validate_reference_catalog(export_reference_catalog(session))
