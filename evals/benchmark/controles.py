"""Controles do instrumento (T1): avaliação de um cliente sobre `casos_edicao.json`.

Um cliente recebe o caso e devolve as chamadas que faz e a resposta final. O
harness executa as chamadas com as tools entregues e o histórico de versões
(`desfazer`, `diff_versoes`), que na RECOD é da estrutura dela. Sem os dois
controles passando, nenhum número do benchmark vale:

    uv run python -m evals.benchmark.controles
"""

import json
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from evals.benchmark.historico import ROOT, diferenca
from evals.benchmark.tools import GRUPOS
from evals.benchmark.tools.edicao import _norm

CASOS = Path(__file__).parent / "casos_edicao.json"
# Tudo que muda o estado: as edições (exceto `validar`, que só lê) e `desfazer`.
ALTERA = (set(GRUPOS["edicao"]) - {"validar"}) | {"desfazer"}
TERRAPLENAGEM = {
    "tool": "resolver_terraplenagem",
    "args": {"aterro": "1:2", "corte": "1:1,5", "muro": "sem limite"},
}

Chamada = dict[str, Any]
Cliente = Callable[[dict], tuple[list[Chamada], Any]]


def _aqg(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


def executar(caso: dict, chamadas: list[Chamada]) -> tuple[list[str], list[Any]]:
    """Versões ao fim das chamadas (a última é o estado atual) e a saída de cada uma."""
    versoes = list(caso["historico"])
    saidas: list[Any] = []
    for chamada in chamadas:
        tool, args = chamada["tool"], chamada["args"]
        if tool == "desfazer":
            if not 0 < args["n"] < len(versoes):
                saidas.append({"erro": "não há versões para desfazer"})
                continue
            del versoes[-args["n"] :]
            saidas.append({"estado": versoes[-1]})
        elif tool == "diff_versoes":
            mae, filha = versoes[args["mae"]], versoes[args["filha"]]
            saidas.append(diferenca(_aqg(mae), _aqg(filha)))
        elif tool in GRUPOS["edicao"]:
            out = GRUPOS["edicao"][tool](versoes[-1], **args)
            if out["estado"]:
                versoes.append(out["estado"])
            saidas.append(out["resposta"])
        elif tool == "calcular":
            saidas.append(GRUPOS["calculo"][tool](**args))
        else:
            f = GRUPOS["calculo"].get(tool) or GRUPOS["linha_de_base"][tool]
            saidas.append(f(versoes[-1], **args))
    return versoes, saidas


def _chave(chamada: Chamada) -> str:
    args = {k: v for k, v in chamada["args"].items() if v is not None}
    return json.dumps([chamada["tool"], _norm(args)])


def avaliar(caso: dict, chamadas: list[Chamada], resposta: Any) -> dict[str, Any]:
    """Acerto: fez as chamadas esperadas e respondeu certo. Dano colateral: fez
    alguma chamada que muda o estado sem estar entre as esperadas (inclusive uma
    "fora do roteiro", que no produto teria mudado o desenho)."""
    versoes, saidas = executar(caso, chamadas)
    esperadas = Counter(_chave(c) for c in caso["chamadas_esperadas"])
    feitas = Counter(_chave(c) for c in chamadas)
    alteram = Counter(_chave(c) for c in chamadas if c["tool"] in ALTERA)
    return {
        "acerto": not (esperadas - feitas) and resposta == caso["resposta_esperada"],
        "dano_colateral": bool(alteram - esperadas),
        "estado_esperado": versoes[-1] == caso["estado_esperado"],
        "fora_do_roteiro": sum(
            isinstance(s, dict) and s.get("erro") == "fora do roteiro" for s in saidas
        ),
        "chamadas": len(chamadas),
    }


def gabarito(caso: dict) -> tuple[list[Chamada], Any]:
    return caso["chamadas_esperadas"], caso["resposta_esperada"]


def vandalo(caso: dict) -> tuple[list[Chamada], Any]:
    """Acerta e ainda refaz a terraplenagem: muda o estado quando há gravação
    (depois da D1) e cai "fora do roteiro" nos demais."""
    chamadas, resposta = gabarito(caso)
    return [*chamadas, TERRAPLENAGEM], resposta


def rodar(cliente: Cliente, casos: list[dict]) -> list[dict]:
    return [avaliar(caso, *cliente(caso)) for caso in casos]


def main() -> None:
    casos = json.loads(CASOS.read_text())
    ok = True
    for nome, cliente, esperado in (
        ("gabarito", gabarito, {"acerto": True, "dano_colateral": False}),
        ("vandalo", vandalo, {"acerto": True, "dano_colateral": True}),
    ):
        notas = rodar(cliente, casos)
        taxas = {k: sum(n[k] for n in notas) for k in esperado}
        passou = all(all(n[k] == v for k, v in esperado.items()) for n in notas)
        ok &= passou
        print(
            f"{nome}: {taxas} de {len(notas)} casos -> {'ok' if passou else 'FALHOU'}"
        )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
