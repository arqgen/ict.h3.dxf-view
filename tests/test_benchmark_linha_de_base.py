import json
from collections import Counter
from pathlib import Path

import pytest

from evals.benchmark.cliente_linha_de_base import CASOS, SEM_COBERTURA, responder

AQG = Path(__file__).resolve().parents[1] / "data" / "aqg"


@pytest.mark.skipif(not (AQG / "avaliadas").exists(), reason="AQGs não versionados")
def test_linha_de_base_confere_com_o_gabarito() -> None:
    # Só os arquivos em que as 12 tarefas cobertas se aplicam, e 3 deles: a
    # conferência completa (45 s) é o próprio módulo.
    casos = [
        c
        for c in json.loads(CASOS.read_text())
        if c["status"] == "ok" and c["tarefa"] not in SEM_COBERTURA
    ]
    por_arquivo = Counter(c["arquivo"] for c in casos)
    arquivos = sorted(a for a, n in por_arquivo.items() if n == 12)[:3]
    amostra = [c for c in casos if c["arquivo"] in arquivos]
    assert len(amostra) == 36
    assert len({c["tarefa"] for c in amostra}) == 12
    for caso in amostra:
        assert responder(caso)[0] == caso["resposta_esperada"], caso["tarefa"]
