"""Gravações das tarefas de edição (lado Arqgen; IMPLEMENTATION-queries.md, G1+).

Cada tarefa resolve a referência por descrição com o parser deste repo, sobre o AQG
cru, e passa a edição pela cascata de `gravacao.aplicar`. Arquivo em que a descrição
não aponta um elemento só (empate abaixo de `TIE`) fica fora da tarefa.

    cd <viabiliza-terrenos.backend>/packages/py && ../../venv/bin/python \\
        <repo>/evals/benchmark/edicoes.py [d1 d3 d6 e1 e3] [arquivos]

Sem tarefas, roda todas; sem arquivos, todos os admitidos.
"""

import json
import math
import sys
import uuid
from pathlib import Path
from typing import Any

from buildings.family.construction import build_families
from buildings.family.variations.empena_cega import calc_empena_cega
from buildings.family.variations.height import (
    _calc_expected_parking_spots,
    _gen_family_variation,
    _gen_tower_height_variation,
    gen_floor_heights_spec,
    gen_max_floors_with_units,
    gen_min_floors_with_units,
)
from buildings.protocol.archprog import MaxHeight
from buildings.protocol.family import Families
from buildings.protocol.id import VolumeId
from buildings.protocol.project import Project, build_project
from gravacao import AQG, ROOT, SPECS, TOWER, aplicar, gravar, tower_ids
from persistente.hid import Hid
from pyrsistent import pvector
from shapely.geometry import shape

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
FAMILIES = ROOT / "data" / "families"
# E3: as variantes simples (sem varanda, sem suíte) do catálogo comercial.
MIX_E3 = {"/building/apartamento/2q/40_71": 60, "/building/apartamento/1q/27_97": 40}
PROGRAMA = ("FamilyProportion", "StaticFamilyProportion", "FamilySelection")
FORMATOS = {"I", "L", "U", "H"}
# arquivo admitido -> catálogo de origem
ADMITIDOS = {
    r["arquivo"]: r["catalogo"]
    for r in json.loads(Path(__file__).with_name("admissao.json").read_text())
    if r["admitido"]
}
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


def tipo_irmao(project: Project, family: Any, total: int) -> Any:
    """A família `Tower` com `total` pavimentos: altura, afastamento e quantidades
    refeitos como `_compute_tower_property`; a planta do pavimento-tipo não muda."""
    p = family.properties
    cobertura = 1 if p.altura_cobertura > 0 else 0
    pav_tipo = p.pav_tipo.set(n=total - cobertura - 1)
    n_unidades = pav_tipo.n + (p.terreo.n if p.terreo_com_unidades else 0)
    props = p.set(
        total_pavimentos=total, pav_tipo=pav_tipo, n_pavimentos_unidades=n_unidades
    )
    variation = _gen_tower_height_variation(
        props, SPECS.config, project.site.inputs
    ).unwrap()
    base = family.set(
        volume=pvector(
            g for g in family.volume if g.class_path not in VolumeId.afastamento()
        ),
        drawing_elements=pvector(
            d for d in family.drawing_elements if d.label != "afastamento"
        ),
        class_path=Hid(str(family.class_path).rsplit("/", 1)[0]),
    )
    empena = calc_empena_cega(project.archprog, SPECS)
    sibling = _gen_family_variation(variation, family=base, empena_cega=empena)
    return sibling.unwrap().set(properties=props.set(afastamento=variation.afastamento))


def faixa_pavimentos(project: Project, family: Any) -> tuple[int, int]:
    """(mínimo, máximo) de pavimentos com unidades que o programa permite."""
    p = family.properties
    archprog = project.archprog
    heights = gen_floor_heights_spec(SPECS.config, archprog).unwrap()
    max_height = archprog.get_item(MaxHeight)
    maximo = gen_max_floors_with_units(
        archprog,
        project.site.inputs,
        max_height.value if max_height else float("inf"),
        heights,
        None,
        units_per_floor=sum(p.pav_tipo.tipologias.values()),
        unidades_terreo=sum(p.terreo.tipologias.values())
        if p.terreo_com_unidades
        else 0,
    )
    return gen_min_floors_with_units(archprog, heights), maximo


def trocar_familia(torre: str, family: Any):
    i = int(torre[1:])

    def edit(project: Project) -> Project:
        po = project.solution.placed_objects[i]
        uid = str(po.hid).rsplit("/", 1)[1]
        if all(f.class_path != family.class_path for f in project.families):
            project = project.set(families=project.families.append(family))
        hid = f"{family.class_path}/{uid}"
        return project.transform(["solution", "placed_objects", i, "hid"], hid)

    return edit


def formato(class_path: str, origem: dict[str, str]) -> str | None:
    """I, L, U ou H: do caminho, nas torres do tetris; do catálogo, nas estáticas."""
    segs = class_path.split("/")
    if segs[3] in FORMATOS:
        return segs[3]
    return origem.get("/".join(["", "building", "pav_tipo", *segs[3:-1]]))


def pegada(family: Any) -> float:
    return sum(
        shape(g.geometry).area
        for g in family.volume
        if str(g.class_path).startswith("/core")
    )


def equivalente(
    original: Any, candidatas: list[Any], origem: dict[str, str]
) -> Any | None:
    """Regra de família equivalente (2.5), sem formato pedido."""
    alvo = formato(str(original.class_path), origem)
    if alvo is not None:
        candidatas = [c for c in candidatas if formato(str(c.class_path), {}) == alvo]
    p = original.properties

    def por_andar(f: Any) -> int:
        return sum(f.properties.pav_tipo.tipologias.values())

    return min(
        candidatas,
        key=lambda c: (
            abs(c.properties.total_pavimentos - p.total_pavimentos),
            abs(por_andar(c) - por_andar(original)),
            pegada(c),
            str(c.class_path),
        ),
        default=None,
    )


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


def d6(arquivo: str, raw: dict, model: CadModel) -> dict:
    portaria = [
        prim
        for inst in model.instances.values()
        if _category(inst.family_type) == "portaria"
        for eid in inst.entity_ids
        for prim in model.by_id[eid].prims
    ]
    if not portaria:
        return {"tarefa": "D6", "arquivo": arquivo, "fora": "sem portaria"}
    torre, motivo = nearest_tower(model, portaria)
    if torre is None:
        return {"tarefa": "D6", "arquivo": arquivo, "fora": motivo}
    total = 20
    args = {"torre": torre, "total": total}
    original = Project.create(raw)
    po = original.solution.placed_objects[int(torre[1:])]
    family = next(f for f in original.families if f.class_path == po.hid.nonunique())
    edit = trocar_familia(torre, tipo_irmao(original, family, total))
    row = {"tarefa": "D6", "arquivo": arquivo, "torre": torre}
    minimo, maximo = faixa_pavimentos(original, family)
    n_unidades = total - (1 if family.properties.altura_cobertura > 0 else 0)
    n_unidades -= 0 if family.properties.terreo_com_unidades else 1
    if not minimo <= n_unidades <= maximo:
        regra = "MaxPavimentos" if n_unidades > maximo else "MinPavimentos"
        resposta = {
            "veredito": "invalido",
            "violacoes": [{"regra": regra, "torres": [torre]}],
            "etapas": ["validar"],
            "pavimentos_com_unidades": {
                "pedido": n_unidades,
                "minimo": minimo,
                "maximo": maximo,
            },
        }
        return {
            **row,
            **gravar(arquivo, "definir_pavimentos", args, edit(original), resposta),
        }
    return {**row, **aplicar(arquivo, original, "definir_pavimentos", args, edit)}


def e3(arquivo: str, raw: dict, model: CadModel) -> dict:
    args = {"mix": MIX_E3}
    row = {"tarefa": "E3", "arquivo": arquivo}
    archprog = [a for a in raw["archprog"] if a["type"] not in PROGRAMA]
    archprog += [
        {"type": "FamilyProportion", "hid": hid, "value": v}
        for hid, v in MIX_E3.items()
    ]
    novo = Project.create({**raw, "archprog": archprog})
    comercial = Families.create(
        json.loads((FAMILIES / "comercial-vba.json").read_text())
    )
    built = build_families(
        build_project(
            client_id="vba",
            site=novo.site,
            user="benchmark",
            archprog=novo.archprog,
            seed=0,
        ).unwrap(),
        SPECS,
        comercial,
    )
    if built.is_err():
        resposta = {"veredito": "erro", "violacoes": [], "erro": str(built)[:300]}
        return {**row, **gravar(arquivo, "alterar_programa", args, None, resposta)}
    # O tetris dá `_id` aleatório e as datas da execução: fixados para regravar
    # dar o mesmo AQG.
    candidatas = [
        f.set(
            _id=str(uuid.uuid5(uuid.NAMESPACE_URL, str(f.class_path))),
            created_at="",
            updated_at="",
        )
        for f in built.unwrap().families
        if str(f.class_path).startswith(TOWER)
    ]
    origem = {
        f["class_path"]: f["properties"].get("formato")
        for f in json.loads((FAMILIES / f"{ADMITIDOS[arquivo]}.json").read_text())
        if "/pav_tipo/" in f["class_path"]
    }
    original = Project.create(raw)
    families = {str(f.class_path): f for f in original.families}
    trocas: dict[str, Any] = {}
    for torre, family_hid, _ in tower_ids(original):
        nova = equivalente(families[family_hid], candidatas, origem)
        if nova is None:
            resposta = {
                "veredito": "erro",
                "violacoes": [],
                "erro": "troca impossível com este programa",
            }
            return {**row, **gravar(arquivo, "alterar_programa", args, None, resposta)}
        trocas[torre] = nova
    row["trocas"] = {t: str(f.class_path) for t, f in trocas.items()}

    def edit(project: Project) -> Project:
        project = project.set(archprog=novo.archprog)
        for torre, family in trocas.items():
            project = trocar_familia(torre, family)(project)
        return project

    entry = aplicar(arquivo, original, "alterar_programa", args, edit, repor=True)
    return {**row, **entry}


def recalcular_vagas(family: Any, archprog: Any) -> Any:
    """`vagas_necessarias` de cada pavimento da torre com o programa novo (fato 4)."""
    if not str(family.class_path).startswith(TOWER):
        return family
    p = family.properties
    pavs = {
        nome: getattr(p, nome).set(
            vagas_necessarias=_calc_expected_parking_spots(
                getattr(p, nome).tipologias, archprog
            )
        )
        for nome in ("pav_tipo", "terreo")
    }
    return family.set(properties=p.set(**pavs))


def e1(arquivo: str, raw: dict, model: CadModel) -> dict:
    row = {"tarefa": "E1", "arquivo": arquivo}
    if "parking_lot" not in json.dumps(raw["solution"]["strategy"]):
        return {**row, "fora": "sem estacionamento"}
    args = {"chave": "ParkingLotPerUnit", "valor": 1.5}
    archprog = [
        {**a, "value": 1.5} if a["type"] == "ParkingLotPerUnit" else a
        for a in raw["archprog"]
    ]
    novo = Project.create({**raw, "archprog": archprog}).archprog

    def edit(project: Project) -> Project:
        families = pvector(recalcular_vagas(f, novo) for f in project.families)
        return project.set(archprog=novo, families=families)

    return {
        **row,
        **aplicar(arquivo, Project.create(raw), "alterar_programa", args, edit),
    }


def main() -> None:
    tarefas = {"d1": d1, "d3": d3, "d6": d6, "e1": e1, "e3": e3}
    names = [a for a in sys.argv[1:] if a in tarefas]
    tasks = [tarefas[n] for n in names] or list(tarefas.values())
    only = set(sys.argv[1:]) - set(names)
    for arquivo in ADMITIDOS:
        if only and arquivo not in only:
            continue
        data = (AQG / arquivo).read_bytes()
        raw = json.loads(data)
        model = load_aqg(data, arquivo)
        for task in tasks:
            row = task(arquivo, raw, model)
            keep = ("tarefa", "torre", "fora", "veredito", "violacoes", "erro")
            extra = (
                "unidades_perdidas",
                "vagas",
                "reposicionadas",
                "removidas",
                "segundos",
            )
            shown = {k: row[k] for k in (*keep, *extra) if row.get(k) is not None}
            print(shown, arquivo)


if __name__ == "__main__":
    main()
