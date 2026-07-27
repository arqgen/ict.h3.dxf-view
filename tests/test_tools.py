"""Executa as 12 tools contra o DXF sintetico, sem subir a API nem o LLM.

Duas coisas sao verificadas aqui e em nenhum outro lugar:
- `run_context` e invisivel no schema JSON que vai para o modelo;
- dado invalido volta como dado, nunca como excecao.
"""

import json

import pytest
from agno.run.base import RunContext

from src.ai_modules.tools.cad_tools import CAD_TOOLS, UI_TOOL_NAMES
from src.ai_modules.tools.cad_tools.query_tools import (
    count_entities,
    get_block_definition,
    get_entity_details,
    get_header_variables,
    list_layers,
    measure,
    query_entities,
    search_text,
)
from src.ai_modules.tools.cad_tools.ui_tools import (
    clear_highlight,
    highlight_entities,
    set_layer_visibility,
    zoom_to,
)
from src.cad.model import CadModel


@pytest.fixture
def ctx(sample_model: CadModel) -> RunContext:
    return RunContext(run_id="r1", session_id="s1", dependencies={"cad": sample_model})


@pytest.fixture
def empty_ctx() -> RunContext:
    return RunContext(run_id="r1", session_id="s1", dependencies={})


def call(tool, ctx: RunContext, **kwargs) -> dict:
    """Invoca o entrypoint da tool e devolve o payload decodificado."""
    return json.loads(tool.entrypoint(run_context=ctx, **kwargs))


def _contour_id(model: CadModel) -> str:
    return next(e.id for e in model.entities if e.layer == "CONTORNO")


# --------------------------------------------------------------------------- #
# Contrato geral
# --------------------------------------------------------------------------- #


def test_twelve_tools_are_registered():
    assert len(CAD_TOOLS) == 12
    names = {tool.name for tool in CAD_TOOLS}
    assert len(names) == 12
    for ui_name in UI_TOOL_NAMES:
        assert ui_name in names


def test_every_tool_has_name_and_description():
    for tool in CAD_TOOLS:
        assert tool.name
        assert tool.description, f"{tool.name} sem descricao"


def test_run_context_is_hidden_from_the_model_schema():
    for tool in CAD_TOOLS:
        schema = tool.parameters or {}
        properties = schema.get("properties", {})
        assert "run_context" not in properties, f"{tool.name} expoe run_context"
        assert "agent" not in properties


def test_every_tool_reports_missing_document_as_data(empty_ctx: RunContext):
    calls = {
        "list_layers": {},
        "count_entities": {},
        "query_entities": {},
        "get_entity_details": {"entity_id": "1"},
        "search_text": {"query": "x"},
        "measure": {"ids": ["1"]},
        "get_block_definition": {"name": "PORTA"},
        "get_header_variables": {},
        "highlight_entities": {"ids": ["1"]},
        "clear_highlight": {},
        "zoom_to": {"ids": ["1"]},
        "set_layer_visibility": {"layers": ["0"]},
    }
    assert set(calls) == {tool.name for tool in CAD_TOOLS}

    for tool in CAD_TOOLS:
        payload = call(tool, empty_ctx, **calls[tool.name])
        assert "erro" in payload, f"{tool.name} nao sinalizou documento ausente"


# --------------------------------------------------------------------------- #
# Tools de consulta
# --------------------------------------------------------------------------- #


def test_list_layers_sorted_by_count(ctx: RunContext):
    payload = call(list_layers, ctx, sort_by="count")
    counts = [layer["contagem"] for layer in payload["layers"]]
    assert counts == sorted(counts, reverse=True)
    assert payload["total"] == len(payload["layers"])


def test_list_layers_sorted_by_name(ctx: RunContext):
    payload = call(list_layers, ctx, sort_by="name")
    names = [layer["nome"].lower() for layer in payload["layers"]]
    assert names == sorted(names)


def test_list_layers_flags_frozen(ctx: RunContext):
    payload = call(list_layers, ctx)
    auxiliar = next(item for item in payload["layers"] if item["nome"] == "AUXILIAR")
    assert auxiliar["congelada"] is True


def test_count_entities_by_type(ctx: RunContext):
    payload = call(count_entities, ctx, group_by="type")
    assert payload["total"] == 14
    assert payload["contagens"]["INSERT"] == 3
    assert payload["contagens"]["LWPOLYLINE"] == 2


def test_count_entities_by_layer(ctx: RunContext):
    payload = call(count_entities, ctx, group_by="layer")
    assert payload["contagens"]["CONTORNO"] == 1
    assert payload["contagens"]["MOBILIARIO"] == 6


def test_count_entities_by_block(ctx: RunContext):
    payload = call(count_entities, ctx, group_by="block")
    assert payload["contagens"]["PORTA"] == 3


def test_count_entities_with_filters(ctx: RunContext):
    payload = call(count_entities, ctx, group_by="type", layer="PAREDES")
    assert payload["total"] == 3  # 2 LINE + 1 LWPOLYLINE com bulge
    assert payload["contagens"] == {"LINE": 2, "LWPOLYLINE": 1}


def test_query_entities_by_type(ctx: RunContext):
    payload = call(query_entities, ctx, entity_type="LINE")
    assert payload["total_encontrado"] == 2
    assert len(payload["ids"]) == 2


def test_query_entities_type_filter_is_case_insensitive(ctx: RunContext):
    payload = call(query_entities, ctx, entity_type="line")
    assert payload["total_encontrado"] == 2


def test_query_entities_layer_contains(ctx: RunContext):
    payload = call(query_entities, ctx, layer_contains="pared")
    assert payload["total_encontrado"] == 3


def test_query_entities_closed_only_have_area(ctx: RunContext):
    payload = call(query_entities, ctx, closed_only=True)
    assert payload["total_encontrado"] > 0
    for entity in payload["entidades"]:
        assert "area" in entity


def test_query_entities_sorted_by_length_desc(ctx: RunContext, sample_model):
    payload = call(query_entities, ctx, sort_by="length_desc", limit=5)
    lengths = [e["comprimento"] for e in payload["entidades"]]
    assert lengths == sorted(lengths, reverse=True)
    # O contorno de perimetro 68 e o mais longo do desenho.
    assert payload["entidades"][0]["id"] == _contour_id(sample_model)
    assert payload["entidades"][0]["comprimento"] == 68.0


def test_query_entities_sorted_by_area_desc(ctx: RunContext, sample_model):
    payload = call(query_entities, ctx, sort_by="area_desc", closed_only=True)
    assert payload["entidades"][0]["id"] == _contour_id(sample_model)
    assert payload["entidades"][0]["area"] == 280.0


def test_query_entities_bbox_intersects_vs_contains(ctx: RunContext):
    region = [0.0, 0.0, 10.0, 10.0]
    touching = call(query_entities, ctx, in_bbox=region, bbox_mode="intersects")
    inside = call(query_entities, ctx, in_bbox=region, bbox_mode="contains")
    assert touching["total_encontrado"] >= inside["total_encontrado"]
    assert inside["total_encontrado"] > 0


def test_query_entities_rejects_malformed_bbox(ctx: RunContext):
    payload = call(query_entities, ctx, in_bbox=[0.0, 0.0])
    assert "erro" in payload


def test_query_entities_pagination(ctx: RunContext):
    first = call(query_entities, ctx, limit=5, offset=0)
    second = call(query_entities, ctx, limit=5, offset=5)
    assert first["devolvidas"] == 5
    assert first["truncado"] is True
    assert set(first["ids"]).isdisjoint(second["ids"])


def test_query_entities_limit_is_capped(ctx: RunContext):
    payload = call(query_entities, ctx, limit=99999)
    assert payload["devolvidas"] <= 200


def test_query_entities_min_length_filter(ctx: RunContext):
    payload = call(query_entities, ctx, min_length=60.0)
    assert payload["total_encontrado"] == 1
    assert payload["entidades"][0]["comprimento"] == 68.0


def test_get_entity_details_returns_raw_props(ctx: RunContext, sample_model):
    payload = call(get_entity_details, ctx, entity_id=_contour_id(sample_model))
    assert payload["layer"] == "CONTORNO"
    assert payload["fechada"] is True
    assert payload["props_dxf"]["layer"] == "CONTORNO"


def test_get_entity_details_unknown_id_is_data(ctx: RunContext):
    payload = call(get_entity_details, ctx, entity_id="nao-existe")
    assert "erro" in payload


def test_search_text_plain(ctx: RunContext):
    payload = call(search_text, ctx, query="planta")
    assert payload["total_encontrado"] == 1
    assert "PLANTA BAIXA" in payload["entidades"][0]["texto"]


def test_search_text_case_sensitive_misses(ctx: RunContext):
    payload = call(search_text, ctx, query="planta", case_sensitive=True)
    assert payload["total_encontrado"] == 0


def test_search_text_regex(ctx: RunContext):
    payload = call(search_text, ctx, query=r"ESCALA \d+:\d+", regex=True)
    assert payload["total_encontrado"] == 1


def test_search_text_invalid_regex_is_data(ctx: RunContext):
    payload = call(search_text, ctx, query="[unclosed", regex=True)
    assert "erro" in payload


def test_search_text_empty_query_is_data(ctx: RunContext):
    payload = call(search_text, ctx, query="")
    assert "erro" in payload


def test_measure_length(ctx: RunContext, sample_model):
    payload = call(measure, ctx, ids=[_contour_id(sample_model)], metric="length")
    assert payload["comprimento_total"] == 68.0
    assert payload["unidade"] == "metros"
    assert payload["aproximado"] is True


def test_measure_area(ctx: RunContext, sample_model):
    payload = call(measure, ctx, ids=[_contour_id(sample_model)], metric="area")
    assert payload["area_total"] == 280.0


def test_measure_bbox(ctx: RunContext, sample_model):
    payload = call(measure, ctx, ids=[_contour_id(sample_model)], metric="bbox")
    assert payload["bbox"] == [0.0, 0.0, 20.0, 14.0]


def test_measure_distance_needs_exactly_two(ctx: RunContext, sample_model):
    one = call(measure, ctx, ids=[_contour_id(sample_model)], metric="distance")
    assert "erro" in one


def test_measure_distance(ctx: RunContext, sample_model):
    ids = [e.id for e in sample_model.entities if e.type == "LINE"]
    payload = call(measure, ctx, ids=ids, metric="distance")
    assert payload["metrica"] == "distancia"
    assert payload["distancia"] >= 0.0


def test_measure_reports_rejected_ids(ctx: RunContext, sample_model):
    payload = call(
        measure, ctx, ids=[_contour_id(sample_model), "lixo"], metric="length"
    )
    assert payload["rejeitados"] == ["lixo"]
    assert payload["comprimento_total"] == 68.0


def test_measure_all_ids_invalid_is_data(ctx: RunContext):
    payload = call(measure, ctx, ids=["a", "b"], metric="length")
    assert "erro" in payload
    assert payload["rejeitados"] == ["a", "b"]


def test_measure_area_of_open_entity_reports_missing(ctx: RunContext, sample_model):
    line_id = next(e.id for e in sample_model.entities if e.type == "LINE")
    payload = call(measure, ctx, ids=[line_id], metric="area")
    assert payload["sem_area"] == [line_id]
    assert payload["area_total"] == 0.0


def test_get_block_definition(ctx: RunContext):
    payload = call(get_block_definition, ctx, name="PORTA")
    assert payload["insercoes"] == 3
    assert payload["conteudo"] == {"ARC": 1, "LINE": 1}
    assert len(payload["ids_das_insercoes"]) == 3


def test_get_block_definition_unknown_is_data(ctx: RunContext):
    payload = call(get_block_definition, ctx, name="NAO_EXISTE")
    assert "erro" in payload
    assert "PORTA" in payload["blocos_disponiveis"]


def test_get_header_variables_all(ctx: RunContext):
    payload = call(get_header_variables, ctx)
    assert payload["variaveis"]["$INSUNITS"] == 6
    assert payload["unidade"] == "metros"


def test_get_header_variables_named_and_normalized(ctx: RunContext):
    payload = call(get_header_variables, ctx, names=["insunits", "$ACADVER"])
    assert payload["variaveis"]["$INSUNITS"] == 6
    assert payload["variaveis"]["$ACADVER"] == "AC1024"


def test_get_header_variables_reports_unavailable(ctx: RunContext):
    payload = call(get_header_variables, ctx, names=["$NAO_EXISTE"])
    assert payload["indisponiveis"] == ["$NAO_EXISTE"]


# --------------------------------------------------------------------------- #
# Tools de interface
# --------------------------------------------------------------------------- #


def test_highlight_entities(ctx: RunContext, sample_model):
    payload = call(
        highlight_entities,
        ctx,
        ids=[_contour_id(sample_model)],
        label="contorno",
        zoom=True,
    )
    assert payload["destacadas"] == 1
    assert payload["rotulo"] == "contorno"
    assert payload["zoom"] is True
    assert payload["bbox"] == [0.0, 0.0, 20.0, 14.0]


def test_highlight_entities_dedupes_and_rejects(ctx: RunContext, sample_model):
    contour = _contour_id(sample_model)
    payload = call(highlight_entities, ctx, ids=[contour, contour, "lixo"])
    assert payload["destacadas"] == 1
    assert payload["rejeitados"] == ["lixo"]


def test_highlight_entities_empty_ids_is_data(ctx: RunContext):
    assert "erro" in call(highlight_entities, ctx, ids=[])


def test_highlight_entities_all_invalid_is_data(ctx: RunContext):
    payload = call(highlight_entities, ctx, ids=["x"])
    assert payload["destacadas"] == 0


def test_clear_highlight(ctx: RunContext):
    assert call(clear_highlight, ctx)["destaque_removido"] is True


def test_zoom_to_all(ctx: RunContext):
    payload = call(zoom_to, ctx, target="all")
    assert payload["alvo"] == "all"
    assert payload["bbox"] is not None


def test_zoom_to_ids(ctx: RunContext, sample_model):
    payload = call(zoom_to, ctx, ids=[_contour_id(sample_model)], target="ids")
    assert payload["bbox"] == [0.0, 0.0, 20.0, 14.0]


def test_zoom_to_layer(ctx: RunContext):
    payload = call(zoom_to, ctx, layer="CONTORNO", target="layer")
    assert payload["layer"] == "CONTORNO"
    assert payload["bbox"] == [0.0, 0.0, 20.0, 14.0]


def test_zoom_to_layer_is_case_insensitive(ctx: RunContext):
    payload = call(zoom_to, ctx, layer="contorno", target="layer")
    assert payload["layer"] == "CONTORNO"


def test_zoom_to_unknown_layer_is_data(ctx: RunContext):
    payload = call(zoom_to, ctx, layer="NAO_EXISTE", target="layer")
    assert "erro" in payload
    assert "CONTORNO" in payload["layers_disponiveis"]


def test_zoom_to_bbox_normalizes_inverted_region(ctx: RunContext):
    payload = call(zoom_to, ctx, bbox=[20.0, 14.0, 0.0, 0.0], target="bbox")
    assert payload["bbox"] == [0.0, 0.0, 20.0, 14.0]


def test_zoom_to_malformed_bbox_is_data(ctx: RunContext):
    assert "erro" in call(zoom_to, ctx, bbox=[1.0], target="bbox")


def test_set_layer_visibility(ctx: RunContext):
    payload = call(set_layer_visibility, ctx, layers=["PAREDES"], visible=False)
    assert payload["layers"] == ["PAREDES"]
    assert payload["visivel"] is False


def test_set_layer_visibility_isolate(ctx: RunContext):
    payload = call(
        set_layer_visibility, ctx, layers=["contorno"], visible=True, isolate=True
    )
    # O nome canonico do layer volta, nao o que o modelo digitou.
    assert payload["layers"] == ["CONTORNO"]
    assert payload["isolar"] is True


def test_set_layer_visibility_reports_unknown(ctx: RunContext):
    payload = call(set_layer_visibility, ctx, layers=["PAREDES", "FANTASMA"])
    assert payload["layers"] == ["PAREDES"]
    assert payload["desconhecidos"] == ["FANTASMA"]


def test_set_layer_visibility_all_unknown_is_data(ctx: RunContext):
    payload = call(set_layer_visibility, ctx, layers=["FANTASMA"])
    assert "erro" in payload


def test_set_layer_visibility_empty_is_data(ctx: RunContext):
    assert "erro" in call(set_layer_visibility, ctx, layers=[])


def test_every_result_carries_a_summary(ctx: RunContext, sample_model):
    contour = _contour_id(sample_model)
    results = [
        call(list_layers, ctx),
        call(count_entities, ctx),
        call(query_entities, ctx),
        call(get_entity_details, ctx, entity_id=contour),
        call(search_text, ctx, query="planta"),
        call(measure, ctx, ids=[contour]),
        call(get_block_definition, ctx, name="PORTA"),
        call(get_header_variables, ctx),
        call(highlight_entities, ctx, ids=[contour]),
        call(clear_highlight, ctx),
        call(zoom_to, ctx, target="all"),
        call(set_layer_visibility, ctx, layers=["PAREDES"]),
    ]
    assert len(results) == 12
    for payload in results:
        assert payload.get("resumo"), "resultado sem resumo para a linha do tempo"
