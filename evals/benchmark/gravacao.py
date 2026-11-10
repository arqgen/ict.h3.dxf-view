"""Núcleo de gravação do benchmark (lado Arqgen; IMPLEMENTATION-queries.md, G0).

Tudo o que roda motor mora aqui: a cascata de uma edição, o `validar` por partes
(D9) e o registro das gravações. Roda com o venv do viabiliza-terrenos (de onde vem
o `lib`), com cwd em `data/benchmark/bin`, onde ficam os binários nas versões da D8:
o checkout do VT acompanha as de produção. Nada deste módulo é entregue à RECOD (D1).

A cascata sempre refaz, a partir das torres, todas as etapas seguintes da strategy
do arquivo. As etapas que a edição não afeta saem idênticas, porque os motores são
determinísticos nos arquivos admitidos; a única exceção é a portaria, que não se
reproduz e por isso é preservada do arquivo, como no Eros.

    cd <repo>/data/benchmark/bin && <viabiliza-terrenos.backend>/venv/bin/python \\
        <repo>/evals/benchmark/gravacao.py [arquivos ou pastas]

Sem argumentos, confere a cascata sem edição (o estado inicial dos casos) em todo
`data/aqg/` e grava cada uma como base.
"""

import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

# A ordem de `families` no AQG gravado sai de sets: sem semente fixa, muda entre
# processos e regravar não dá o mesmo arquivo (1.2, determinismo).
if os.environ.get("PYTHONHASHSEED") != "0":
    os.execve(
        sys.executable,
        [sys.executable, *sys.argv],
        {**os.environ, "PYTHONHASHSEED": "0"},
    )

import lib.problem.earth_movement as earth_movement  # noqa: E402
from buildings.annotations import compute_annotations
from buildings.metrics.compute import compute_outputs
from buildings.protocol.client_specs import ClientSpecs, StepId
from buildings.protocol.inputs import CAMaximoExigido
from buildings.protocol.project import Project
from errata.result import Err, Ok, Result
from lib.config.client_specs import temp_get_client_specs
from lib.problem.pipeline import _gen_tower_config, _solve_step
from lib.problem.towers import _gen_problem
from lib.problem.towers.constraint import gen_tx_available_area_to_towers
from maga.ibitira.protocol import FeasibilitySolution
from pyrsistent import pvector

ROOT = Path(__file__).resolve().parents[2]
AQG = ROOT / "data" / "aqg"
GRAVACOES = ROOT / "data" / "benchmark" / "gravacoes"
INDICE = Path(__file__).with_name("gravacoes.json")
SPECS = temp_get_client_specs("default").unwrap()
TIMEOUT_MS = 260_000
FORMULATION = "inconsistency in the formulated problem"
BROAD = "agregado ou circulação"
TOWER = "/building/torre"
PORTARIA = "/building/portaria"
# D8: o conjunto que reproduziu o acervo.
VERSOES = {
    "teodora": "17.1.0",
    "teseu": "0.5.2",
    "ibitira": "5.2.0+adaptador",
    "minotauro": "2.0.0",
    "buildings": "19.3.0",
    "specs": "default",
}


def invoke_ibitira_v5(problem: Any, executable: str) -> Result:
    """Adaptador da D8: maga_ibitira 6 manda `road_graph` como lista de pares
    (largura, linhas); o binário 5.2.0 espera um par só."""
    payload = problem.serialize()
    graphs = payload["road_graph"]
    if len(graphs) > 1:
        return Err(f"adaptador: {len(graphs)} larguras de via, a v5 aceita uma")
    payload["road_graph"] = graphs[0] if graphs else [0.0, []]
    proc = subprocess.run(
        [executable, "feasibility"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=600,
    )
    if proc.returncode:
        return Err(f"ibitira: {proc.stderr[:200]}")
    return Ok(FeasibilitySolution.create(json.loads(proc.stdout)))


earth_movement.invoke_ibitira = invoke_ibitira_v5


def placed_with_prefix(project: Project, prefix: str) -> list[Any]:
    return [p for p in project.solution.placed_objects if str(p.hid).startswith(prefix)]


def only_towers(project: Project) -> Project:
    return project.transform(
        ["solution", "placed_objects"],
        lambda _: pvector(placed_with_prefix(project, TOWER)),
    )


def strategy_step(project: Project, step: StepId) -> Any:
    strategy = getattr(project.solution, "strategy", None) or []
    return next((p for p in strategy if p.step == step), None)


# --- validar (D9) ---------------------------------------------------------------


def teodora_problem(project: Project) -> dict:
    """O PositioningProblem do passo Tower, montado sem nada posicionado."""
    path = strategy_step(project, StepId.Tower)
    if path is None:
        raise ValueError("sem passo Tower na strategy")
    config = _gen_tower_config(project, SPECS.pipeline.get_config(path))
    empty = project.transform(["solution", "placed_objects"], lambda _: pvector())
    res = _gen_problem(empty, path, config, SPECS)
    if res.is_err():
        raise ValueError(f"formulação: {str(res)[:150]}")
    return res.unwrap()[1].serialize()


def check_problem(problem: dict, towers: list[tuple[str, dict]]) -> dict:
    """Receita do Eros: os moldes das torres saem e entra uma cópia fixa por torre."""
    by_id = {obj["id"]: obj for obj in problem["objects"]}
    moldes = {family for family, _ in towers}
    objects = [obj for obj in problem["objects"] if obj["id"] not in moldes]
    objects += [{**by_id[family], "position": dict(pos)} for family, pos in towers]
    return {
        "objects": objects,
        "constraints": problem.get("constraints") or [],
        "score_criteria": {},
        "grid_generators": [],
        "goals": [],
        "next_object": None,
    }


def run_teodora(problem: dict) -> tuple[str, str]:
    """(status, regra): status é valid, invalid ou unavailable."""
    proc = subprocess.run(
        ["./teodora", "positioning"],
        input=json.dumps(problem),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode == 0:
        return "valid", ""
    if FORMULATION in proc.stderr:
        rule = re.search(r"\[([A-Za-z]+)", proc.stderr.split(FORMULATION, 1)[1])
        return "invalid", rule.group(1) if rule else "desconhecida"
    if "broad" in proc.stderr.lower():
        return "invalid", BROAD
    return "unavailable", proc.stderr[:150]


def tower_ids(project: Project) -> list[tuple[str, str, dict]]:
    """(id do parser p<i>, família, posição) de cada torre, na ordem do arquivo."""
    return [
        (f"p{i}", str(po.hid.nonunique()), po.position.serialize())
        for i, po in enumerate(project.solution.placed_objects)
        if str(po.hid).startswith(TOWER)
    ]


def agregados_estourados(
    project: Project, problem: dict, families: list[str]
) -> list[str]:
    """Nome de cada `MaximumSum` que as torres estouram.

    O teodora só diz "broken broad constraint". Os tetos com nome são os mesmos que o
    gerador usa (`_gen_towers_exceeding_caps`): permeabilidade e CA; os demais saem
    como `MaximumSum`.
    """
    caps = []
    for name, cap in (
        ("PermeabilidadeExigida", gen_tx_available_area_to_towers(project)),
        ("CAMaximoExigido", project.site.inputs.get_input(CAMaximoExigido)),
    ):
        if cap.is_ok():
            value = cap.unwrap()
            caps.append((name, getattr(value, "value", value)))
    names = []
    for constraint in problem.get("constraints") or []:
        total_sum = constraint.get("MaximumSum")
        if not total_sum:
            continue
        total = sum(w * families.count(f) for f, w in total_sum["objects"])
        if total <= total_sum["amount"]:
            continue
        names.append(
            next(
                (n for n, v in caps if math.isclose(v, total_sum["amount"])),
                "MaximumSum",
            )
        )
    return names


def validar(project: Project) -> list[dict]:
    """Todas as violações das torres: cada uma sozinha, cada par e o conjunto."""
    problem = teodora_problem(project)
    towers = tower_ids(project)
    violacoes: list[dict] = []

    def check(subset: list[tuple[str, str, dict]]) -> tuple[str, str]:
        status, rule = run_teodora(
            check_problem(problem, [(f, p) for _, f, p in subset])
        )
        if rule == BROAD:
            named = agregados_estourados(project, problem, [f for _, f, _ in subset])
            rule = ", ".join(named) or rule
        return status, rule

    alone_ok = []
    for tower in towers:
        status, rule = check([tower])
        if status == "valid":
            alone_ok.append(tower)
        else:
            regra = rule if status == "invalid" else f"indisponível: {rule}"
            violacoes.append({"regra": regra, "torres": [tower[0]]})
    pairs_ok = True
    for i, a in enumerate(alone_ok):
        for b in alone_ok[i + 1 :]:
            status, rule = check([a, b])
            if status != "valid":
                pairs_ok = False
                violacoes.append({"regra": rule, "torres": [a[0], b[0]]})
    if not violacoes and pairs_ok and len(towers) > 2:
        status, rule = check(towers)
        if status != "valid":
            violacoes.append({"regra": rule, "torres": [t[0] for t in towers]})
    return violacoes


def reposicionar(
    project: Project, violacoes: list[dict]
) -> tuple[Project, list[str], list[str]]:
    """Reposiciona só as torres inválidas, com as demais fixas (D3, troca de família).

    Fica fixa, na ordem do arquivo, a torre válida sozinha e compatível com as já
    fixadas; as outras viram moldes livres do teodora (receita do Eros). Torre que o
    teodora não recoloca sai do projeto. Devolve (projeto, reposicionadas, removidas).
    """
    towers = tower_ids(project)
    alone = {v["torres"][0] for v in violacoes if len(v["torres"]) == 1}
    pairs = {frozenset(v["torres"]) for v in violacoes if len(v["torres"]) == 2}
    kept: list[tuple[str, str, dict]] = []
    moves: list[tuple[str, str, dict]] = []
    for t in towers:
        clash = any(frozenset((t[0], k[0])) in pairs for k in kept)
        (moves if t[0] in alone or clash else kept).append(t)
    # Famílias sem uso (as trocadas) viram moldes livres e o teodora as escolheria.
    problem = teodora_problem(project.remove_unused_families())
    by_id = {obj["id"]: obj for obj in problem["objects"]}
    fixed = check_problem(problem, [(f, pos) for _, f, pos in kept])
    fixed["objects"] += [by_id[f] for f in dict.fromkeys(f for _, f, _ in moves)]
    for key in ("position_chooser", "score_criteria"):
        fixed[key] = problem.get(key)
    # A família de cada torre já está escolhida: a proporção da strategy do arquivo
    # (`KeepProportion`) citaria as famílias trocadas. A meta de CA também pode já
    # estar atendida pelas fixas; a meta passa a ser recolocar cada torre (as cópias
    # fixas têm o id do molde e também contam).
    fixed["next_object"] = {"type": "SmallestCardinality"}
    families = [f for _, f, _ in towers if f in {m[1] for m in moves}]
    fixed["goals"] = [
        {"MinimumSum": {"amount": float(len(families)), "objects": [[f, 1.0]]}}
        for f in dict.fromkeys(families)
    ]
    fixed["grid_generators"] = problem["grid_generators"]
    proc = subprocess.run(
        ["./teodora", "positioning", "--seed", "0"],
        input=json.dumps(fixed),
        capture_output=True,
        text=True,
        timeout=TIMEOUT_MS // 1000,
    )
    found = json.loads(proc.stdout)["positions"] if proc.returncode == 0 else {}
    placed = project.solution.placed_objects
    moved, removed = [], []
    for torre, family, _ in moves:
        i = int(torre[1:])
        if not found.get(family):
            removed.append(torre)
            continue
        pos = found[family].pop(0)
        placed = placed.set(
            i,
            placed[i].transform(
                ["position"],
                lambda p, pos=pos: p.set(x=pos["x"], y=pos["y"], angle=pos["angle"]),
            ),
        )
        moved.append(torre)
    gone = {int(t[1:]) for t in removed}
    placed = pvector(po for i, po in enumerate(placed) if i not in gone)
    return project.transform(["solution", "placed_objects"], placed), moved, removed


# --- cascata ---------------------------------------------------------------------


def cascata(
    original: Project,
    edited: Project,
    specs: ClientSpecs = SPECS,
    por_etapa: dict[StepId, ClientSpecs] | None = None,
) -> Result[Project]:
    """Refaz, a partir das torres de `edited`, todas as etapas seguintes da strategy.

    A portaria vem de `original` (não se reproduz); os scores também, porque o
    gerador não os recalcula numa edição. `por_etapa` troca as specs de uma etapa só
    (E7: o talude novo não pode mexer no viário, que também lê o `SlopeSpec`).
    """
    portaria = placed_with_prefix(original, PORTARIA)
    project = only_towers(edited)
    project = project.transform(["solution", "outputs"], lambda _: pvector())
    project = project.transform(["solution", "annotations"], lambda _: pvector())

    for step in project.solution.strategy:
        if step.step == StepId.Tower:
            continue
        if step.step == StepId.Entrance:
            project = project.transform(
                ["solution", "placed_objects"], lambda pos: pos.extend(portaria)
            )
            continue
        try:
            step_specs = (por_etapa or {}).get(step.step, specs)
            res = _solve_step(project, step, step_specs, timeout=TIMEOUT_MS)
        except TypeError as exc:
            # O motor faz `unwrap` de um Err por dentro (ex.: teseu "infeasible").
            res = Err(str(exc))
        if res.is_err():
            return Err(f"{step}: {str(res)[:200]}")
        project = res.unwrap()

    res = compute_outputs(project, specs)
    if res.is_err():
        return Err(f"indicadores: {str(res)[:200]}")
    project = res.unwrap()
    project = compute_annotations(project)
    project = project.remove_unused_families()
    project = project.transform(
        ["solution", "scores"], lambda _: original.solution.scores
    )
    return Ok(_stable_road_hid(project, original))


def _stable_road_hid(project: Project, original: Project) -> Project:
    """O elemento de viário ganha um UUID novo a cada execução; fixa o do arquivo."""
    old = placed_with_prefix(original, "/road_network/")
    if not old:
        return project
    hid = old[0].hid

    def fix(pos: Any) -> Any:
        return pvector(
            p.set(hid=hid) if str(p.hid).startswith("/road_network/") else p
            for p in pos
        )

    return project.transform(["solution", "placed_objects"], fix)


# --- gravação ----------------------------------------------------------------------


def chave(arquivo: str, tool: str, args: dict[str, Any]) -> str:
    """A chave canônica: o mesmo pedido, com os argumentos em qualquer ordem."""
    canon = json.dumps([arquivo, tool, sorted(args.items())], ensure_ascii=False)
    return hashlib.sha1(canon.encode()).hexdigest()[:16]


def gravar(
    arquivo: str,
    tool: str,
    args: dict[str, Any],
    project: Project | None,
    resposta: dict[str, Any],
) -> dict:
    """Grava o AQG resultante e registra a chamada no índice."""
    key = chave(arquivo, tool, args)
    entry: dict[str, Any] = {
        "arquivo": arquivo,
        "tool": tool,
        "args": args,
        **resposta,
        "versoes": VERSOES,
    }
    if project is not None:
        out = GRAVACOES / Path(arquivo).stem / f"{key}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        # A rede do teseu fica fora do AQG, como nos arquivos; a B5 a grava à parte.
        data = project.transform(
            ["solution", "road_network"], lambda _: None
        ).serialize()
        # A ordem das famílias sai do hash, que inclui geometrias (hash por
        # identidade); as instâncias citam a família pelo hid, a ordem não importa.
        data["families"].sort(key=lambda f: f["class_path"])
        out.write_text(json.dumps(data, ensure_ascii=False))
        entry["aqg"] = str(out.relative_to(ROOT))
    indice = json.loads(INDICE.read_text()) if INDICE.exists() else {}
    indice[key] = entry
    INDICE.write_text(json.dumps(indice, ensure_ascii=False, indent=1, sort_keys=True))
    return entry


def aplicar(
    arquivo: str,
    original: Project,
    tool: str,
    args: dict[str, Any],
    edicao: Callable[[Project], Project],
    specs: ClientSpecs = SPECS,
    repor: bool = False,
) -> dict:
    """Edição → validar → [reposicionar] → cascata → gravação (contratos 2.2 e 2.3).

    `repor` só na troca de família: as torres inválidas são reposicionadas e o
    conjunto é validado de novo.
    """
    start = time.perf_counter()
    edited = edicao(original)
    violacoes = validar(edited)
    extra: dict[str, Any] = {}
    if violacoes and repor:
        edited, moved, removed = reposicionar(edited, violacoes)
        extra = {"reposicionadas": moved, "removidas": removed}
        violacoes = validar(edited)
    if violacoes:
        resposta = {
            "veredito": "invalido",
            "violacoes": violacoes,
            "etapas": ["validar", *(["reposicionar"] if extra else [])],
            **extra,
        }
        return gravar(arquivo, tool, args, edited, resposta)
    res = cascata(original, edited, specs)
    vagas = re.search(r"expected (\d+), found ([\d.]+)", str(res))
    if res.is_err() and vagas:
        # O teseu recusa quando acha menos de 80% da demanda: é veredito, não falha.
        resposta = {
            "veredito": "invalido",
            "violacoes": [
                {
                    "regra": "ParkingNetworkInsufficientRatio",
                    "torres": [t for t, _, _ in tower_ids(edited)],
                }
            ],
            "etapas": [
                "validar",
                *(["reposicionar"] if extra else []),
                "estacionamento",
            ],
            "vagas": {
                "necessarias": int(vagas.group(1)),
                "encontradas": int(float(vagas.group(2))),
            },
            **extra,
        }
        return gravar(arquivo, tool, args, edited, resposta)
    if res.is_err():
        resposta = {
            "veredito": "erro",
            "violacoes": [],
            "erro": str(res)[:300],
            **extra,
        }
        return gravar(arquivo, tool, args, None, resposta)
    etapas = ["validar", *(["reposicionar"] if extra else [])]
    etapas += [str(s.step.value) for s in edited.solution.strategy[1:]]
    resposta = {
        "veredito": "valido",
        "violacoes": [],
        "etapas": [*etapas, "indicadores"],
        **extra,
        "segundos": round(time.perf_counter() - start, 2),
    }
    return gravar(arquivo, tool, args, res.unwrap(), resposta)


# --- conferência da base (aceite do G0) ----------------------------------------


def _placed_summary(raw: dict) -> dict[str, list]:
    out: dict[str, list] = {}
    for po in raw["solution"]["placed_objects"]:
        cat = "/".join(po["hid"].split("/")[1:3])
        pos = po.get("position") or {}
        out.setdefault(cat, []).append(
            tuple(round(pos.get(k, 0.0), 2) for k in ("x", "y", "z", "angle"))
        )
    return {k: sorted(v) for k, v in out.items()}


def conferir_base(path: Path) -> dict:
    """Cascata sem edição: tem de reproduzir o arquivo e ser determinística."""
    arquivo = str(path.relative_to(AQG))
    raw = json.loads(path.read_text())
    original = Project.create(raw)
    first = cascata(original, original)
    if first.is_err():
        return {"arquivo": arquivo, "ok": False, "motivo": str(first)[:200]}
    base = first.unwrap().serialize()
    again = cascata(original, original).unwrap().serialize()

    expected, got = _placed_summary(raw), _placed_summary(base)
    placed_diff = sorted(
        k for k in set(expected) | set(got) if expected.get(k) != got.get(k)
    )
    old = {o["type"]: o for o in raw["solution"]["outputs"]}
    new = {o["type"]: o for o in base["solution"]["outputs"]}
    outputs_diff = sorted(t for t in old.keys() & new.keys() if old[t] != new[t])
    row = {
        "arquivo": arquivo,
        "elementos_diferentes": placed_diff,
        "indicadores_diferentes": outputs_diff,
        "indicadores_so_no_arquivo": sorted(old.keys() - new.keys()),
        "indicadores_so_na_base": sorted(new.keys() - old.keys()),
        "deterministico": base == again,
        "violacoes_no_arquivo": validar(original),
    }
    # Indicadores diferentes não reprovam: o estado inicial dos casos é esta base,
    # e o buildings atual calcula alguns indicadores de outro jeito que o exportador
    # que gerou o arquivo (registrado no relatório).
    row["ok"] = (
        not placed_diff and row["deterministico"] and not row["violacoes_no_arquivo"]
    )
    gravar(arquivo, "base", {}, Project.create(base), {"veredito": "valido"})
    return row


def main() -> None:
    admitted = {
        r["arquivo"]
        for r in json.loads(Path(__file__).with_name("admissao.json").read_text())
        if r["admitido"]
    }
    targets = [Path(a) for a in sys.argv[1:]] or [AQG]
    files = [
        f for t in targets for f in (sorted(t.rglob("*.json")) if t.is_dir() else [t])
    ]
    files = [f for f in files if str(f.relative_to(AQG)) in admitted]
    rows = []
    for path in files:
        row = conferir_base(path)
        rows.append(row)
        print(
            "ok  " if row["ok"] else "DIF ",
            row["arquivo"],
            {
                k: v
                for k, v in row.items()
                if v and k not in ("arquivo", "ok", "deterministico")
            },
        )
    print(f"{sum(r['ok'] for r in rows)} de {len(rows)} bases reproduzem o arquivo")


if __name__ == "__main__":
    main()
