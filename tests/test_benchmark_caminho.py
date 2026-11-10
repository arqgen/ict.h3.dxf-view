import json
from pathlib import Path

import pytest

from evals.benchmark.tools import calculo


@pytest.fixture
def arquivo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    rede = {
        "ruas": [
            [[0, 0, 0], [10, 0, 0]],
            [[10, 0, 0], [20, 0, 0]],
            [[100, 0, 0], [110, 0, 0]],
        ],
        "acessos": {
            "p0": {"familia": "/building/portaria", "linhas": [[[0, -5]]]},
            "p1": {"familia": "/building/torre/a", "linhas": [[[10, 0], [20, 0]]]},
            "p2": {"familia": "/building/torre/b", "linhas": [[[105, 0]]]},
            "p3": {"familia": "/building/torre/c", "linhas": []},
            "p4": {"familia": "/building/torre/d", "linhas": [[[5, 3]]]},
            "p5": {"familia": "/building/torre/e", "linhas": [[[15, -2], [15, 2]]]},
        },
    }
    (tmp_path / "x.json").write_text(json.dumps(rede))
    monkeypatch.setattr(calculo, "REDES", tmp_path)
    return "pasta/x.json"


def test_caminho_desempata_pelo_menor_caminho(arquivo: str) -> None:
    assert calculo.caminho(arquivo, "p0", "p1") == {
        "origem": "p0",
        "destino": "p1",
        "distancia": 10.0,
        "afastamento_origem": 5.0,
        "afastamento_destino": 0.0,
    }


def test_caminho_projeta_o_acesso_na_aresta(arquivo: str) -> None:
    meio = calculo.caminho(arquivo, "p0", "p4")
    assert (meio["distancia"], meio["afastamento_destino"]) == (5.0, 3.0)
    cruza = calculo.caminho(arquivo, "p0", "p5")
    assert (cruza["distancia"], cruza["afastamento_destino"]) == (15.0, 0.0)


def test_caminho_inalcancavel_e_erros_como_dado(arquivo: str) -> None:
    assert calculo.caminho(arquivo, "p0", "p2")["erro"] == "inalcançável"
    assert "não tem acesso" in calculo.caminho(arquivo, "p0", "p3")["erro"]
    assert "não é portaria" in calculo.caminho(arquivo, "p0", "p9")["erro"]
    assert "sem rede" in calculo.caminho("outro.json", "p0", "p1")["erro"]
