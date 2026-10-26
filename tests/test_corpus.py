"""Smoke test sobre o acervo real de AQGs em data/aqg (nao versionado).

Num clone sem os arquivos, o teste pula.
"""

from pathlib import Path

import pytest

from src.cad.geometry import bbox_contains
from src.cad.model import load_aqg, tower_units

FILES = sorted((Path(__file__).parents[1] / "data" / "aqg").rglob("*.json"))
PARAMS = FILES or [
    pytest.param(None, marks=pytest.mark.skip("acervo data/aqg ausente"))
]


@pytest.mark.parametrize("path", PARAMS, ids=lambda p: p.name if p else "vazio")
def test_corpus_file(path: Path):
    model = load_aqg(path.read_bytes(), path.name)

    assert not [w for w in model.warnings if "sem família" in w]
    assert all(inst.entity_ids for inst in model.instances.values())

    perimeter = model.layer("AQG_PERIMETRO")
    assert perimeter is not None and perimeter.bbox is not None
    for entity in model.entities:
        if entity.type in ("core", "vaga", "portaria"):
            assert bbox_contains(perimeter.bbox, entity.bbox), entity.id

    towers = [
        inst
        for inst in model.instances.values()
        if inst.family_type.lower() in ("tower", "dynamictower3d")
    ]
    outputs = {o["type"]: o.get("value") for o in model.indicators["outputs"]}
    assert len(towers) == outputs["TotalDeTorres"]

    units = [tower_units(model.families[t.family_index].properties) for t in towers]
    assert None not in units
    assert sum(u[1] for u in units) == outputs["TotalDeUnidades"]
