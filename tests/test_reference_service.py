from __future__ import annotations

import copy
from pathlib import Path

import pytest
from sqlalchemy import func, select

from models import AfirmacionReferencia, FuenteCientifica, LocusReferencia
from reference_service import (
    export_reference_catalog,
    load_reference_catalog,
    sync_reference_catalog,
    validate_database_catalog,
    validate_reference_catalog,
)


def _catalog() -> dict:
    return {
        "version": 1,
        "revisado_el": "2026-11-25",
        "revisado_por": "Prueba",
        "fuentes": [
            {
                "clave": "fuente-prueba",
                "tipo": "Articulo_primario",
                "autores": "Autores de prueba",
                "titulo": "Título de prueba",
                "publicacion": "Revista de prueba",
                "anio": 2026,
                "doi": "10.0000/prueba",
                "url": None,
                "fecha_consulta": None,
            }
        ],
        "loci": [
            {
                "codigo": "TEST1",
                "nombre_completo": "Locus de prueba",
                "categoria": "Color_estructural",
                "tipo_entidad": "Gen_molecular",
                "nombres_alternativos": ["Alias de prueba"],
                "especie_alcance": "Hippeastrum",
                "resumen": "Resumen de prueba",
                "estado_curacion": "Aceptado",
                "afirmaciones": [
                    {
                        "codigo_estable": "TEST1-funcion",
                        "tipo": "Funcion",
                        "texto": "Afirmación de prueba.",
                        "especie_alcance": "Hippeastrum",
                        "contexto": "Ensayo controlado",
                        "estado": "Aceptado",
                        "revisado_por": "Prueba",
                        "fecha_revision": "2026-11-25",
                        "notas_limitaciones": None,
                        "evidencias": [
                            {
                                "fuente": "fuente-prueba",
                                "metodo_evidencia": "Experimento_directo",
                                "fuerza": "Alta",
                                "relacion": "Apoya",
                                "localizacion_fuente": "Tabla 1",
                                "cita_textual": None,
                                "limitaciones": None,
                            }
                        ],
                    }
                ],
            }
        ],
    }


def test_sync_is_idempotent_and_export_round_trips(session):
    data = _catalog()
    sync_reference_catalog(session, data)
    sync_reference_catalog(session, data)
    assert session.scalar(select(func.count(LocusReferencia.id))) == 1
    assert session.scalar(select(func.count(AfirmacionReferencia.id))) == 1
    assert session.scalar(select(func.count(FuenteCientifica.id))) == 1
    exported = export_reference_catalog(session)
    assert exported["loci"][0]["codigo"] == "TEST1"
    assert exported["loci"][0]["afirmaciones"][0]["evidencias"][0]["fuente"] == "fuente-prueba"
    validate_database_catalog(session)


def test_accepted_claim_requires_supporting_source():
    data = _catalog()
    data["loci"][0]["afirmaciones"][0]["evidencias"] = []
    with pytest.raises(ValueError, match="necesita evidencia"):
        validate_reference_catalog(data)


def test_homology_cannot_validate_phenotype_claim():
    data = _catalog()
    claim = data["loci"][0]["afirmaciones"][0]
    claim["tipo"] = "Efecto_alelo"
    claim["evidencias"][0]["metodo_evidencia"] = "Homologia"
    with pytest.raises(ValueError, match="homología no basta"):
        validate_reference_catalog(data)


def test_placeholder_is_not_a_scientific_source():
    data = copy.deepcopy(_catalog())
    data["fuentes"][0]["clave"] = "Homología"
    data["loci"][0]["afirmaciones"][0]["evidencias"][0]["fuente"] = "Homología"
    with pytest.raises(ValueError, match="no es una referencia"):
        validate_reference_catalog(data)


def test_reviewed_claim_requires_traceable_evidence():
    data = _catalog()
    claim = data["loci"][0]["afirmaciones"][0]
    claim["estado"] = "Revisado"
    claim["evidencias"] = []
    with pytest.raises(ValueError, match="necesita evidencia"):
        validate_reference_catalog(data)


def test_curated_catalog_is_traceable_and_conservative(session):
    path = Path(__file__).resolve().parents[1] / "data" / "reference_catalog.json"
    data = load_reference_catalog(path)
    sync_reference_catalog(session, data)
    sync_reference_catalog(session, data)

    loci = {locus.codigo: locus for locus in session.scalars(select(LocusReferencia)).all()}
    assert len(loci) == 14
    assert "HpUFGT" in loci
    for code in ("R", "Y", "W", "P", "D", "HpbHLH1"):
        assert loci[code].estado_curacion.value == "Disputado"
    assert loci["HpMYB1"].estado_curacion.value == "Revisado"
    for locus in loci.values():
        for claim in locus.afirmaciones:
            if claim.estado.value == "Revisado":
                assert claim.revisado_por
                assert claim.fecha_revision
                assert claim.evidencias
                assert all(evidence.localizacion_fuente for evidence in claim.evidencias)
    validate_database_catalog(session)
    assert export_reference_catalog(session)["version"] == 2
