"""Casos das tarefas de edição e de histórico, sem LLM e sem motor.

Lê o índice das gravações e escreve `casos_edicao.json`:

    uv run python -m evals.benchmark.casos_edicao

Cada caso traz o `historico` (as versões até o estado atual, o último é o
estado inicial da tarefa), as `chamadas_esperadas`, o `estado_esperado` ao fim
delas e a `resposta_esperada` (o que o modelo deve dizer além do estado).
"""

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

from evals.benchmark.historico import ROOT, VAGA, casos_historico
from evals.benchmark.tools.edicao import OCULTOS

OUT = Path(__file__).parent
INDICE = OUT / "gravacoes.json"

PERGUNTAS = {
    "D1": "Mova a torre mais próxima da frente 5 m em direção aos fundos.",
    "D3": "Remova a torre mais próxima da APP e diga quantas unidades perdi.",
    "D6": "Suba a torre mais próxima da portaria para 20 pavimentos.",
    "E1": "Aumente para 1,5 vaga por unidade e refaça só o estacionamento.",
    "E3": "Mude o mix para 60% 2Q / 40% 1Q mantendo a implantação.",
    "E7": "Refaça só a terraplenagem com talude mais suave e sem muro.",
}
TAREFA = {
    "mover_torre": "D1",
    "remover_torre": "D3",
    "definir_pavimentos": "D6",
    "resolver_terraplenagem": "E7",
}


def _tarefa(entry: dict) -> str:
    if entry["tool"] == "alterar_programa":
        return "E3" if "mix" in entry["args"] else "E1"
    return TAREFA[entry["tool"]]


def _projeto(path: str) -> tuple[Any, int]:
    """`TotalDeUnidades` e número de vagas de um AQG."""
    raw = json.loads((ROOT / path).read_text())
    outputs = raw["solution"]["outputs"]
    unidades = next(
        (o.get("value") for o in outputs if o["type"] == "TotalDeUnidades"), None
    )
    vagas = sum(po["hid"].startswith(VAGA) for po in raw["solution"]["placed_objects"])
    return unidades, vagas


def resposta_esperada(tarefa: str, entry: dict, base: str) -> dict:
    """O que a tool devolve ao modelo, mais o número que a pergunta pede."""
    resposta = {k: v for k, v in entry.items() if k not in OCULTOS}
    if entry["veredito"] != "valido":
        return resposta
    if tarefa == "D3":
        antes, _ = _projeto(base)
        depois, _ = _projeto(entry["aqg"])
        resposta["unidades_perdidas"] = antes - depois
    if tarefa == "E1":
        unidades, projetadas = _projeto(entry["aqg"])
        _, no_arquivo = _projeto(base)
        necessarias = math.ceil(unidades * entry["args"]["valor"])
        resposta["vagas"] = {
            "necessarias": necessarias,
            "projetadas": projetadas,
            "deficit": necessarias - projetadas,
            "na_base": no_arquivo,
        }
    return resposta


def casos_edicao(indice: dict[str, dict]) -> list[dict]:
    bases = {v["arquivo"]: v["aqg"] for v in indice.values() if v["tool"] == "base"}
    casos = []
    for key, entry in sorted(indice.items(), key=lambda kv: kv[1]["arquivo"]):
        # Entradas com `apos` são passos de uma sequência (G5), não tarefas.
        if entry["tool"] == "base" or "apos" in entry["args"]:
            continue
        tarefa = _tarefa(entry)
        base = bases[entry["arquivo"]]
        casos.append(
            {
                "tarefa": tarefa,
                "arquivo": entry["arquivo"],
                "pergunta": PERGUNTAS[tarefa],
                "historico": [base],
                "chamadas_esperadas": [{"tool": entry["tool"], "args": entry["args"]}],
                "gravacao": key,
                # Erro do motor não grava estado: a implantação fica a da base.
                "estado_esperado": entry.get("aqg", base),
                "resposta_esperada": resposta_esperada(tarefa, entry, base),
            }
        )
    return sorted(casos, key=lambda c: (c["tarefa"], c["arquivo"]))


def main() -> None:
    indice = json.loads(INDICE.read_text())
    casos = casos_edicao(indice) + casos_historico(indice)
    (OUT / "casos_edicao.json").write_text(
        json.dumps(casos, ensure_ascii=False, indent=1)
    )
    print(Counter(c["tarefa"] for c in casos))


if __name__ == "__main__":
    main()
