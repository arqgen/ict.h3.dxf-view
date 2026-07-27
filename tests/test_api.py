"""Testes das rotas HTTP e da construcao do agente.

Nao chamam o LLM: verificam que o documento e indexado, que o payload de render
sai coerente com o indice e que o agente monta com as 12 tools e o resumo do
desenho nas instrucoes.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from src.api.server import create_app
from tests.make_sample import build_sample_doc


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture(scope="module")
def sample_bytes(tmp_path_factory) -> bytes:
    """Bytes de um DXF real em disco — o mesmo caminho de um upload de verdade."""
    path = tmp_path_factory.mktemp("dxf") / "sample.dxf"
    build_sample_doc().saveas(path)
    return path.read_bytes()


@pytest.fixture(scope="module")
def document_id(client: TestClient, sample_bytes: bytes) -> str:
    response = client.post(
        "/api/documents",
        files={"file": ("sample.dxf", sample_bytes, "application/dxf")},
    )
    assert response.status_code == 201, response.text
    return response.json()["document_id"]


def test_health(client: TestClient):
    body = client.get("/health").json()
    assert body["status"] == "ok"


def test_upload_returns_index_metadata(client: TestClient, sample_bytes: bytes):
    response = client.post(
        "/api/documents",
        files={"file": ("sample.dxf", sample_bytes, "application/dxf")},
    )
    assert response.status_code == 201
    body = response.json()

    assert body["entity_count"] == 14
    assert body["units"] == "metros"
    assert body["filename"] == "sample.dxf"
    assert body["by_type"]["INSERT"] == 3
    assert body["insert_count"] == 3
    assert body["bbox"] is not None
    assert any(layer["name"] == "CONTORNO" for layer in body["layers"])


def test_upload_rejects_non_dxf(client: TestClient):
    response = client.post(
        "/api/documents",
        files={"file": ("nota.txt", b"isto nao e um dxf", "text/plain")},
    )
    assert response.status_code == 400


def test_get_document(client: TestClient, document_id: str):
    body = client.get(f"/api/documents/{document_id}").json()
    assert body["document_id"] == document_id
    assert body["entity_count"] == 14


def test_get_prims_matches_the_index(client: TestClient, document_id: str):
    body = client.get(f"/api/documents/{document_id}/prims").json()

    assert body["entities"], "payload de render vazio"
    assert body["bbox"] is not None

    contour = next(e for e in body["entities"] if e["layer"] == "CONTORNO")
    assert contour["color"] == "#ff0000"
    assert contour["shapes"][0]["pts"] == [
        [0.0, 0.0],
        [20.0, 0.0],
        [20.0, 14.0],
        [0.0, 14.0],
    ]
    assert contour["shapes"][0]["c"] is True


def test_prims_ids_are_addressable_as_entities(client: TestClient, document_id: str):
    prims = client.get(f"/api/documents/{document_id}/prims").json()

    # Todo id que o canvas desenha tem de ser consultavel — e a premissa que faz
    # o destaque da IA cair na entidade certa.
    for entity in prims["entities"][:5]:
        detail = client.get(f"/api/documents/{document_id}/entities/{entity['id']}")
        assert detail.status_code == 200
        assert detail.json()["id"] == entity["id"]


def test_entity_details(client: TestClient, document_id: str):
    prims = client.get(f"/api/documents/{document_id}/prims").json()
    contour = next(e for e in prims["entities"] if e["layer"] == "CONTORNO")

    body = client.get(f"/api/documents/{document_id}/entities/{contour['id']}").json()
    assert body["closed"] is True
    assert body["length"] == 68.0
    assert body["area"] == 280.0
    assert body["raw"]["layer"] == "CONTORNO"


def test_unknown_entity_is_404(client: TestClient, document_id: str):
    response = client.get(f"/api/documents/{document_id}/entities/nao-existe")
    assert response.status_code == 404


def test_unknown_document_is_404(client: TestClient):
    assert client.get("/api/documents/deadbeef").status_code == 404
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


def test_agent_builds_with_twelve_tools_and_the_document_summary(sample_model):
    from src.ai_modules.agents import get_cad_agent

    agent = asyncio.run(get_cad_agent(user_id="local", model=sample_model))

    assert len(agent.tools) == 12
    assert agent.tool_call_limit == 14

    instructions = "\n".join(agent.instructions)
    assert "<documento_carregado>" in instructions
    assert "Nunca invente números" in instructions
    # O resumo real do desenho tem de estar la, nao so o cabecalho do bloco.
    assert "Total de entidades indexadas: 14" in instructions
    assert "metros" in instructions
