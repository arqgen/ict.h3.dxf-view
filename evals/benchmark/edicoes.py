"""Gravações das tarefas de edição (lado Arqgen; IMPLEMENTATION-queries.md, G1+).

Cada tarefa resolve a referência por descrição com o parser deste repo, sobre o AQG
cru, e passa a edição pela cascata de `gravacao.aplicar`. Arquivo em que a descrição
não aponta um elemento só (empate abaixo de `TIE`) fica fora da tarefa.

    cd <viabiliza-terrenos.backend>/packages/py && ../../venv/bin/python \\
        <repo>/evals/benchmark/edicoes.py
"""

import json
import math
import sys
from pathlib import Path
from typing import Any

from buildings.protocol.project import Project
from gravacao import AQG, ROOT, aplicar
from pyrsistent import pvector

sys.path.insert(0, str(ROOT))
from src.cad.geometry import (  # noqa: E402
    PolylinePrim,
    Prim,
    distance_point_segment,
    min_distance,
    point_in_polygon,
)
from src.cad.model import CadModel, _category, load_aqg  # noqa: E402

TIE = 0.01
Vec2 = tuple[float, float]


def tower_prims(model: CadModel) -> dict[str, list[Prim]]:
    """Torre vale pelo pavimento-tipo desenhado, como em `relacao_espacial`."""
    return {
        inst.id: [
            prim
            for eid in inst.entity_ids
            if model.by_id[eid].layer == "pav_tipo"
            for prim in model.by_id[eid].prims
        ]
        for inst in model.instances.values()
        if _category(inst.family_type) == "torre"
    }


def layer_prims(model: CadModel, layer: str) -> list[Prim]:
    return [prim for e in model.entities if e.layer == layer for prim in e.prims]


def nearest_tower(model: CadModel, target: list[Prim]) -> tuple[str | None, str]:
    """(torre, motivo): None quando falta referência ou há empate."""
    towers = tower_prims(model)
    if not target or not towers:
        return None, "sem referência ou torre"
    rank = sorted((min_distance(p, target), t) for t, p in towers.items())
    if len(rank) > 1 and rank[1][0] - rank[0][0] < TIE:
        return None, f"empate entre {rank[0][1]} e {rank[1][1]} a {rank[0][0]:.3f} m"
    return rank[0][1], f"a {rank[0][0]:.3f} m"


def segments(prims: list[Prim]) -> list[tuple[Vec2, Vec2]]:
    out = []
    for p in prims:
        if not isinstance(p, PolylinePrim):
            continue
        pts = p.pts + p.pts[:1] if p.closed else p.pts
        out += list(zip(pts, pts[1:], strict=False))
    return out


def rumo_fundos(model: CadModel, torre: str) -> Vec2:
    """P2: perpendicular à linha de frente mais próxima da torre, para dentro."""
    tower = [pt for p in tower_prims(model)[torre] for pt in getattr(p, "pts", [])]
    a, b = min(
        segments(layer_prims(model, "AQG_FRENTE")),
        key=lambda s: min(distance_point_segment(pt, *s) for pt in tower),
    )
    length = math.dist(a, b)
    n = ((a[1] - b[1]) / length, (b[0] - a[0]) / length)
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    perimetro = max(
        (p for p in layer_prims(model, "AQG_PERIMETRO") if isinstance(p, PolylinePrim)),
        key=lambda p: len(p.pts),
    )
    probe = (mid[0] + n[0] * 0.5, mid[1] + n[1] * 0.5)
    return n if point_in_polygon(probe, perimetro.pts) else (-n[0], -n[1])


def mover(torre: str, delta: Vec2):
    i = int(torre[1:])

    def edit(project: Project) -> Project:
        po = project.solution.placed_objects[i]
        pos = po.position.set(x=po.position.x + delta[0], y=po.position.y + delta[1])
        return project.transform(["solution", "placed_objects", i, "position"], pos)

    return edit


def remover(torre: str):
    i = int(torre[1:])

    def edit(project: Project) -> Project:
        pos = project.solution.placed_objects
        return project.transform(
            ["solution", "placed_objects"], pvector([*pos[:i], *pos[i + 1 :]])
        )

    return edit


def total_unidades(raw: dict) -> Any:
    unidades = "TotalDeUnidades"
    return next(
        (o["value"] for o in raw["solution"]["outputs"] if o["type"] == unidades),
        None,
    )


def d1(arquivo: str, raw: dict, model: CadModel) -> dict:
    torre, motivo = nearest_tower(model, layer_prims(model, "AQG_FRENTE"))
    if torre is None:
        return {"tarefa": "D1", "arquivo": arquivo, "fora": motivo}
    n = rumo_fundos(model, torre)
    delta = (n[0] * 5.0, n[1] * 5.0)
    args = {"torre": torre, "distancia": 5.0, "sentido": "fundos"}
    entry = aplicar(
        arquivo, Project.create(raw), "mover_torre", args, mover(torre, delta)
    )
    return {"tarefa": "D1", "arquivo": arquivo, "torre": torre, "vetor": delta, **entry}


def d3(arquivo: str, raw: dict, model: CadModel) -> dict:
    app = layer_prims(model, "AQG_APP")
    if not app:
        return {"tarefa": "D3", "arquivo": arquivo, "fora": "sem APP"}
    torre, motivo = nearest_tower(model, app)
    if torre is None:
        return {"tarefa": "D3", "arquivo": arquivo, "fora": motivo}
    entry = aplicar(
        arquivo, Project.create(raw), "remover_torre", {"torre": torre}, remover(torre)
    )
    row = {"tarefa": "D3", "arquivo": arquivo, "torre": torre, **entry}
    if entry.get("veredito") == "valido":
        gravado = json.loads((ROOT / entry["aqg"]).read_text())
        row["unidades_perdidas"] = total_unidades(raw) - total_unidades(gravado)
    return row


def main() -> None:
    admitted = [
        r["arquivo"]
        for r in json.loads(Path(__file__).with_name("admissao.json").read_text())
        if r["admitido"]
    ]
    only = set(sys.argv[1:])
    for arquivo in admitted:
        if only and arquivo not in only:
            continue
        data = (AQG / arquivo).read_bytes()
        raw = json.loads(data)
        model = load_aqg(data, arquivo)
        for task in (d1, d3):
            row = task(arquivo, raw, model)
            keep = ("tarefa", "torre", "fora", "veredito", "violacoes", "erro")
            extra = ("unidades_perdidas", "segundos")
            shown = {k: row[k] for k in (*keep, *extra) if row.get(k) is not None}
            print(shown, arquivo)


if __name__ == "__main__":
    main()
