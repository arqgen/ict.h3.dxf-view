import json
from pathlib import Path

import pytest

from evals.benchmark.controles import CASOS, executar, gabarito, rodar, vandalo

GRAVACOES = Path(__file__).resolve().parents[1] / "data" / "benchmark" / "gravacoes"
pytestmark = pytest.mark.skipif(
    not GRAVACOES.exists(), reason="gravações não versionadas"
)


def test_controles_do_instrumento() -> None:
    casos = json.loads(CASOS.read_text())
    assert casos
    for nota in rodar(gabarito, casos):
        assert nota["acerto"] and nota["estado_esperado"]
        assert not nota["dano_colateral"] and not nota["fora_do_roteiro"]
    assert all(n["acerto"] and n["dano_colateral"] for n in rodar(vandalo, casos))


def test_diff_versoes_e_desfazer() -> None:
    casos = json.loads(CASOS.read_text())
    g4 = next(c for c in casos if c["tarefa"] == "G4")
    _, saidas = executar(g4, g4["chamadas_esperadas"])
    assert saidas == [g4["resposta_esperada"]]
    g5 = next(c for c in casos if c["tarefa"] == "G5")
    versoes, saidas = executar(g5, [{"tool": "desfazer", "args": {"n": 3}}])
    assert versoes == g5["historico"] and "erro" in saidas[0]
