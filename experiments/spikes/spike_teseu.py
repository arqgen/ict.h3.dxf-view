"""Spike: remontar o problema do teseu a partir de um AQG e resolver o estacionamento.

Roda com o venv do viabiliza-terrenos, com cwd em packages/py (`lib` e `./teseu`).
Para cada AQG com `/parking_lot/optimal_selection`: estado pré-estacionamento = só
as torres (no pipeline com teseu a portaria vem depois); formula com as funções do
pipeline, roda o teseu e monta a solução (greide incluso). Compara as vagas com as
do arquivo. Depois simula a E1: demanda × 1,5.
"""

import glob
import json
import sys
import time
from math import ceil
from pathlib import Path

from buildings.protocol.project import Project
from lib.config.client_specs import temp_get_client_specs
from lib.problem.parking_lot.solver import optimal_selection as osel
from lib.problem.parking_lot.utils import calc_parking_spots_amount
from pyrsistent import pvector

AQG = Path(__file__).resolve().parents[2] / "data" / "aqg"
FILES = sorted(
    glob.glob(str(AQG / "favoritadas" / "*.json"))
    + glob.glob(str(AQG / "avaliadas" / "*" / "*.json"))
)
SPECS = temp_get_client_specs("default").unwrap()


def count_spots(project: Project) -> int:
    return sum(
        1
        for po in project.solution.placed_objects
        if str(po.hid).startswith("/equipment/vaga")
    )


def run(project: Project, factor: float) -> dict:
    out: dict = {}
    base = calc_parking_spots_amount(project)
    out["demanda"] = base.map(lambda v: ceil(v * factor)).unwrap_or_default(None)
    original = osel.calc_parking_spots_amount
    if factor != 1:
        osel.calc_parking_spots_amount = lambda _p: base.map(lambda v: ceil(v * factor))
    try:
        perimeter = osel.gen_perimeter_2d(project).unwrap()
        t0 = time.perf_counter()
        problem = osel._formulate_teseu_problem(
            project=project,
            perimeter=perimeter,
            client_specs=SPECS,
            max_iterations=50,
            timeout=60000,
        )
    finally:
        osel.calc_parking_spots_amount = original
    out["formular_ms"] = round((time.perf_counter() - t0) * 1000)
    if problem.is_err():
        out["erro"] = f"formulacao: {str(problem)[:200]}"
        return out

    t1 = time.perf_counter()
    solution = osel._solve_teseu(problem.unwrap())
    out["teseu_s"] = round(time.perf_counter() - t1, 2)
    if solution.is_err():
        out["erro"] = f"teseu: {str(solution)[:200]}"
        return out
    sol = solution.unwrap()
    out.update(
        vagas_teseu=len(sol.parking_spots),
        ruas=len(sol.streets),
        parada=str(getattr(sol, "stop_reason", "")),
        iteracoes=sol.iteration_count,
    )

    t2 = time.perf_counter()
    solved = osel._compute_solution(
        sol, project=project, perimeter=perimeter, client_specs=SPECS, max_slope=8.33
    )
    out["montar_s"] = round(time.perf_counter() - t2, 2)
    if solved.is_err():
        out["erro"] = f"montar: {str(solved)[:200]}"
        return out
    out["vagas_no_projeto"] = count_spots(solved.unwrap())
    return out


def spike(path: str) -> dict | None:
    raw = json.load(open(path))
    strategy = (raw.get("solution") or {}).get("strategy") or []
    if not any(s.startswith("/parking_lot/optimal_selection") for s in strategy):
        return None
    outputs = {o["type"]: o for o in raw["solution"]["outputs"]}
    row = {
        "arquivo": path.split("/")[-1][:40],
        "versao": raw.get("version"),
        "vagas_arquivo": sum(
            1
            for po in raw["solution"]["placed_objects"]
            if po.get("hid", "").startswith("/equipment/vaga")
        ),
        "vagas_indicador": (outputs.get("NumeroDeVagasProjetado") or {}).get("value"),
    }
    try:
        project = Project.create(raw)
        towers_only = project.transform(
            ["solution", "placed_objects"],
            lambda pos: pvector(
                p for p in pos if str(p.hid).startswith("/building/torre")
            ),
        )
        row["torres"] = len(towers_only.solution.placed_objects)
        row["original"] = run(towers_only, 1.0)
        row["e1_x1.5"] = run(towers_only, 1.5)
    except Exception as err:
        row["erro"] = f"{type(err).__name__}: {str(err)[:200]}"
    return row


if __name__ == "__main__":
    files = sys.argv[1:] or FILES
    rows = [r for r in (spike(f) for f in files) if r]
    json.dump(rows, open(sys.argv[0].replace(".py", "_resultado.json"), "w"), indent=1)
    for r in rows:
        print(json.dumps(r, ensure_ascii=False))
