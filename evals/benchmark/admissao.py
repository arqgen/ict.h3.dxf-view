"""Teste de admissão de AQGs nas tarefas de edição do benchmark.

Um arquivo entra nas tarefas de edição só se os motores reproduzem o próprio
arquivo, a partir só das torres:

- teodora: o problema remontado aceita as torres do arquivo e recusa o controle
  (a primeira torre deslocada 500 m);
- teseu: refaz as mesmas vagas, nas mesmas posições (até 1 cm);
- ibitira: refaz o mesmo corte, aterro e muro e a mesma cota das torres.

Também informa o catálogo de `data/families/` que cobre o programa; sem catálogo, o
arquivo entra, mas sem as tarefas de troca de família.

Roda com o venv do viabiliza-terrenos, com cwd em `data/benchmark/bin` (os binários
nas versões fixadas na D8 do PRD-queries.md; ver `gravacao.py`):

    cd <repo>/data/benchmark/bin && <viabiliza-terrenos.backend>/venv/bin/python \\
        <repo>/evals/benchmark/admissao.py [arquivos ou pastas]

Sem argumentos, testa todo `data/aqg/`. Escreve `admissao.json` ao lado deste
arquivo.
"""

import json
import sys
from pathlib import Path
from typing import Any

from buildings.protocol.client_specs import StepId
from buildings.protocol.project import Project
from gravacao import (
    SPECS,
    check_problem,
    earth_movement,
    only_towers,
    run_teodora,
    strategy_step,
    teodora_problem,
)
from lib.problem.parking_lot import solve_parking_lot

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_name("admissao.json")
EARTH_KEYS = ("corte", "aterro", "muro_altura", "muro_comprimento")
PROGRAM_TYPES = ("FamilyProportion", "StaticFamilyProportion", "FamilySelection")


def check_teodora(project: Project) -> str | None:
    """None quando passa; senão, o motivo."""
    try:
        problem = teodora_problem(project)
    except ValueError as err:
        return str(err)
    towers = [
        (str(po.hid.nonunique()), po.position.serialize())
        for po in project.solution.placed_objects
        if str(po.hid).startswith("/building/torre")
    ]
    if run_teodora(check_problem(problem, towers))[0] != "valid":
        return "as torres do arquivo não passam na validação"
    family, pos = towers[0]
    moved = [(family, {**pos, "x": pos["x"] + 500}), *towers[1:]]
    if run_teodora(check_problem(problem, moved))[0] != "invalid":
        return "o controle deslocado 500 m não foi recusado"
    return None


def spot_keys(placed: list[dict]) -> set[tuple[float, float]]:
    return {
        (round(po["position"]["x"], 2), round(po["position"]["y"], 2))
        for po in placed
        if po.get("hid", "").startswith("/equipment/vaga")
    }


def tower_z(placed: list[dict]) -> list[float]:
    return [
        round(po["position"].get("z", 0.0), 2)
        for po in placed
        if po.get("hid", "").startswith("/building/torre")
    ]


def catalog_for(raw: dict) -> str | None:
    hids = {
        a["hid"]
        for a in raw.get("archprog") or []
        if a.get("type") in PROGRAM_TYPES and a.get("hid")
    }
    for path in sorted((ROOT / "data" / "families").glob("*.json")):
        if hids <= {f["class_path"] for f in json.loads(path.read_text())}:
            return path.stem
    return None


def admit(path: Path) -> dict:
    raw = json.loads(path.read_text())
    row: dict[str, Any] = {
        "arquivo": str(path.relative_to(ROOT / "data" / "aqg"))
        if path.is_relative_to(ROOT / "data" / "aqg")
        else str(path),
        "versao": raw.get("version"),
        "catalogo": catalog_for(raw),
    }
    try:
        project = Project.create(raw)
        motivo = check_teodora(project)
        row["teodora"] = motivo or "ok"
        if motivo:
            return {**row, "admitido": False, "motivo": f"teodora: {motivo}"}

        parked = only_towers(project)
        parking = strategy_step(project, StepId.ParkingLot)
        if parking is None:
            row["teseu"] = "sem estacionamento"
        elif str(parking.solver) != "optimal_selection" and "optimal" not in str(
            parking
        ):
            motivo = f"estacionamento fora da cadeia gravável ({parking})"
            return {**row, "teseu": motivo, "admitido": False, "motivo": motivo}
        else:
            res = solve_parking_lot(parking, parked, SPECS)
            if res.is_err():
                motivo = f"teseu: {str(res)[:150]}"
                return {**row, "teseu": motivo, "admitido": False, "motivo": motivo}
            parked = res.unwrap()
            novo = spot_keys(parked.serialize()["solution"]["placed_objects"])
            antigo = spot_keys(raw["solution"]["placed_objects"])
            row["teseu"] = (
                "ok"
                if novo == antigo
                else (
                    f"vagas diferentes: {len(antigo)} no arquivo, "
                    f"{len(novo)} refeitas, {len(novo & antigo)} iguais"
                )
            )
            if row["teseu"] != "ok":
                return {**row, "admitido": False, "motivo": row["teseu"]}

        if strategy_step(project, StepId.Earthmoving) is None:
            row["ibitira"] = "sem terraplenagem"
        else:
            res = earth_movement.compute_earthmoving(parked, SPECS)
            if res.is_err():
                motivo = f"ibitira: {str(res)[:150]}"
                return {**row, "ibitira": motivo, "admitido": False, "motivo": motivo}
            solved = res.unwrap().serialize()["solution"]
            arq = {o["type"]: o for o in raw["solution"]["outputs"]}
            antigo = arq.get("MovimentoDeTerra", {})
            novo = [o for o in solved["outputs"] if o.get("type") == "MovimentoDeTerra"]
            novo_mov = novo[-1] if novo else {}
            diffs = [k for k in EARTH_KEYS if antigo.get(k) != novo_mov.get(k)]
            if tower_z(raw["solution"]["placed_objects"]) != tower_z(
                solved["placed_objects"]
            ):
                diffs.append("cota das torres")
            row["ibitira"] = "ok" if not diffs else f"diferem: {diffs}"
            if diffs:
                return {**row, "admitido": False, "motivo": row["ibitira"]}
    except Exception as err:  # noqa: BLE001 - o teste reporta, não interrompe o lote
        motivo = f"{type(err).__name__}: {str(err)[:150]}"
        return {**row, "admitido": False, "motivo": motivo}

    return {**row, "admitido": True, "motivo": ""}


def collect(args: list[str]) -> list[Path]:
    targets = [Path(a) for a in args] or [ROOT / "data" / "aqg"]
    files: list[Path] = []
    for target in targets:
        files += sorted(target.rglob("*.json")) if target.is_dir() else [target]
    return files


def main() -> None:
    rows = [admit(path) for path in collect(sys.argv[1:])]
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    for r in rows:
        status = "ADMITIDO" if r["admitido"] else "fora    "
        print(status, r["versao"], r["catalogo"] or "-", r["arquivo"], r["motivo"])
    print(f"{sum(r['admitido'] for r in rows)} de {len(rows)} admitidos")


if __name__ == "__main__":
    main()
