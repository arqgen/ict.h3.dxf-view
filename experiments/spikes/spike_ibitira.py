"""Spike: refazer a terraplenagem (trama + ibitira) a partir de um AQG.

Roda com o venv do viabiliza-terrenos, com cwd em packages/py (`lib`, `./teseu` e
`./ibitira`). O AQG não guarda a rede viária, e a terraplenagem precisa dela; por
isso o estado de entrada é: só as torres → estacionamento regerado pelo teseu
(spike_teseu) → terraplenagem. Compara corte, aterro, muro e a cota das torres
com o arquivo.
"""

import glob
import json
import sys
import time
from pathlib import Path

from buildings.protocol.client_specs import StepId
from buildings.protocol.project import Project
from lib.config.client_specs import temp_get_client_specs
from lib.problem.earth_movement import compute_earthmoving
from lib.problem.parking_lot import solve_parking_lot
from pyrsistent import pvector

AQG = Path(__file__).resolve().parents[2] / "data" / "aqg"
FILES = sorted(
    glob.glob(str(AQG / "favoritadas" / "*.json"))
    + glob.glob(str(AQG / "avaliadas" / "*" / "*.json"))
)
SPECS = temp_get_client_specs("default").unwrap()
EARTH_KEYS = ("corte", "aterro", "balanco", "muro_altura", "muro_comprimento")


def last_output(outputs, kind: str) -> dict | None:
    found = [o for o in outputs if o.get("type") == kind]
    return found[-1] if found else None


def tower_z(placed: list[dict]) -> list[float]:
    return [
        round(po["position"].get("z", 0.0), 2)
        for po in placed
        if po.get("hid", "").startswith("/building/torre")
    ]


def spike(path: str) -> dict | None:
    raw = json.load(open(path))
    strategy = (raw.get("solution") or {}).get("strategy") or []
    if not any(s.startswith("/earthmoving") for s in strategy):
        return None
    parking = [s for s in strategy if s.startswith("/parking_lot")]
    row = {
        "arquivo": path.split("/")[-1][:40],
        "versao": raw.get("version"),
        "terraplenagem": next(s for s in strategy if s.startswith("/earthmoving")),
        "estacionamento": parking[0] if parking else None,
    }
    if parking and not parking[0].startswith("/parking_lot/optimal_selection"):
        row["etapa"] = "fora: estacionamento sem teseu"
        return row

    archived = {o["type"]: o for o in raw["solution"]["outputs"]}
    row["arquivo_mov"] = {
        k: archived.get("MovimentoDeTerra", {}).get(k) for k in EARTH_KEYS
    }
    row["arquivo_z"] = tower_z(raw["solution"]["placed_objects"])

    try:
        project = Project.create(raw)
        project = project.transform(
            ["solution", "placed_objects"],
            lambda pos: pvector(
                p for p in pos if str(p.hid).startswith("/building/torre")
            ),
        )
        if parking:
            path_ = next(
                p for p in project.solution.strategy if p.step == StepId.ParkingLot
            )
            t0 = time.perf_counter()
            res = solve_parking_lot(path_, project, SPECS)
            row["estacionamento_s"] = round(time.perf_counter() - t0, 2)
            if res.is_err():
                row["etapa"] = f"estacionamento: {str(res)[:200]}"
                return row
            project = res.unwrap()

        t1 = time.perf_counter()
        res = compute_earthmoving(project, SPECS)
        row["terraplenagem_s"] = round(time.perf_counter() - t1, 2)
        if res.is_err():
            row["etapa"] = f"terraplenagem: {str(res)[:200]}"
            return row
        solved = res.unwrap().serialize()
    except Exception as err:
        row["etapa"] = f"{type(err).__name__}: {str(err)[:200]}"
        return row

    mov = last_output(solved["solution"]["outputs"], "MovimentoDeTerra") or {}
    row["novo_mov"] = {k: mov.get(k) for k in EARTH_KEYS}
    row["novo_z"] = tower_z(solved["solution"]["placed_objects"])
    row["etapa"] = "ok"
    return row


if __name__ == "__main__":
    files = sys.argv[1:] or FILES
    rows = [r for r in (spike(f) for f in files) if r]
    json.dump(rows, open(sys.argv[0].replace(".py", "_resultado.json"), "w"), indent=1)
    for r in rows:
        print(json.dumps(r, ensure_ascii=False))
