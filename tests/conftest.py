import pytest

from src.cad.model import CadModel, build_model
from tests.make_sample import build_sample_doc


@pytest.fixture(scope="session")
def sample_model() -> CadModel:
    return build_model(build_sample_doc(), "sample.dxf")
