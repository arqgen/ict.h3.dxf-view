import json
import subprocess
import sys
from pathlib import Path

import pytest

from evals.benchmark.tools import GRUPOS, edicao, esquemas

GRAVACOES = Path(__file__).resolve().parents[1] / "data" / "benchmark" / "gravacoes"
MOTOR = ("buildings", "maga", "errata", "persistente", "lib")


def test_tools_nao_importam_codigo_de_motor() -> None:
    code = (
        "import sys, evals.benchmark.tools; "
        "print(sorted({m.split('.')[0] for m in sys.modules}))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert not set(json.loads(out.stdout.replace("'", '"'))) & set(MOTOR)


def test_esquemas_nao_expoem_estado() -> None:
    schemas = esquemas(["calculo", "edicao", "linha_de_base"])
    assert len(schemas) == 4 + 9 + 16
    assert all("estado" not in s["parameters"]["properties"] for s in schemas)


def test_calcular_so_aritmetica() -> None:
    calcular = GRUPOS["calculo"]["calcular"]
    assert calcular("(8000 - 1200) / 8000")["resultado"] == 0.85
    assert "erro" in calcular("__import__('os')")
    assert "erro" in calcular("1 / 0")


@pytest.mark.skipif(not GRAVACOES.exists(), reason="gravações não versionadas")
def test_toda_chamada_gravada_devolve_a_gravacao() -> None:
    indice = edicao._indice()
    bases = {v["arquivo"]: v["aqg"] for v in indice.values() if v["tool"] == "base"}
    entradas = [v for v in indice.values() if v["tool"] != "base"]
    assert entradas
    for v in entradas:
        args = {k: x for k, x in v["args"].items() if k != "apos"}
        estado = indice[v["args"]["apos"]]["aqg"] if "apos" in v["args"] else None
        out = GRUPOS["edicao"][v["tool"]](estado or bases[v["arquivo"]], **args)
        assert out["estado"] == v.get("aqg"), v
        assert out["resposta"]["veredito"] == v["veredito"], v


@pytest.mark.skipif(not GRAVACOES.exists(), reason="gravações não versionadas")
def test_formas_equivalentes_e_fora_do_roteiro() -> None:
    indice = edicao._indice()
    e7 = next(
        v
        for v in indice.values()
        if v["tool"] == "resolver_terraplenagem" and "apos" not in v["args"]
    )
    base = next(
        v["aqg"]
        for v in indice.values()
        if v["tool"] == "base" and v["arquivo"] == e7["arquivo"]
    )
    terraplenagem = GRUPOS["edicao"]["resolver_terraplenagem"]
    out = terraplenagem(base, aterro="1:2", corte="1:1.5", muro="Sem limite")
    assert out["estado"] == e7["aqg"]
    fora = terraplenagem(base, aterro="1:3", corte="1:1.5", muro="sem limite")
    assert fora == {"resposta": {"erro": "fora do roteiro"}, "estado": None}
    assert GRUPOS["edicao"]["validar"](base)["resposta"] == {"erro": "fora do roteiro"}
