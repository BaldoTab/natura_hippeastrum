from __future__ import annotations

from sqlalchemy import func, select

from models import CategoriaLocusEnum, GenotipoPlanta, LocusReferencia, Planta


def _locus(session) -> LocusReferencia:
    locus = LocusReferencia(
        codigo="R",
        nombre_completo="Locus R de prueba",
        categoria=CategoriaLocusEnum.Color_estructural,
    )
    session.add(locus)
    session.commit()
    session.refresh(locus)
    return locus


def _base_form() -> dict:
    return {
        "generacion": "F0",
        "estado": "Bueno",
        "ploidy_sospecha": "Desconocido",
        "num_ejemplares_fisicos": "1",
    }


def test_new_plant_persists_genotype(client, session):
    locus = _locus(session)
    data = {
        **_base_form(),
        "nombre_cultivar": "Planta de prueba",
        "gl_1_alelo_1": "R",
        "gl_1_alelo_2": "r",
        "gl_1_confianza": "Media_inferido",
        "gl_1_metodo": "Comparacion_parental",
        "gl_1_fuente": "Prueba automatizada",
    }
    response = client.post("/plantas/new", data=data)
    assert response.status_code == 303
    planta = session.scalar(select(Planta).order_by(Planta.id.desc()))
    genotype = session.scalar(select(GenotipoPlanta).where(GenotipoPlanta.planta_id == planta.id))
    assert genotype.locus_id == locus.id
    assert genotype.genotipo_display == "R/r"
    assert genotype.fuente_evidencia == "Prueba automatizada"


def test_edit_can_clear_genotype(client, session):
    locus = _locus(session)
    response = client.post(
        "/plantas/new",
        data={
            **_base_form(),
            "gl_1_alelo_1": "R",
            "gl_1_alelo_2": "R",
            "gl_1_confianza": "Baja_visual",
            "gl_1_metodo": "Observacion_fenotipo",
        },
    )
    planta_id = int(response.headers["location"].rsplit("/", 1)[1])
    response = client.post(
        f"/plantas/{planta_id}/edit",
        data={
            **_base_form(),
            "gl_1_alelo_1": "?",
            "gl_1_alelo_2": "?",
            "gl_1_confianza": "Desconocido",
            "gl_1_metodo": "Desconocido",
            "gl_1_fuente": "",
        },
    )
    assert response.status_code == 303
    assert session.scalar(select(func.count(GenotipoPlanta.id)).where(GenotipoPlanta.planta_id == planta_id)) == 0


def test_unknown_locus_is_rejected(client, session):
    _locus(session)
    response = client.post("/plantas/new", data={**_base_form(), "gl_999_alelo_1": "R"})
    assert response.status_code == 400
    assert session.scalar(select(func.count(Planta.id))) == 0
