"""Respostas esperadas das tarefas de histórico G4 e G5, sem LLM e sem motor.

Lê as gravações do índice (a base é a mãe, o estado inicial que a RECOD lê).
Quem escreve os casos é `casos_edicao.py`.
"""

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[2]
TORRE = "/building/torre"
VAGA = "/equipment/vaga"
TERRA = ("corte", "aterro", "muro_comprimento", "muro_altura")

PERGUNTAS = {
    "G4": "O que mudou entre a solução mãe e a filha?",
    "G5": "Desfaça as duas últimas mudanças.",
}


def r3(x: float) -> float:
    return round(x, 3)


def _torres(raw: dict) -> list[tuple[str, dict]]:
    return [
        (f"p{i}", po.get("position") or {})
        for i, po in enumerate(raw["solution"]["placed_objects"])
        if po["hid"].startswith(TORRE)
    ]


def _vagas(raw: dict) -> Counter:
    return Counter(
        tuple(round((po.get("position") or {}).get(k, 0.0), 2) for k in "xy")
        + (round((po.get("position") or {}).get("angle", 0.0), 2),)
        for po in raw["solution"]["placed_objects"]
        if po["hid"].startswith(VAGA)
    )


def diferenca(mae: dict, filha: dict) -> dict[str, Any]:
    """O que muda de `mae` para `filha` com as mesmas torres na mesma ordem (a cascata
    preserva a ordem delas); os ids são os de cada estado."""
    tm, tf = _torres(mae), _torres(filha)
    if len(tm) != len(tf):
        raise ValueError(f"torres diferentes: {len(tm)} na mãe, {len(tf)} na filha")
    movidas = []
    for (im, pm), (i_f, pf) in zip(tm, tf, strict=True):
        dx, dy = (
            pf.get("x", 0.0) - pm.get("x", 0.0),
            pf.get("y", 0.0) - pm.get("y", 0.0),
        )
        giro = pf.get("angle", 0.0) - pm.get("angle", 0.0)
        if math.hypot(dx, dy) < 1e-6 and abs(giro) < 1e-6:
            continue
        movidas.append(
            {
                "mae": im,
                "filha": i_f,
                "vetor": [r3(dx), r3(dy)],
                "distancia": r3(math.hypot(dx, dy)),
                "giro": r3(giro),
            }
        )

    vm, vf = _vagas(mae), _vagas(filha)
    vagas = {
        "mae": sum(vm.values()),
        "filha": sum(vf.values()),
        "mantidas": sum((vm & vf).values()),
        "removidas": sum((vm - vf).values()),
        "novas": sum((vf - vm).values()),
    }

    om = {o["type"]: o for o in mae["solution"]["outputs"]}
    of = {o["type"]: o for o in filha["solution"]["outputs"]}
    terra_m, terra_f = om.get("MovimentoDeTerra", {}), of.get("MovimentoDeTerra", {})
    terraplenagem = {
        k: {"mae": terra_m.get(k), "filha": terra_f.get(k)}
        for k in TERRA
        if terra_m.get(k) != terra_f.get(k)
    }
    mudaram = sorted(t for t in om.keys() & of.keys() if om[t] != of[t])
    indicadores = {
        t: {"mae": om[t]["value"], "filha": of[t]["value"]}
        for t in mudaram
        if "value" in om[t]
    }
    return {
        "torres_movidas": movidas,
        "vagas": vagas,
        "terraplenagem": terraplenagem,
        "indicadores": indicadores,
        "outros_indicadores_alterados": [t for t in mudaram if t not in indicadores],
        "indicadores_so_na_mae": sorted(om.keys() - of.keys()),
        "indicadores_so_na_filha": sorted(of.keys() - om.keys()),
    }


def caso(tarefa: str, arquivo: str, **campos: Any) -> dict:
    return {
        "tarefa": tarefa,
        "arquivo": arquivo,
        "pergunta": PERGUNTAS[tarefa],
        **campos,
    }


def casos_historico(indice: dict[str, dict]) -> list[dict]:
    por_tool: dict[tuple[str, str], list[tuple[str, dict]]] = {}
    for k, v in indice.items():
        por_tool.setdefault((v["arquivo"], v["tool"]), []).append((k, v))
    load = lambda v: json.loads((ROOT / v["aqg"]).read_text())  # noqa: E731

    casos = []
    for (arquivo, tool), entradas in sorted(por_tool.items()):
        if tool != "mover_torre":
            continue
        k1, d1 = entradas[0]
        if d1["veredito"] != "valido":
            continue
        _, base = por_tool[(arquivo, "base")][0]
        mae, filha = load(base), load(d1)
        resposta = diferenca(mae, filha)
        # Conferência contra as gravações: a única torre movida é a da D1, no vetor
        # pedido (5 m para os fundos).
        movidas = resposta["torres_movidas"]
        assert [m["mae"] for m in movidas] == [d1["args"]["torre"]], (arquivo, movidas)
        assert abs(movidas[0]["distancia"] - 5.0) < 1e-3, (arquivo, movidas)
        casos.append(
            caso(
                "G4",
                arquivo,
                historico=[base["aqg"], d1["aqg"]],
                edicoes=[{"tool": "mover_torre", "args": d1["args"]}],
                chamadas_esperadas=[
                    {"tool": "diff_versoes", "args": {"mae": 0, "filha": 1}}
                ],
                estado_esperado=d1["aqg"],
                resposta_esperada=resposta,
            )
        )

        seq = [
            (k, v)
            for k, v in por_tool.get((arquivo, "resolver_terraplenagem"), [])
            if v["args"].get("apos") == k1 and v["veredito"] == "valido"
        ]
        if not seq:
            continue
        _, e7 = seq[0]
        # A E7 não mexe nas torres da D1; desfazer as duas volta à base.
        assert _torres(load(e7)) == _torres(filha), arquivo
        casos.append(
            caso(
                "G5",
                arquivo,
                historico=[base["aqg"], d1["aqg"], e7["aqg"]],
                edicoes=[
                    {"tool": "mover_torre", "args": d1["args"]},
                    {"tool": "resolver_terraplenagem", "args": e7["args"]},
                ],
                chamadas_esperadas=[{"tool": "desfazer", "args": {"n": 2}}],
                estado_esperado=base["aqg"],
                resposta_esperada=None,
            )
        )
    return casos
