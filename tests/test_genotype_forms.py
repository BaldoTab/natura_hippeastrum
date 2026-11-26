from __future__ import annotations

from sqlalchemy import func, select

from models import (
    CategoriaLocusEnum,
    ConfianzaGenotipoEnum,
    Fenotipo,
    GenotipoPlanta,
    LocusReferencia,
    MetodoInferenciaEnum,
    PapilioEnum,
    Planta,
    TipoPatronEnum,
)


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


def test_plant_form_explains_phenotype_does_not_determine_genotype(client, session):
    _locus(session)
    response = client.get("/plantas/new")

    assert response.status_code == 200
    assert "Genotipo conocido (opcional)" in response.text
    assert "El fenotipo describe lo que observas, pero no permite deducir el genotipo" in response.text
    assert 'href="/referencia/bases"' in response.text
    assert "Grado de papilio" in response.text
    assert "x-data='{ tipoPatron:" in response.text
    assert "x-show=\"tipoPatron === 'Papilio'\"" in response.text
    assert "Confirmado en laboratorio" in response.text
    assert "Baja por observación visual" in response.text
    assert "Observación del fenotipo" in response.text
    assert "PapilioEnum.Si" not in response.text


def test_plant_detail_uses_readable_enum_labels(client, session):
    _locus(session)
    response = client.post(
        "/plantas/new",
        data={
            **_base_form(),
            "fen_tipo_patron": TipoPatronEnum.Papilio.value,
            "fen_patron_papilio": PapilioEnum.Si.value,
            "gl_1_alelo_1": "R",
            "gl_1_alelo_2": "R",
            "gl_1_confianza": ConfianzaGenotipoEnum.Baja_visual.value,
            "gl_1_metodo": MetodoInferenciaEnum.Observacion_fenotipo.value,
        },
    )
    planta_id = int(response.headers["location"].rsplit("/", 1)[1])

    response = client.get(f"/plantas/{planta_id}")

    assert response.status_code == 200
    assert "Papilio:</span> Sí" in response.text
    assert "Observación del fenotipo · Baja por observación visual" in response.text
    assert "PapilioEnum.Si" not in response.text
    assert "MetodoInferenciaEnum.Observacion_fenotipo" not in response.text
    assert "ConfianzaGenotipoEnum.Baja_visual" not in response.text


def test_papilio_grade_is_cleared_when_pattern_is_not_papilio(client, session):
    response = client.post(
        "/plantas/new",
        data={
            **_base_form(),
            "fen_tipo_patron": TipoPatronEnum.Papilio.value,
            "fen_patron_papilio": PapilioEnum.Parcial.value,
        },
    )
    planta_id = int(response.headers["location"].rsplit("/", 1)[1])
    fenotipo = session.scalar(select(Fenotipo).where(Fenotipo.planta_id == planta_id))
    assert fenotipo.patron_papilio == PapilioEnum.Parcial

    response = client.post(
        f"/plantas/{planta_id}/edit",
        data={
            **_base_form(),
            "fen_tipo_patron": TipoPatronEnum.Uniforme.value,
            "fen_patron_papilio": PapilioEnum.Si.value,
        },
    )
    assert response.status_code == 303
    session.refresh(fenotipo)
    assert fenotipo.tipo_patron == TipoPatronEnum.Uniforme
    assert fenotipo.patron_papilio is None
