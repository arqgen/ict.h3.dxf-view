"""Assertivas EXATAS sobre o indice.

Nada de `>=` aqui. Uma assertiva frouxa sobre contagem de entidades e capaz de
passar com o indexador perdendo geometria silenciosamente.
"""

from src.cad.geometry import PolylinePrim, TextPrim
from src.cad.model import (
    CadModel,
    describe_model,
    entity_raw_props,
    prims_payload,
)

# Entidades de modelspace do DXF sintetico (ver tests/make_sample.py):
# 2 LWPOLYLINE, 2 LINE, 1 CIRCLE, 1 ARC, 1 SPLINE, 1 POINT, 1 TEXT, 1 MTEXT,
# 3 INSERT, 1 DIMENSION.
EXPECTED_BY_TYPE = {
    "INSERT": 3,
    "LINE": 2,
    "LWPOLYLINE": 2,
    "ARC": 1,
    "CIRCLE": 1,
    "DIMENSION": 1,
    "MTEXT": 1,
    "POINT": 1,
    "SPLINE": 1,
    "TEXT": 1,
}
EXPECTED_ENTITY_COUNT = 14


def _contour(model: CadModel):
    entities = [e for e in model.entities if e.layer == "CONTORNO"]
    assert len(entities) == 1
    return entities[0]


def test_entity_count_is_exact(sample_model: CadModel):
    assert len(sample_model.entities) == EXPECTED_ENTITY_COUNT


def test_by_type_is_exact(sample_model: CadModel):
    assert sample_model.by_type == EXPECTED_BY_TYPE


def test_no_warnings(sample_model: CadModel):
    assert sample_model.warnings == []


def test_units_are_meters(sample_model: CadModel):
    assert sample_model.units == "metros"


def test_acad_version(sample_model: CadModel):
    assert sample_model.acad_version == "AC1024"


def test_contour_perimeter_is_exactly_68(sample_model: CadModel):
    assert _contour(sample_model).length == 68.0


def test_contour_area_is_exactly_280(sample_model: CadModel):
    assert _contour(sample_model).area == 280.0


def test_contour_is_closed_with_four_vertices(sample_model: CadModel):
    contour = _contour(sample_model)
    assert contour.closed
    assert len(contour.prims) == 1
    prim = contour.prims[0]
    assert isinstance(prim, PolylinePrim)
    # O vertice de fechamento duplicado devolvido pelo ezdxf foi normalizado.
    assert len(prim.pts) == 4


def test_open_entities_have_no_area(sample_model: CadModel):
    lines = [e for e in sample_model.entities if e.type == "LINE"]
    assert len(lines) == 2
    assert all(line.area is None for line in lines)
    assert all(line.length == 20.0 or line.length == 14.0 for line in lines)


def test_document_bbox_covers_the_contour(sample_model: CadModel):
    assert sample_model.bbox is not None
    min_x, min_y, max_x, max_y = sample_model.bbox
    assert min_x <= 0.0
    assert min_y < 0.0  # a cota fica abaixo do contorno
    assert max_x >= 20.0
    assert max_y >= 14.0


def test_bulge_became_an_arc(sample_model: CadModel):
    bulged = [
        e
        for e in sample_model.entities
        if e.type == "LWPOLYLINE" and e.layer == "PAREDES"
    ]
    assert len(bulged) == 1
    prim = bulged[0].prims[0]
    assert isinstance(prim, PolylinePrim)
    assert len(prim.pts) > 5


def test_spline_was_sampled(sample_model: CadModel):
    splines = [e for e in sample_model.entities if e.type == "SPLINE"]
    assert len(splines) == 1
    prim = splines[0].prims[0]
    assert isinstance(prim, PolylinePrim)
    assert len(prim.pts) > 20


def test_circle_is_closed_and_has_area(sample_model: CadModel):
    circles = [e for e in sample_model.entities if e.type == "CIRCLE"]
    assert len(circles) == 1
    circle = circles[0]
    assert circle.closed
    assert circle.area is not None
    # Raio 2 -> area ~12.566. Poligono inscrito subestima; toleramos 1%.
    assert abs(circle.area - 12.566) / 12.566 < 0.01


def test_mtext_escapes_were_cleaned(sample_model: CadModel):
    mtexts = [e for e in sample_model.entities if e.type == "MTEXT"]
    assert len(mtexts) == 1
    assert mtexts[0].text == "PLANTA BAIXA\nESCALA 1:50"


def test_text_prim_carries_height_and_rotation(sample_model: CadModel):
    texts = [e for e in sample_model.entities if e.type == "TEXT"]
    assert len(texts) == 1
    prim = texts[0].prims[0]
    assert isinstance(prim, TextPrim)
    assert prim.text == "PLAIN"
    assert prim.height == 1.0
    assert prim.rotation == 0.0


def test_inserts_produced_block_geometry(sample_model: CadModel):
    inserts = [e for e in sample_model.entities if e.type == "INSERT"]
    assert len(inserts) == 3
    for insert in inserts:
        assert insert.block == "PORTA"
        # O bloco tem LINE + ARC; ambos devem ter chegado achatados.
        assert len(insert.prims) == 2
        assert insert.bbox is not None


def test_block_insert_count_is_three(sample_model: CadModel):
    assert sample_model.insert_counts == {"PORTA": 3}


def test_block_names_exclude_anonymous_blocks(sample_model: CadModel):
    assert "PORTA" in sample_model.block_names
    assert not any(name.startswith("*") for name in sample_model.block_names)


def test_dimension_produced_geometry(sample_model: CadModel):
    dims = [e for e in sample_model.entities if e.type == "DIMENSION"]
    assert len(dims) == 1
    assert dims[0].prims, "cota sem geometria — o bloco anonimo nao foi resolvido"


def test_layers_include_table_and_used(sample_model: CadModel):
    names = sample_model.layer_names
    for expected in ("0", "CONTORNO", "PAREDES", "TEXTOS", "MOBILIARIO", "COTAS"):
        assert expected in names


def test_frozen_layer_is_flagged(sample_model: CadModel):
    auxiliar = sample_model.layer("AUXILIAR")
    assert auxiliar is not None
    assert auxiliar.frozen
    assert auxiliar.count == 1  # o POINT


def test_layer_counts_sum_to_entity_count(sample_model: CadModel):
    total = sum(layer.count for layer in sample_model.layers)
    assert total == EXPECTED_ENTITY_COUNT


def test_layer_colors_are_hex(sample_model: CadModel):
    contorno = sample_model.layer("CONTORNO")
    assert contorno is not None
    assert contorno.color == "#ff0000"


def test_entity_colors_are_hex(sample_model: CadModel):
    assert _contour(sample_model).color == "#ff0000"


def test_header_vars_are_exposed_and_jsonable(sample_model: CadModel):
    assert sample_model.header["$INSUNITS"] == 6
    assert sample_model.header["$ACADVER"] == "AC1024"


def test_raw_props_of_contour(sample_model: CadModel):
    contour = _contour(sample_model)
    props = entity_raw_props(sample_model, contour.id)
    assert props is not None
    assert props["layer"] == "CONTORNO"
    assert props["vertices"] == [[0.0, 0.0], [20.0, 0.0], [20.0, 14.0], [0.0, 14.0]]


def test_raw_props_of_unknown_id_is_none(sample_model: CadModel):
    assert entity_raw_props(sample_model, "nao-existe") is None


def test_prims_payload_shape(sample_model: CadModel):
    payload = prims_payload(sample_model)
    contour = next(item for item in payload if item["id"] == _contour(sample_model).id)
    assert contour["color"] == "#ff0000"
    assert contour["layer"] == "CONTORNO"
    assert contour["bbox"] == [0.0, 0.0, 20.0, 14.0]
    assert contour["shapes"] == [
        {
            "k": "p",
            "pts": [[0.0, 0.0], [20.0, 0.0], [20.0, 14.0], [0.0, 14.0]],
            "c": True,
        }
    ]


def test_prims_payload_ids_match_index(sample_model: CadModel):
    payload_ids = {item["id"] for item in prims_payload(sample_model)}
    assert payload_ids <= set(sample_model.by_id)


def test_describe_model_states_totals_without_inventing_measures(
    sample_model: CadModel,
):
    summary = describe_model(sample_model)
    assert "sample.dxf" in summary
    assert "metros" in summary
    assert f"Total de entidades indexadas: {EXPECTED_ENTITY_COUNT}" in summary
    assert "PORTA: 3" in summary
    assert "[congelada]" in summary
    assert "Avisos do parser" not in summary
