"""Compara as vagas do teseu remontado com as do AQG (receita do spike_teseu)."""

import json
import sys

from buildings.protocol.project import Project
from lib.config.client_specs import temp_get_client_specs
from lib.problem.parking_lot.solver import optimal_selection as osel
from pyrsistent import pvector

SPECS = temp_get_client_specs("default").unwrap()


def key(x: float, y: float) -> tuple[float, float]:
    return (round(x, 2), round(y, 2))


for path in sys.argv[1:]:
    raw = json.load(open(path))
    archived = {
        key(po["position"]["x"], po["position"]["y"])
        for po in raw["solution"]["placed_objects"]
        if po.get("hid", "").startswith("/equipment/vaga")
    }
    project = Project.create(raw).transform(
        ["solution", "placed_objects"],
        lambda pos: pvector(p for p in pos if str(p.hid).startswith("/building/torre")),
    )
    perimeter = osel.gen_perimeter_2d(project).unwrap()
    problem = osel._formulate_teseu_problem(
        project=project,
        perimeter=perimeter,
        client_specs=SPECS,
        max_iterations=50,
        timeout=60000,
    ).unwrap()
    sol = osel._solve_teseu(problem).unwrap()
    rebuilt = {key(s.position.x, s.position.y) for s in sol.parking_spots}
    print(
        path.split("/")[-1][:30],
        "arquivo",
        len(archived),
        "remontado",
        len(rebuilt),
        "iguais",
        len(archived & rebuilt),
        "ruas",
        len(sol.streets),
        "com_no",
        sum(1 for s in sol.streets if getattr(s, "node_id", None) is not None),
    )
