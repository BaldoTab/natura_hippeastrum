from __future__ import annotations

import datetime as dt
import json

from sqlalchemy import func, select

import crud
from models import Cruce, GeneracionEnum, Planta


def _base_form() -> dict:
    return {
        "generacion": GeneracionEnum.F1.value,
        "estado": "Bueno",
        "ploidy_sospecha": "Desconocido",
        "num_ejemplares_fisicos": "1",
    }


def _plant(session, name: str) -> Planta:
    return crud.create_planta(
        session,
        {"nombre_cultivar": name, "generacion": GeneracionEnum.F1},
    )


def _cross(session, mother: Planta, father: Planta) -> Cruce:
    return crud.create_cruce(
        session,
        {
            "planta_madre_id": mother.id,
            "planta_padre_id": father.id,
            "fecha_polinizacion": dt.date(2026, 4, 10),
        },
    )


def test_plant_form_includes_genealogy_fields(client):
    response = client.get("/plantas/new")

    assert response.status_code == 200
    assert 'id="genealogia"' in response.text
    assert 'name="id_madre"' in response.text
    assert 'name="id_padre"' in response.text
    assert 'name="id_cruce_origen"' in response.text
    assert 'name="es_clon_de"' in response.text
    assert "autopolinización" in response.text


def test_new_plant_uses_cross_parentage(client, session):
    mother = _plant(session, "Madre")
    father = _plant(session, "Padre")
    cross = _cross(session, mother, father)

    response = client.post(
        "/plantas/new",
        data={**_base_form(), "id_cruce_origen": cross.id, "id_madre": 999},
    )

    assert response.status_code == 303
    plant = session.scalar(select(Planta).order_by(Planta.id.desc()))
    assert plant.id_madre == mother.id
    assert plant.id_padre == father.id
    assert plant.id_cruce_origen == cross.id

    detail = client.get(f"/plantas/{plant.id}")
    assert detail.status_code == 200
    assert mother.codigo in detail.text
    assert father.codigo in detail.text
    assert cross.codigo in detail.text


def test_family_view_groups_siblings_children_and_clones(client, session):
    mother = _plant(session, "Madre")
    father = _plant(session, "Padre")
    cross = _cross(session, mother, father)
    child = crud.create_planta(
        session,
        {
            "nombre_cultivar": "Hijo",
            "generacion": GeneracionEnum.F1,
            "id_madre": mother.id,
            "id_padre": father.id,
            "id_cruce_origen": cross.id,
        },
    )
    sibling = crud.create_planta(
        session,
        {
            "nombre_cultivar": "Hermano",
            "generacion": GeneracionEnum.F1,
            "id_madre": mother.id,
            "id_padre": father.id,
            "id_cruce_origen": cross.id,
        },
    )
    clone = crud.create_planta(
        session,
        {
            "nombre_cultivar": "Clon",
            "generacion": GeneracionEnum.F1,
            "es_clon_de": child.id,
        },
    )
    descendant = crud.create_planta(
        session,
        {
            "nombre_cultivar": "Descendiente",
            "generacion": GeneracionEnum.F2,
            "id_madre": child.id,
            "id_padre": father.id,
        },
    )

    detail = client.get(f"/plantas/{child.id}")
    assert detail.status_code == 200
    assert f'href="/plantas/{sibling.id}"' in detail.text
    assert f'href="/plantas/{clone.id}"' in detail.text
    assert f'href="/plantas/{descendant.id}"' in detail.text
    assert "Autopolinización" not in detail.text

    cross_detail = client.get(f"/cruces/{cross.id}")
    assert cross_detail.status_code == 200
    assert f'href="/plantas/{child.id}"' in cross_detail.text
    assert f'href="/plantas/{sibling.id}"' in cross_detail.text

    tree = client.get(f"/arbol?planta_id={child.id}")
    assert tree.status_code == 200
    payload = tree.text.split('<script id="genealogyData" type="application/json">', 1)[1].split("</script>", 1)[0]
    graph = json.loads(payload)
    node_ids = {node["id"] for node in graph["nodes"]}
    assert graph["selected"] == f"p-{child.id}"
    assert {f"p-{plant.id}" for plant in (mother, father, child, sibling, clone, descendant)} <= node_ids
    assert f"c-{cross.id}" in node_ids
    assert any(link["type"] == "clon" for link in graph["links"])


def test_tree_defaults_to_a_plant_with_registered_family(client, session):
    isolated = _plant(session, "Aislada")
    mother = _plant(session, "Madre")
    father = _plant(session, "Padre")
    cross = _cross(session, mother, father)

    response = client.get("/arbol")

    assert response.status_code == 200
    payload = response.text.split('<script id="genealogyData" type="application/json">', 1)[1].split("</script>", 1)[0]
    graph = json.loads(payload)
    assert graph["selected"] != f"p-{isolated.id}"
    assert f"c-{cross.id}" in {node["id"] for node in graph["nodes"]}


def test_edit_rejects_self_parent_and_parent_cycles(client, session):
    parent = _plant(session, "Parental")
    child = crud.create_planta(
        session,
        {
            "nombre_cultivar": "Hijo",
            "generacion": GeneracionEnum.F1,
            "id_madre": parent.id,
        },
    )

    self_parent = client.post(
        f"/plantas/{parent.id}/edit",
        data={**_base_form(), "id_padre": parent.id},
    )
    assert self_parent.status_code == 400

    cycle = client.post(
        f"/plantas/{parent.id}/edit",
        data={**_base_form(), "id_madre": child.id},
    )
    assert cycle.status_code == 400
    session.refresh(parent)
    assert parent.id_madre is None
    assert parent.id_padre is None


def test_clone_cycles_are_rejected(client, session):
    original = _plant(session, "Original")
    clone = crud.create_planta(
        session,
        {
            "nombre_cultivar": "Clon",
            "generacion": GeneracionEnum.F1,
            "es_clon_de": original.id,
        },
    )

    response = client.post(
        f"/plantas/{original.id}/edit",
        data={**_base_form(), "es_clon_de": clone.id},
    )

    assert response.status_code == 400
    session.refresh(original)
    assert original.es_clon_de is None


def test_cross_edit_rejects_a_descendant_as_parent(client, session):
    mother = _plant(session, "Madre")
    father = _plant(session, "Padre")
    cross = _cross(session, mother, father)
    child = crud.create_planta(
        session,
        {
            "nombre_cultivar": "Hijo",
            "generacion": GeneracionEnum.F1,
            "id_cruce_origen": cross.id,
            "id_madre": mother.id,
            "id_padre": father.id,
        },
    )

    response = client.post(
        f"/cruces/{cross.id}/edit",
        data={
            "planta_madre_id": child.id,
            "planta_padre_id": father.id,
            "fecha_polinizacion": "2026-04-10",
        },
    )

    assert response.status_code == 400
    session.refresh(cross)
    assert cross.planta_madre_id == mother.id


def test_cross_parent_updates_propagate_to_descendants(client, session):
    mother = _plant(session, "Madre")
    father = _plant(session, "Padre")
    replacement = _plant(session, "Nueva madre")
    cross = _cross(session, mother, father)
    child = crud.create_planta(
        session,
        {
            "nombre_cultivar": "Hijo",
            "generacion": GeneracionEnum.F1,
            "id_cruce_origen": cross.id,
            "id_madre": mother.id,
            "id_padre": father.id,
        },
    )

    response = client.post(
        f"/cruces/{cross.id}/edit",
        data={
            "planta_madre_id": replacement.id,
            "planta_padre_id": father.id,
            "fecha_polinizacion": "2026-04-10",
        },
    )

    assert response.status_code == 303
    session.refresh(child)
    assert child.id_madre == replacement.id
    assert child.id_padre == father.id


def test_clone_registration_does_not_create_a_second_offspring_link(client, session):
    original = _plant(session, "Original")
    father = _plant(session, "Padre")
    cross = _cross(session, original, father)

    response = client.post(
        "/plantas/new",
        data={**_base_form(), "es_clon_de": original.id, "id_cruce_origen": cross.id},
    )

    assert response.status_code == 303
    clone = session.scalar(select(Planta).order_by(Planta.id.desc()))
    assert clone.es_clon_de == original.id
    assert clone.id_madre is None
    assert clone.id_padre is None
    assert clone.id_cruce_origen is None


def test_unknown_parent_is_rejected_without_creating_a_plant(client, session):
    response = client.post(
        "/plantas/new",
        data={**_base_form(), "id_madre": 999},
    )

    assert response.status_code == 400
    assert session.scalar(select(func.count(Planta.id))) == 0
