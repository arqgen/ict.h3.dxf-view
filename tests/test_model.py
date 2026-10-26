"""Assertivas EXATAS sobre o indice, contra o projeto de tests/make_aqg_sample.py.

Nada de `>=` aqui. Uma assertiva frouxa sobre contagem de entidades e capaz de
passar com o indexador perdendo geometria silenciosamente. `approx` so onde a
geometria passou por rotacao (cos 90 nao e zero em float).
"""

import json
from collections import Counter

import pytest

from src.cad.model import (
    AqgLoadError,
    CadModel,
    build_model,
    describe_model,
    load_aqg,
    prims_payload,
)
from tests.make_aqg_sample import build_sample_project

EXPECTED_IDS = [
    "s0",
    "s1",
    "s2",
    "s3",
    "p0.0",
    "p0.1",
    "p0.2",
    "p0.3",
    "p0.4",
    "p1.0",
    "p1.1",
    "p1.2",
    "p1.3",
    "p1.4",
    "p2.0",
    "p3.0",
    "p4",
    "p5",
]


def test_entity_ids_are_exact(sample_model: CadModel):
    assert [e.id for e in sample_model.entities] == EXPECTED_IDS
    assert list(sample_model.by_id) == EXPECTED_IDS
    for missing in ("s4", "p0.5", "p0.6", "p0.7", "p2.1", "p2.2", "p6"):
        assert missing not in sample_model.by_id


def test_instances(sample_model: CadModel):
    instances = sample_model.instances
    assert list(instances) == ["p0", "p1", "p2", "p3"]
    for pid in ("p0", "p1"):
        assert instances[pid].family == "T/4"
        assert instances[pid].family_type == "Tower"
    for pid in ("p2", "p3"):
        assert instances[pid].family == "Vaga 0"
        assert instances[pid].family_type == "Vaga"
    assert instances["p0"].entity_ids == ["p0.0", "p0.1", "p0.2", "p0.3", "p0.4"]
    assert instances["p2"].entity_ids == ["p2.0"]
    assert instances["p1"].angle == 90.0
    assert not any(pid in sample_model.by_id for pid in instances)


def test_count_by_family(sample_model: CadModel):
    counts = Counter(inst.family for inst in sample_model.instances.values())
    assert counts == {"T/4": 2, "Vaga 0": 2}


def test_families(sample_model: CadModel):
    assert [(f.label, f.type) for f in sample_model.families] == [
        ("T/4", "Tower"),
        ("Vaga 0", "Vaga"),
    ]


def test_single_warning_cites_p6(sample_model: CadModel):
    assert sample_model.warnings == [
        "instância p6 (/building/inexistente/x) sem família — ignorada"
    ]


def test_layers(sample_model: CadModel):
    counts = {layer.name: layer.count for layer in sample_model.layers}
    assert counts == {
        "pav_tipo": 8,
        "shaft": 2,
        "viario_vaga": 2,
        "AQG_PERIMETRO": 1,
        "AQG_FRENTE": 1,
        "AQG_CURVA_DE_NIVEL_MESTRA": 1,
        "AQG_PORTARIA": 1,
        "AQG_TALUDE": 1,
        "AQG_RUA": 1,
    }
    names = sample_model.layer_names
    assert names == sorted(names, key=str.lower)
    assert sample_model.layer("aqg_rua").color == "#7C8798"


def test_no_layer_frozen_or_hidden(sample_model: CadModel):
    assert all(not layer.frozen and layer.on for layer in sample_model.layers)


def test_by_type(sample_model: CadModel):
    assert sample_model.by_type == {
        "apartamento": 4,
        "CadPolygon": 2,
        "CadPolyline": 2,
        "core": 2,
        "shaft": 2,
        "vaga": 2,
        "varanda": 2,
        "CadBlock": 1,
        "CadMultiPolygon": 1,
    }
    assert list(sample_model.by_type)[0] == "apartamento"


def test_areas(sample_model: CadModel):
    by_id = sample_model.by_id
    assert by_id["s0"].area == 8000
    assert by_id["p0.0"].area == 50
    assert by_id["p0.1"].area == 50
    assert by_id["p0.2"].area == 10
    assert by_id["p0.3"].area == 1
    assert by_id["p0.4"].area == 200
    assert by_id["p2.0"].area == 12.5
    assert by_id["p3.0"].area == 12.5
    assert by_id["p4"].area == 276
    assert by_id["p5"].area == 500
    assert by_id["p1.4"].area == pytest.approx(200, abs=1e-9)
    for eid in ("s1", "s2", "s3"):
        assert by_id[eid].area is None


def test_lengths_and_closed(sample_model: CadModel):
    by_id = sample_model.by_id
    assert by_id["s0"].length == 360
    assert by_id["s1"].length == 100
    assert by_id["s2"].length == 60
    assert by_id["s2"].closed is True
    assert by_id["s1"].closed is False


def test_bboxes(sample_model: CadModel):
    by_id = sample_model.by_id
    assert by_id["p0.4"].bbox == (20, 10, 30, 30)
    assert by_id["p0.0"].bbox == (20, 10, 25, 20)
    assert by_id["p1.4"].bbox == pytest.approx((40, 10, 60, 20), abs=1e-9)
    assert by_id["p1.0"].bbox == pytest.approx((50, 10, 60, 15), abs=1e-9)
    assert by_id["p2.0"].bbox == (5, 40, 7.5, 45)
    assert by_id["p3.0"].bbox == (8, 40, 10.5, 45)
    assert sample_model.bbox == (0, 0, 100, 80)


def test_labels(sample_model: CadModel):
    by_id = sample_model.by_id
    for eid in ("p0.0", "p0.1", "p0.2"):
        assert by_id[eid].text == "2 Quartos"
    assert by_id["p0.3"].text == "T/4"
    assert by_id["p0.4"].text == "T/4"
    assert by_id["p4"].text == "talude"
    assert by_id["s0"].text is None


def test_part_attributes(sample_model: CadModel):
    part = sample_model.by_id["p0.0"]
    assert (part.type, part.layer, part.color) == ("apartamento", "pav_tipo", "#BDD9E7")
    assert (part.instance, part.family) == ("p0", "T/4")
    talude = sample_model.by_id["p4"]
    assert (talude.layer, talude.type, talude.color) == (
        "AQG_TALUDE",
        "CadMultiPolygon",
        "#B7C3D0",
    )
    assert (talude.instance, talude.family) == (None, None)


def test_indicators_copied_as_is(sample_model: CadModel):
    project = build_sample_project()
    assert sample_model.indicators == {
        "outputs": project["solution"]["outputs"],
        "inputs": project["site"]["inputs"],
        "processed_info": project["site"]["processed_info"],
        "scores": project["solution"]["scores"],
    }


def test_indicators_default_when_missing():
    model = build_model({"families": [], "solution": {"placed_objects": []}}, "x")
    assert model.indicators == {
        "outputs": [],
        "inputs": [],
        "processed_info": [],
        "scores": {},
    }


def test_units(sample_model: CadModel):
    assert sample_model.units == "metros"


def test_load_aqg_rejects_non_json():
    with pytest.raises(AqgLoadError):
        load_aqg(b"nao e json", "x")


def test_load_aqg_rejects_non_project():
    with pytest.raises(AqgLoadError):
        load_aqg(b'{"a": 1}', "x")


def test_load_aqg_equals_build_model(sample_project: dict):
    loaded = load_aqg(json.dumps(sample_project).encode(), "x")
    built = build_model(sample_project, "x")
    assert loaded == built


def test_prims_payload_matches_index(sample_model: CadModel):
    payload = prims_payload(sample_model)
    assert len(payload) == 18
    assert [item["id"] for item in payload] == list(sample_model.by_id)
    assert set(payload[0]) == {"id", "type", "layer", "color", "bbox", "shapes"}


def test_describe_model_has_no_numbers(sample_model: CadModel):
    summary = describe_model(sample_model)
    for expected in ("T/4", "Vaga 0", "AQG_TALUDE", "TotalDeUnidades", "metros"):
        assert expected in summary
    for forbidden in ("37", "1234", "8000", "276"):
        assert forbidden not in summary


def test_load_aqg_rejects_malformed_field() -> None:
    project = build_sample_project()
    project["solution"]["placed_objects"][0]["position"]["x"] = "abc"
    with pytest.raises(AqgLoadError):
        load_aqg(json.dumps(project).encode(), "x")
