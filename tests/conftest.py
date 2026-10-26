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
