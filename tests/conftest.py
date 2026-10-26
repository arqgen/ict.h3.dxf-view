import pytest

from src.cad.model import CadModel, build_model
from tests.make_aqg_sample import build_sample_project


@pytest.fixture
def sample_project() -> dict:
    return build_sample_project()


@pytest.fixture(scope="session")
def sample_model() -> CadModel:
    return build_model(build_sample_project(), "sample.json")
