from __future__ import annotations

import crud
from models import GeneracionEnum


def test_dashboard_shows_primary_plant_cover(client, session):
    planta = crud.create_planta(session, {"generacion": GeneracionEnum.F1})
    crud.create_foto(
        session,
        {
            "planta_id": planta.id,
            "filename": "principal.jpg",
            "thumbnail_filename": "principal_thumb.jpg",
            "es_foto_principal": True,
        },
    )
    crud.create_foto(
        session,
        {
            "planta_id": planta.id,
            "filename": "secondary.jpg",
            "thumbnail_filename": "secondary_thumb.jpg",
            "es_foto_principal": False,
        },
    )

    response = client.get("/")

    assert response.status_code == 200
    assert 'src="/static/thumbnails/principal_thumb.jpg"' in response.text
    assert 'src="/static/thumbnails/secondary_thumb.jpg"' not in response.text


def test_dashboard_uses_original_photo_when_thumbnail_is_missing(client, session):
    planta = crud.create_planta(session, {"generacion": GeneracionEnum.F1})
    crud.create_foto(
        session,
        {
            "planta_id": planta.id,
            "filename": "original.jpg",
            "thumbnail_filename": None,
            "es_foto_principal": True,
        },
    )

    response = client.get("/")

    assert response.status_code == 200
    assert 'src="/static/photos/original.jpg"' in response.text


def test_plant_list_shows_primary_plant_cover(client, session):
    planta = crud.create_planta(session, {"generacion": GeneracionEnum.F1})
    crud.create_foto(
        session,
        {
            "planta_id": planta.id,
            "filename": "principal.jpg",
            "thumbnail_filename": "principal_thumb.jpg",
            "es_foto_principal": True,
        },
    )
    crud.create_foto(
        session,
        {
            "planta_id": planta.id,
            "filename": "secondary.jpg",
            "thumbnail_filename": "secondary_thumb.jpg",
            "es_foto_principal": False,
        },
    )

    response = client.get("/plantas")

    assert response.status_code == 200
    assert 'src="/static/thumbnails/principal_thumb.jpg"' in response.text
    assert 'src="/static/thumbnails/secondary_thumb.jpg"' not in response.text
    assert 'alt="Portada de HP-001"' in response.text
