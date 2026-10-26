"""Testes das rotas HTTP.

Nao chamam o LLM: verificam que o projeto AQG e indexado, que o payload de render
sai coerente com o indice e que o detalhe de entidade traz os dados da familia.
"""

import json

import pytest
from fastapi.testclient import TestClient

from src.api.server import create_app
from tests.make_aqg_sample import build_sample_project


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture(scope="module")
def sample_bytes() -> bytes:
    return json.dumps(build_sample_project()).encode()


def _upload(client: TestClient, data: bytes):
    return client.post(
        "/api/documents",
        files={"file": ("sample.json", data, "application/json")},
    )


@pytest.fixture(scope="module")
def document_id(client: TestClient, sample_bytes: bytes) -> str:
    response = _upload(client, sample_bytes)
    assert response.status_code == 201, response.text
    return response.json()["document_id"]


def test_health(client: TestClient):
    body = client.get("/health").json()
    assert body["status"] == "ok"


def test_upload_returns_index_metadata(client: TestClient, sample_bytes: bytes):
    response = _upload(client, sample_bytes)
    assert response.status_code == 201
    body = response.json()

    assert body["entity_count"] == 18
    assert body["layer_count"] == 9
    assert body["units"] == "metros"
    assert body["filename"] == "sample.json"
    assert body["by_type"]["apartamento"] == 4
    assert body["bbox"] == [0.0, 0.0, 100.0, 80.0]
    assert "acad_version" not in body
    assert "block_count" not in body
    assert "insert_count" not in body
    assert len(body["warnings"]) == 1
    assert "p6" in body["warnings"][0]


def test_upload_rejects_non_json(client: TestClient):
    response = _upload(client, b"isto nao e json")
    assert response.status_code == 400


def test_upload_rejects_json_that_is_not_a_project(client: TestClient):
    response = _upload(client, json.dumps({"a": 1}).encode())
    assert response.status_code == 400


def test_upload_rejects_project_without_drawable_geometry(client: TestClient):
    project = build_sample_project()
    project["site"]["elements"] = [
        e for e in project["site"]["elements"] if e["cad"]["type"] == "CadMesh"
    ]
    project["solution"]["placed_objects"] = []

    response = _upload(client, json.dumps(project).encode())
    assert response.status_code == 400
    assert response.json()["detail"] == "o arquivo não contém geometria desenhável"


def test_get_document(client: TestClient, document_id: str):
    body = client.get(f"/api/documents/{document_id}").json()
    assert body["document_id"] == document_id
    assert body["entity_count"] == 18


def test_prims_ids_match_the_entities(client: TestClient, document_id: str):
    prims = client.get(f"/api/documents/{document_id}/prims").json()

    ids = {entity["id"] for entity in prims["entities"]}
    assert ids == {
        "s0", "s1", "s2", "s3",
        "p0.0", "p0.1", "p0.2", "p0.3", "p0.4",
        "p1.0", "p1.1", "p1.2", "p1.3", "p1.4",
        "p2.0", "p3.0", "p4", "p5",
    }  # fmt: skip

    # Todo id que o canvas desenha tem de ser consultavel — e a premissa que faz
    # o destaque da IA cair na entidade certa.
    for entity_id in ids:
        detail = client.get(f"/api/documents/{document_id}/entities/{entity_id}")
        assert detail.status_code == 200
        assert detail.json()["id"] == entity_id


def test_family_part_details(client: TestClient, document_id: str):
    body = client.get(f"/api/documents/{document_id}/entities/p0.0").json()

    assert body["type"] == "apartamento"
    assert body["layer"] == "pav_tipo"
    assert body["area"] == 50.0
    assert body["text"] == "2 Quartos"
    assert body["instance"] == "p0"
    assert body["family"] == "T/4"
    assert body["hid"] == "/building/torre/T/4/0i/2f/11111111"
    assert body["properties"] == {"type": "Tower", "total_pavimentos": 2}
    assert "block" not in body
    assert "raw" not in body


def test_site_element_details(client: TestClient, document_id: str):
    body = client.get(f"/api/documents/{document_id}/entities/s0").json()

    assert body["layer"] == "AQG_PERIMETRO"
    assert body["area"] == 8000.0
    assert body["length"] == 360.0
    assert body["instance"] is None
    assert body["family"] is None
    assert body["hid"] is None
    assert body["properties"] == {}


def test_instance_id_is_not_an_entity(client: TestClient, document_id: str):
    response = client.get(f"/api/documents/{document_id}/entities/p0")
    assert response.status_code == 404


def test_unknown_entity_is_404(client: TestClient, document_id: str):
    response = client.get(f"/api/documents/{document_id}/entities/nao-existe")
    assert response.status_code == 404


def test_unknown_document_is_404(client: TestClient):
    response = client.get("/api/documents/deadbeef")
    assert response.status_code == 404
    assert "envie o arquivo novamente" in response.json()["detail"]
    assert client.get("/api/documents/deadbeef/prims").status_code == 404


def test_chat_with_unknown_document_is_404(client: TestClient):
    response = client.post(
        "/api/chat",
        json={"message": "quantas entidades?", "chat_id": "c1", "document_id": "x"},
    )
    assert response.status_code == 404


def test_chat_validates_empty_message(client: TestClient, document_id: str):
    response = client.post(
        "/api/chat",
        json={"message": "", "chat_id": "c1", "document_id": document_id},
    )
    assert response.status_code == 422
