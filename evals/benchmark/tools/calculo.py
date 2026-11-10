"""Tools de cálculo entregues à RECOD (D4): geometria sem motor, sobre dado gravado.

`estado` é o caminho do AQG atual: quem passa é o harness, não o modelo.
"""

import ast
import heapq
import json
import math
import operator
from functools import lru_cache
from pathlib import Path
from typing import Literal

from agno.run.base import RunContext

from src.ai_modules.tools.cad_tools.query_tools import _edge_prims, measure
from src.cad.geometry import (
    _orient,
    distance_point_segment,
    min_distance,
    segments_cross,
)
from src.cad.model import AqgLoadError, CadModel, load_aqg

ROOT = Path(__file__).resolve().parents[3]
REDES = ROOT / "data" / "benchmark" / "redes"
TIE = 0.01
OPERADORES = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}
METRICAS = {"comprimento": "length", "area": "area", "distancia": "edge_distance"}
Node = tuple[float, float]
Linhas = list[list[list[float]]]
Rua = list[list[float]]


def _segmentos(linhas: Linhas) -> list[tuple[Node, Node]]:
    """Segmentos 2D do acesso; um ponto solto vira segmento degenerado."""
    out = []
    for part in linhas:
        pts = [(p[0], p[1]) for p in part]
        pares = zip(pts, pts[1:], strict=False)
        out.extend(pares if len(pts) > 1 else [(pts[0], pts[0])])
    return out


def _no(rua: Rua, t: float) -> Node:
    (ax, ay, *_), (bx, by, *_) = rua
    return (round(ax + t * (bx - ax), 3), round(ay + t * (by - ay), 3))


def _param(p: Node, a: Node, b: Node) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = dx * dx + dy * dy
    if n == 0.0:
        return 0.0
    return max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / n))


def _ancoras(ruas: list[Rua], linhas: Linhas) -> tuple[list[tuple[int, float]], float]:
    """Pontos da rede (aresta, t) mais próximos do acesso, com empate de 1 cm.

    Entre dois segmentos, o ponto mais próximo é sempre uma ponta, a projeção de uma
    ponta do outro ou o cruzamento; na sobreposição, as pontas dela estão entre eles.
    """
    segs = _segmentos(linhas)
    cands: list[tuple[int, float, float]] = []
    for i, rua in enumerate(ruas):
        a, b = _no(rua, 0.0), _no(rua, 1.0)
        ts = {0.0, 1.0}
        for p, q in segs:
            ts |= {_param(p, a, b), _param(q, a, b)}
            if segments_cross(a, b, p, q):
                ts.add(_orient(p, q, a) / (_orient(p, q, a) - _orient(p, q, b)))
        for t in ts:
            no = _no(rua, t)
            d = min(distance_point_segment(no, p, q) for p, q in segs)
            cands.append((i, t, d))
    d0 = min(d for _, _, d in cands)
    return [(i, t) for i, t, d in cands if d - d0 < TIE], d0


def caminho(estado: str, origem: str, destino: str) -> dict:
    """Distância de carro de `origem` a `destino` (ids `p<i>` de portaria ou torre).

    Menor caminho na rede que o teseu refaz, entre os pontos das ruas mais próximos
    do `/road_access` de cada um (P1, projetado na aresta). Pontos empatados a menos
    de 1 cm do acesso valem todos: fica o de menor caminho, o primeiro ponto do
    acesso que o carro alcança. Os afastamentos dizem quanto cada acesso fica fora
    da rede.
    """
    path = REDES / f"{Path(estado).stem}.json"
    if not path.exists():
        return {"erro": "sem rede viária gravada para este estado"}
    rede = json.loads(path.read_text())
    ruas: list[Rua] = rede["ruas"]

    for ref in (origem, destino):
        acesso = rede["acessos"].get(ref)
        if acesso is None:
            return {"erro": f"{ref} não é portaria nem torre deste arquivo"}
        if not acesso["linhas"]:
            return {"erro": f"{ref} não tem acesso viário (/road_access)"}
    fontes, d_origem = _ancoras(ruas, rede["acessos"][origem]["linhas"])
    alvos, d_destino = _ancoras(ruas, rede["acessos"][destino]["linhas"])

    # Os pontos de acesso viram nós: cada rua é partida neles.
    cortes: dict[int, set[float]] = {i: {0.0, 1.0} for i in range(len(ruas))}
    for i, t in fontes + alvos:
        cortes[i].add(t)
    grafo: dict[Node, list[tuple[Node, float]]] = {}
    for i, rua in enumerate(ruas):
        comprimento = math.dist(*rua)
        ts = sorted(cortes[i])
        for t1, t2 in zip(ts, ts[1:], strict=False):
            n1, n2, w = _no(rua, t1), _no(rua, t2), comprimento * (t2 - t1)
            grafo.setdefault(n1, []).append((n2, w))
            grafo.setdefault(n2, []).append((n1, w))

    inicio = {_no(ruas[i], t) for i, t in fontes}
    dist = {no: 0.0 for no in inicio}
    fila = [(0.0, no) for no in inicio]
    while fila:
        d, no = heapq.heappop(fila)
        if d > dist[no]:
            continue
        for viz, w in grafo[no]:
            if d + w < dist.get(viz, math.inf):
                dist[viz] = d + w
                heapq.heappush(fila, (d + w, viz))

    alcancados = [n for n in {_no(ruas[i], t) for i, t in alvos} if n in dist]
    if not alcancados:
        return {
            "erro": "inalcançável",
            "motivo": f"o acesso de {destino} fica num trecho da rede sem ligação "
            f"com o acesso de {origem}",
        }
    return {
        "origem": origem,
        "destino": destino,
        "distancia": round(min(dist[n] for n in alcancados), 2),
        "afastamento_origem": round(d_origem, 2),
        "afastamento_destino": round(d_destino, 2),
    }


def contexto(model: CadModel) -> RunContext:
    """O `RunContext` que as tools deste repo esperam, com o documento do estado."""
    return RunContext(
        run_id="benchmark", session_id="benchmark", dependencies={"cad": model}
    )


@lru_cache(maxsize=8)
def modelo(estado: str) -> CadModel:
    """O AQG do estado, pelo parser deste repo (o mesmo índice das tools atuais)."""
    path = Path(estado) if Path(estado).is_absolute() else ROOT / estado
    return load_aqg(path.read_bytes(), path.name)


def _carregar(estado: str) -> CadModel | dict:
    try:
        return modelo(estado)
    except (OSError, AqgLoadError) as exc:
        return {"erro": f"estado ilegível: {exc}"}


def calcular(expressao: str) -> dict:
    """Calcula uma expressão aritmética com valores lidos na estrutura.

    Aceita números, `+ - * / **` e parênteses; nada de nomes ou funções.

    Args:
        expressao: por exemplo "120 * 0.5 + 3" ou "(8000 - 1200) / 8000".
    """

    def avaliar(no: ast.AST) -> float:
        if isinstance(no, ast.Constant) and isinstance(no.value, int | float):
            return no.value
        if isinstance(no, ast.BinOp) and type(no.op) in OPERADORES:
            return OPERADORES[type(no.op)](avaliar(no.left), avaliar(no.right))
        if isinstance(no, ast.UnaryOp) and type(no.op) in OPERADORES:
            return OPERADORES[type(no.op)](avaliar(no.operand))
        raise ValueError(f"elemento não permitido: {ast.dump(no)[:60]}")

    try:
        valor = avaliar(ast.parse(expressao, mode="eval").body)
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError) as exc:
        return {"erro": str(exc)}
    return {"expressao": expressao, "resultado": round(valor, 6)}


def medir(
    estado: str, ids: list[str], metrica: Literal["comprimento", "area", "distancia"]
) -> dict:
    """Mede entidades do desenho.

    Na distância, uma torre (`p<i>`) vale pelo pavimento-tipo desenhado.

    Args:
        ids: ids das entidades; o id da instância (`p<i>`) vale por todas as partes.
        metrica: "comprimento" e "area" somam sobre os ids; "distancia" exige
            exatamente 2 ids e devolve a menor distância entre as bordas.
    """
    model = _carregar(estado)
    if isinstance(model, dict):
        return model
    ctx = contexto(model)
    resultado = json.loads(measure.entrypoint(ctx, ids, METRICAS[metrica]))
    resultado.pop("resumo", None)
    return resultado


def relacao_espacial(
    estado: str,
    ids: list[str],
    alvo: list[str],
    tipo: Literal["mais_proximo", "dentro_do_raio"],
    raio: float | None = None,
) -> dict:
    """Relaciona cada id com o alvo pela menor distância entre as bordas.

    Uma torre (`p<i>`) vale pelo pavimento-tipo desenhado; o alvo é o conjunto de
    todas as geometrias dos ids dele (ex.: as linhas da frente, todas as vagas).

    Args:
        ids: os candidatos (ex.: as torres).
        alvo: ids do que se mede contra (ex.: a portaria, as linhas da frente).
        tipo: "mais_proximo" ordena os ids pela distância ao alvo e aponta o mais
            próximo, ou o empate (diferença abaixo de 1 cm); "dentro_do_raio" diz,
            para cada id, se a distância ao alvo é no máximo `raio`.
        raio: em metros; obrigatório em "dentro_do_raio".
    """
    model = _carregar(estado)
    if isinstance(model, dict):
        return model
    alvo_prims = [prim for ref in alvo for prim in _edge_prims(model, ref)]
    if not alvo_prims:
        return {"erro": "alvo sem geometria", "alvo": alvo}
    dist = {}
    rejeitados = []
    for ref in ids:
        prims = _edge_prims(model, ref)
        if prims:
            dist[ref] = min_distance(prims, alvo_prims)
        else:
            rejeitados.append(ref)
    if not dist:
        return {"erro": "nenhum id com geometria", "rejeitados": rejeitados}

    if tipo == "dentro_do_raio":
        if raio is None:
            return {"erro": "dentro_do_raio exige raio"}
        return {
            "raio": raio,
            "por_id": {
                ref: {"distancia": round(d, 3), "dentro": d <= raio}
                for ref, d in dist.items()
            },
            "rejeitados": rejeitados,
        }
    ranking = sorted(dist.items(), key=lambda item: item[1])
    empate = [ref for ref, d in ranking if d - ranking[0][1] < TIE]
    return {
        "mais_proximo": empate[0] if len(empate) == 1 else None,
        "empate": empate if len(empate) > 1 else [],
        "ranking": [{"id": ref, "distancia": round(d, 3)} for ref, d in ranking],
        "rejeitados": rejeitados,
    }
