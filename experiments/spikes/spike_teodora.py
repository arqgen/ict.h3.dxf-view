"""Spike: remontar o problema do teodora a partir de um AQG e validar as torres.

Roda com o venv do viabiliza-terrenos, com cwd em packages/py (onde estão `lib` e
`./teodora`). Para cada AQG: monta o PositioningProblem do passo Tower com as
funções do pipeline, fixa as torres nas posições do arquivo (receita do Eros,
`app/teodora/validate.py`) e roda o binário. Controle: a primeira torre deslocada
500 m em x tem de sair inválida.
"""

import copy
import glob
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path

from buildings.protocol.client_specs import StepId
from buildings.protocol.project import Project
from lib.config.client_specs import temp_get_client_specs
from lib.problem.pipeline import _gen_tower_config
from lib.problem.towers import _gen_problem
from pyrsistent import pvector

AQG = Path(__file__).resolve().parents[2] / "data" / "aqg"
FILES = sorted(
    glob.glob(str(AQG / "favoritadas" / "*.json"))
    + glob.glob(str(AQG / "avaliadas" / "*" / "*.json"))
)
FORMULATION = "inconsistency in the formulated problem"


def check_problem(problem: dict, towers: list[tuple[str, dict]]) -> dict:
    """Receita do Eros: moldes saem, entra uma cópia fixa por torre."""
    by_id = {obj["id"]: obj for obj in problem["objects"]}
    molde_ids = {fam for fam, _ in towers}
    objects = [obj for obj in problem["objects"] if obj["id"] not in molde_ids]
    for fam, position in towers:
        fixed = copy.deepcopy(by_id[fam])
        fixed["position"] = dict(position)
        objects.append(fixed)
    return {
        "objects": objects,
        "constraints": problem.get("constraints") or [],
        "score_criteria": {},
        "grid_generators": [],
        "goals": [],
        "next_object": None,
    }


def run_teodora(problem: dict) -> tuple[str, str, float]:
    start = time.perf_counter()
    proc = subprocess.run(
        ["./teodora", "positioning"],
        input=json.dumps(problem),
        capture_output=True,
        text=True,
        timeout=60,
    )
    ms = (time.perf_counter() - start) * 1000
    if proc.returncode == 0:
        placed = json.loads(proc.stdout).get("positions") or {}
        return ("valid" if not placed else "valid?livres"), "", ms
    if FORMULATION in proc.stderr:
        return "invalid", proc.stderr[:300], ms
    return "unavailable", proc.stderr[:300], ms


def spike(path: str) -> dict:
    raw = json.load(open(path))
    row = {"arquivo": path.split("/")[-1][:40], "versao": raw.get("version")}
    try:
        project = Project.create(raw)
    except Exception as err:
        row["etapa"] = f"Project.create: {type(err).__name__}: {str(err)[:150]}"
        return row

    strategy = getattr(project.solution, "strategy", None) or []
    tower_paths = [p for p in strategy if p.step == StepId.Tower]
    if not tower_paths:
        from buildings.protocol.client_specs import ExecutionPath

        tower_paths = [ExecutionPath.create("/tower/positioning/default/b")]
        row["forcado"] = True
    tower_path = tower_paths[0]
    row["strategy"] = str(tower_path)

    specs = temp_get_client_specs("default").unwrap()
    try:
        config = _gen_tower_config(project, specs.pipeline.get_config(tower_path))
    except Exception as err:
        row["etapa"] = f"config: {type(err).__name__}: {str(err)[:150]}"
        return row

    towers = [
        (str(po.hid.nonunique()), po.position.serialize())
        for po in project.solution.placed_objects
        if str(po.hid).startswith("/building/torre")
    ]
    row["torres"] = len(towers)

    pre_tower = project.transform(["solution", "placed_objects"], lambda _: pvector())
    start = time.perf_counter()
    try:
        res = _gen_problem(pre_tower, tower_path, config, specs)
    except Exception as err:
        row["etapa"] = f"formulacao: {type(err).__name__}: {str(err)[:150]}"
        row["trace"] = traceback.format_exc()[-400:]
        return row
    row["formular_ms"] = round((time.perf_counter() - start) * 1000)
    if res.is_err():
        row["etapa"] = f"formulacao Err: {str(res)[:200]}"
        return row

    _, problem = res.unwrap()
    row["tipo"] = type(problem).__name__
    problem_dict = problem.serialize()
    ids = {obj["id"] for obj in problem_dict["objects"]}
    missing = sorted({fam for fam, _ in towers} - ids)
    if missing:
        row["etapa"] = f"familia ausente no problema: {missing}"
        return row

    verdict, detail, ms = run_teodora(check_problem(problem_dict, towers))
    row.update(veredito=verdict, detalhe=detail, binario_ms=round(ms))

    moved = list(towers)
    fam, pos = moved[0]
    moved[0] = (fam, {**pos, "x": pos["x"] + 500})
    ctrl, ctrl_detail, _ = run_teodora(check_problem(problem_dict, moved))
    row.update(controle=ctrl, controle_detalhe=ctrl_detail[:120])

    if len(towers) >= 2:
        stacked = list(towers)
        fam2, pos2 = stacked[1]
        _, pos1 = towers[0]
        stacked[1] = (fam2, {**pos2, "x": pos1["x"] + 1, "y": pos1["y"]})
        over, over_detail, _ = run_teodora(check_problem(problem_dict, stacked))
        row.update(sobreposta=over, sobreposta_regra=over_detail[40:160])
    row["etapa"] = "ok"
    return row


if __name__ == "__main__":
    files = sys.argv[1:] or FILES
    rows = [spike(f) for f in files]
    json.dump(rows, open(sys.argv[0].replace(".py", "_resultado.json"), "w"), indent=1)
    for r in rows:
        print(
            r["arquivo"],
            r.get("versao"),
            r.get("strategy", ""),
            r.get("tipo", ""),
            r.get("torres", ""),
            r["etapa"][:90],
            r.get("veredito", ""),
            r.get("controle", ""),
            r.get("sobreposta", "-"),
            r.get("forcado", ""),
            r.get("formular_ms", ""),
            r.get("binario_ms", ""),
        )
