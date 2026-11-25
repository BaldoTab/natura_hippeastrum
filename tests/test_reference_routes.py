from sqlalchemy import select

import main
from models import LocusReferencia
from reference_service import load_reference_catalog, sync_reference_catalog


def _sync_catalog(session):
    sync_reference_catalog(session, load_reference_catalog(main.REFERENCE_CATALOG_PATH))


def test_reference_index_filters_and_detail(client, session):
    _sync_catalog(session)

    response = client.get("/referencia")
    assert response.status_code == 200
    assert "HpMYB1" in response.text
    assert "HpUFGT" in response.text
    assert "Criterio de lectura" in response.text
    assert 'href="/referencia/bases"' in response.text

    response = client.get("/referencia", params={"q": "HpUFGT"})
    assert response.status_code == 200
    assert "HpUFGT" in response.text
    assert "HpMYB1" not in response.text

    response = client.get("/referencia", params={"estado": "Disputado"})
    assert response.status_code == 200
    assert "HpbHLH1" in response.text
    assert "HpUFGT" not in response.text

    locus = session.scalar(select(LocusReferencia).where(LocusReferencia.codigo == "HpMYB1"))
    response = client.get(f"/referencia/{locus.id}")
    assert response.status_code == 200
    assert "OQ446482" in response.text
    assert "10.1186/s12870-023-04582-4" in response.text
    assert "Effects of HpMYB1 overexpression in Tobacco" in response.text
    assert "Evidencia funcional heteróloga" in response.text
    assert 'href="/referencia/bases"' in response.text


def test_reference_genetics_basics(client):
    response = client.get("/referencia/bases")

    assert response.status_code == 200
    assert "Bases sobre genética" in response.text
    assert "Conceptos básicos" in response.text
    assert "Símbolos clásicos y genes moleculares" in response.text
    assert "Qué sabemos de HpMYB1" in response.text
    assert "Una flor roja no justifica escribir automáticamente" in response.text
    assert 'href="/referencia"' in response.text


def test_reference_unknown_locus_returns_404(client):
    response = client.get("/referencia/999999")
    assert response.status_code == 404
