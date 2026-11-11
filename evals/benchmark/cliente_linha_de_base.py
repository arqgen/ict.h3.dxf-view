"""Linha de base (D10) nas tarefas de leitura: um roteiro por tarefa que responde só
com as 16 tools deste repo, conferido contra `casos.json`.

Mede a cobertura das tools, não um modelo: o roteiro faz o que um modelo
perfeito faria com as saídas (incluindo a aritmética, porque a linha de base
não tem `calcular`).

    uv run python -m evals.benchmark.cliente_linha_de_base
"""

import json
import math
from collections import Counter
from collections.abc import Callable
from decimal import ROUND_FLOOR, Decimal
from pathlib import Path
from typing import Any

from evals.benchmark.historico import ROOT
from evals.benchmark.tools import GRUPOS

CASOS = Path(__file__).parent / "casos.json"
TOOLS = GRUPOS["linha_de_base"]
RAIO_VAGA = 50.0
SEM_COBERTURA = {
    "B5": "nenhuma tool expõe a rede viária; `measure` só dá distância em linha reta",
    "B8": "nenhuma tool expõe `solution.strategy`",
}


class Sessao:
    """Chama as tools no estado do caso e conta as chamadas."""

    def __init__(self, estado: str) -> None:
        self.estado = estado
        self.chamadas: list[str] = []

    def __call__(self, tool: str, **args: Any) -> dict:
        self.chamadas.append(tool)
        return TOOLS[tool](self.estado, **args)

    def indicadores(self, *tipos: str) -> dict[str, dict]:
        out = self("get_project_indicators", tipos=list(tipos))
        grupos = (out.get(k, []) for k in ("indicadores", "exigidos", "terreno"))
        return {i["type"]: i for grupo in grupos for i in grupo}

    def instancias(self, tipo_familia: str) -> list[str]:
        familias = self("count_entities", group_by="family")["tipo_de_cada_familia"]
        ids: list[str] = []
        for familia, tipo in familias.items():
            if tipo == tipo_familia:
                ids += self("query_entities", family=familia, limit=1)["instancias"]
        return ids

    def mais_proxima(self, torres: list[str], alvos: list[str]) -> str:
        def dist(t: str) -> float:
            return min(
                self("measure", ids=[t, a], metric="edge_distance")["distancia"]
                for a in alvos
            )

        return min(torres, key=dist)


def _torres(s: Sessao) -> list[str]:
    return s.instancias("Tower") + s.instancias("DynamicTower3d")


def l1(s: Sessao) -> Any:
    return len(_torres(s))


def l2(s: Sessao) -> Any:
    ind = s.indicadores("CAMaximoExigido", "CAProjetado")
    return {k: ind[k]["value"] for k in ("CAMaximoExigido", "CAProjetado")}


def l3(s: Sessao) -> Any:
    return len(s.instancias("Vaga"))


def l4(s: Sessao) -> Any:
    frente = s("query_entities", layer="AQG_FRENTE")["ids"]
    torre = s.mais_proxima(_torres(s), frente)
    det = s("get_entity_details", entity_id=torre)
    return {
        "familia": det["familia"],
        "total_pavimentos": det["propriedades_familia"]["total_pavimentos"],
    }


def l5(s: Sessao) -> Any:
    return s.indicadores("UnidadesPorTipologia")["UnidadesPorTipologia"]["value"]


def l6(s: Sessao) -> Any:
    ind = s.indicadores("AreaDoTerreno", "AreaUtil")
    return {k: ind[k]["value"] for k in ("AreaDoTerreno", "AreaUtil")}


def l7(s: Sessao) -> Any:
    # Elemento do terreno é o de id `s<i>` (convenção das instruções do agente).
    layers = [c["nome"] for c in s("list_layers")["layers"]]
    return sorted(
        nome
        for nome in layers
        if any(i.startswith("s") for i in s("query_entities", layer=nome)["ids"])
    )


def l8(s: Sessao) -> Any:
    ind = s.indicadores("AfastamentoProjetado")
    return ind["AfastamentoProjetado"]["entre_blocos"]


def a1(s: Sessao) -> Any:
    ind = s.indicadores(
        "AreaBaseDeCalculo",
        "AreaDeMatricula",
        "AreaDoTerreno",
        "CAMaximoExigido",
        "AreaTotalConstruidaComputavel",
        "TotalDeUnidades",
    )
    base = ind["AreaDoTerreno"]["value"]
    usa_matricula = ind.get("AreaBaseDeCalculo", {}).get("value") == "AreaDeMatricula"
    if usa_matricula and "AreaDeMatricula" in ind:
        base = ind["AreaDeMatricula"]["value"]
    d = lambda k: Decimal(str(ind[k]["value"]))  # noqa: E731
    por_unidade = d("AreaTotalConstruidaComputavel") / d("TotalDeUnidades")
    estimativa = Decimal(str(base)) * d("CAMaximoExigido") / por_unidade
    return int(estimativa.to_integral_value(rounding=ROUND_FLOOR))


def b2(s: Sessao) -> Any:
    tipos = ("EstacionamentoProjetado", "ViarioProjetado", "VagasProjetadas")
    ind = s.indicadores(*tipos, "ProjecaoTorres")
    return {
        k: {"area": ind[k]["area"], "percentual": ind[k]["percentual"]}
        for k in (*tipos, "ProjecaoTorres")
        if k in ind
    }


def b9(s: Sessao) -> Any:
    longe = []
    for torre in _torres(s):
        perto = s("query_entities", entity_type="vaga", near=torre, limit=1)
        if perto["entidades"][0]["distancia"] > RAIO_VAGA:
            longe.append(torre)
    return {"torres_sem_vaga_em_50m": sorted(longe), "existe": bool(longe)}


def b11(s: Sessao) -> Any:
    torre = s.mais_proxima(_torres(s), s.instancias("Portaria"))
    det = s("get_entity_details", entity_id=torre)
    n = det["propriedades_familia"]["n_pavimentos_unidades"]
    return det["unidades_por_pavimento"] * min(5, n)


ROTEIROS: dict[str, Callable[[Sessao], Any]] = {
    "L1": l1,
    "L2": l2,
    "L3": l3,
    "L4": l4,
    "L5": l5,
    "L6": l6,
    "L7": l7,
    "L8": l8,
    "A1": a1,
    "B2": b2,
    "B9": b9,
    "B11": b11,
}


def responder(caso: dict) -> tuple[Any, int]:
    s = Sessao(str(ROOT / "data" / "aqg" / caso["arquivo"]))
    try:
        resposta = ROTEIROS[caso["tarefa"]](s)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        resposta = {"erro": f"{type(exc).__name__}: {exc}"}
    return resposta, len(s.chamadas)


def main() -> None:
    casos = [c for c in json.loads(CASOS.read_text()) if c["status"] == "ok"]
    confere: Counter = Counter()
    total: Counter = Counter()
    chamadas: dict[str, list[int]] = {}
    for caso in casos:
        tarefa = caso["tarefa"]
        total[tarefa] += 1
        if tarefa in SEM_COBERTURA:
            continue
        resposta, n = responder(caso)
        chamadas.setdefault(tarefa, []).append(n)
        if resposta == caso["resposta_esperada"]:
            confere[tarefa] += 1
        else:
            print(
                f"  {tarefa} {caso['arquivo']}: {resposta!r:.200} != "
                f"{caso['resposta_esperada']!r:.200}"
            )
    for tarefa in total:
        if tarefa in SEM_COBERTURA:
            print(f"{tarefa}: sem cobertura ({SEM_COBERTURA[tarefa]})")
            continue
        media = math.fsum(chamadas[tarefa]) / len(chamadas[tarefa])
        print(f"{tarefa}: {confere[tarefa]}/{total[tarefa]} ({media:.1f} chamadas)")


if __name__ == "__main__":
    main()
