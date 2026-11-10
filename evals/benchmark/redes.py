"""Grava a rede viária que o teseu refaz em cada arquivo admitido (B5, contrato 2.6).

O AQG não guarda a rede: ela sai da cascata sem edição. Junto vão os `/road_access`
já posicionados da portaria e das torres, pelo id do parser (`p<i>`), para a tool
`caminho` rodar do lado da RECOD sem o `buildings`.

    cd <viabiliza-terrenos.backend>/packages/py && ../../venv/bin/python \\
        <repo>/evals/benchmark/redes.py [arquivos]
"""

import json
import sys
from pathlib import Path
from typing import Any

from buildings.protocol.client_specs import StepId
from buildings.protocol.id import VolumeId
from buildings.protocol.project import Project
from edicoes import ADMITIDOS
from gravacao import AQG, PORTARIA, ROOT, TOWER, VERSOES, cascata

REDES = ROOT / "data" / "benchmark" / "redes"


def linhas(geometry: Any) -> list[list[list[float]]]:
    """Cada parte da geometria como lista de pontos 2D (um ponto vira linha de um)."""
    parts = getattr(geometry, "geoms", [geometry])
    return [[[round(c, 3) for c in pt[:2]] for pt in part.coords] for part in parts]


def acessos(project: Project) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i, po in enumerate(project.solution.placed_objects):
        hid = str(po.hid)
        if not hid.startswith((TOWER, PORTARIA)):
            continue
        family = next(iter(project.families.filter_by_class_path(po.hid)))
        placed = family.position_family(po.position)
        out[f"p{i}"] = {
            "familia": str(family.class_path),
            "linhas": [
                ln
                for vol in placed.volume.by_class_path(VolumeId.road_access())
                for ln in linhas(vol.geometry)
            ],
        }
    return out


def gravar_rede(arquivo: str) -> dict:
    original = Project.create(json.loads((AQG / arquivo).read_bytes()))
    if StepId.ParkingLot not in [s.step for s in original.solution.strategy]:
        return {"arquivo": arquivo, "fora": "sem etapa de estacionamento"}
    res = cascata(original, original)
    if res.is_err():
        return {"arquivo": arquivo, "erro": str(res)[:200]}
    rede = res.unwrap().solution.road_network
    data = {
        "arquivo": arquivo,
        "versoes": VERSOES,
        "ruas": [
            [[round(c, 3) for c in pt] for pt in line.coords] for line in rede.axis
        ],
        "acessos": acessos(original),
    }
    out = REDES / f"{Path(arquivo).stem}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False))
    return {"arquivo": arquivo, "ruas": len(data["ruas"]), "rede": str(out)}


def main() -> None:
    only = set(sys.argv[1:])
    for arquivo in ADMITIDOS:
        if only and arquivo not in only:
            continue
        print(gravar_rede(arquivo), flush=True)


if __name__ == "__main__":
    main()
