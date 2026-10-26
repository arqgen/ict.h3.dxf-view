import copy

import pytest

from src.cad.model import CadModel, build_model
from tests.make_aqg_sample import build_sample_project


@pytest.fixture
def sample_project() -> dict:
    return build_sample_project()


@pytest.fixture(scope="session")
def sample_model() -> CadModel:
    return build_model(build_sample_project(), "sample.json")


@pytest.fixture
def duplicate_label_model() -> CadModel:
    """Terceira familia com o label `T/4` repetido, instanciada por `p1`."""
    project = build_sample_project()
    family = copy.deepcopy(project["families"][0])
    family["class_path"] = "/building/torre/T/4/0i/3f"
    family["properties"] = {"type": "Tower", "total_pavimentos": 3}
    project["families"].append(family)
    project["solution"]["placed_objects"][1]["hid"] = "/building/torre/T/4/0i/3f/2222"
    return build_model(project, "duplicado.json")


def two_tower_families(second_units_per_floor: int) -> dict:
    """`p0` em `T/4` (4 unidades) e `p1` numa familia `T/5`, com descritivos."""
    project = build_sample_project()
    tower = project["families"][0]
    tower["properties"] = {
        "type": "Tower",
        "n_pavimentos_unidades": 2,
        "pav_tipo": {"tipologias": {"/area/apartamento/2 Quartos/aaaa": 2}},
    }
    other = copy.deepcopy(tower)
    other["class_path"] = "/building/torre/T/5/0i/2f"
    other["label"] = "T/5"
    other["properties"]["pav_tipo"]["tipologias"] = {
        "/area/apartamento/2 Quartos/aaaa": second_units_per_floor
    }
    project["families"].append(other)
    project["solution"]["placed_objects"][1]["hid"] = "/building/torre/T/5/0i/2f/22"
    second = second_units_per_floor * 2
    project["solution"]["outputs"] = [
        o for o in project["solution"]["outputs"] if o["type"] != "DescritivoTorre"
    ] + [
        {"type": "DescritivoTorre", "label": "01", "unidades": 4, "altura": 30},
        {"type": "DescritivoTorre", "label": "02", "unidades": second, "altura": 45},
        {"type": "DescritivoTorre", "label": "TOTAL", "unidades": 4 + second},
    ]
    return project


def with_annotations() -> dict:
    """Dois marcos de cota (a0 perto de p0, a1 longe) e uma seta (a2)."""
    project = build_sample_project()
    project["solution"]["annotations"] = [
        {
            "type": "Annotation",
            "hid": "/annotation/elevation_marker",
            "position": {"x": 25, "y": 5, "z": 101.5, "angle": 0},
            "value": 101.5,
        },
        {
            "type": "Annotation",
            "hid": "/annotation/elevation_marker",
            "position": {"x": 50, "y": 50, "z": 120.25, "angle": 0},
            "value": 120.25,
        },
        {
            "type": "SlopeArrow",
            "hid": "/annotation/slope_arrow/gentle/0",
            "line": {"type": "LineString", "coordinates": [[0, 0, 1], [10, 10, 2]]},
            "value": 0.5,
        },
    ]
    return project
