"""Tools de cálculo entregues à RECOD (D4): geometria sem motor, sobre dado gravado."""

import heapq
import json
import math
from pathlib import Path

from src.cad.geometry import _orient, distance_point_segment, segments_cross

REDES = Path(__file__).resolve().parents[3] / "data" / "benchmark" / "redes"
TIE = 0.01
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


def caminho(arquivo: str, origem: str, destino: str) -> dict:
    """Distância de carro de `origem` a `destino` (ids `p<i>` de portaria ou torre).

    Menor caminho na rede que o teseu refaz, entre os pontos das ruas mais próximos
    do `/road_access` de cada um (P1, projetado na aresta). Pontos empatados a menos
    de 1 cm do acesso valem todos: fica o de menor caminho, o primeiro ponto do
    acesso que o carro alcança. Os afastamentos dizem quanto cada acesso fica fora
    da rede.
    """
    path = REDES / f"{Path(arquivo).stem}.json"
    if not path.exists():
        return {"erro": "sem rede viária gravada para este arquivo"}
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
