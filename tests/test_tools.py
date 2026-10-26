"""Executa as 16 tools contra o AQG sintetico, sem subir a API nem o LLM.

Duas coisas sao verificadas aqui e em nenhum outro lugar:
- `run_context` e invisivel no schema JSON que vai para o modelo;
- dado invalido volta como dado, nunca como excecao.
"""

import asyncio
import json
import math

import pytest
from agno.run.base import RunContext

from src.ai_modules.tools.cad_tools import CAD_TOOLS, UI_TOOL_NAMES
from src.ai_modules.tools.cad_tools.query_tools import (
    check_setbacks,
    check_zoning,
    compare_indicators,
    compare_program,
    count_entities,
    get_entity_details,
    get_project_indicators,
    list_layers,
    measure,
    query_entities,
    search_text,
)
from src.ai_modules.tools.cad_tools.ui_tools import (
    clear_highlight,
    color_by,
    highlight_entities,
    set_layer_visibility,
    zoom_to,
)
from src.cad.model import CadModel, build_model
from tests.conftest import two_tower_families, with_annotations
from tests.make_aqg_sample import build_sample_project, rect


@pytest.fixture
def ctx(sample_model: CadModel) -> RunContext:
    return RunContext(run_id="r1", session_id="s1", dependencies={"cad": sample_model})


@pytest.fixture
def empty_ctx() -> RunContext:
    return RunContext(run_id="r1", session_id="s1", dependencies={})


def call(tool, ctx: RunContext, **kwargs) -> dict:
    """Invoca o entrypoint da tool e devolve o payload decodificado."""
    return json.loads(tool.entrypoint(run_context=ctx, **kwargs))


# --------------------------------------------------------------------------- #
# Contrato geral
# --------------------------------------------------------------------------- #


def test_sixteen_tools_are_registered():
    assert len(CAD_TOOLS) == 16
    names = {tool.name for tool in CAD_TOOLS}
    assert len(names) == 16
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


CALLS = {
    "list_layers": {},
    "count_entities": {},
    "query_entities": {},
    "get_entity_details": {"entity_id": "p0"},
    "search_text": {"query": "x"},
    "measure": {"ids": ["p0"]},
    "get_project_indicators": {},
    "compare_indicators": {"projetado": "CAProjetado", "limite": "CAMaximoExigido"},
    "check_zoning": {},
    "check_setbacks": {},
    "compare_program": {},
    "highlight_entities": {"ids": ["p0"]},
    "clear_highlight": {},
    "zoom_to": {"ids": ["p0"]},
    "set_layer_visibility": {"layers": ["pav_tipo"]},
    "color_by": {"attribute": "tipologia"},
}


def test_every_tool_reports_missing_document_as_data(empty_ctx: RunContext):
    assert set(CALLS) == {tool.name for tool in CAD_TOOLS}

    for tool in CAD_TOOLS:
        payload = call(tool, empty_ctx, **CALLS[tool.name])
        assert "erro" in payload, f"{tool.name} nao sinalizou documento ausente"


def test_every_result_has_a_summary(ctx: RunContext):
    for tool in CAD_TOOLS:
        payload = call(tool, ctx, **CALLS[tool.name])
        assert isinstance(payload.get("resumo"), str), f"{tool.name} sem resumo"


# --------------------------------------------------------------------------- #
# Tools de consulta
# --------------------------------------------------------------------------- #


def test_list_layers_sorted_by_count(ctx: RunContext):
    payload = call(list_layers, ctx, sort_by="count")
    first = payload["layers"][0]
    assert (first["nome"], first["contagem"]) == ("pav_tipo", 8)
    assert first["congelada"] is False and first["visivel"] is True
    assert payload["total"] == 9


def test_count_entities_by_family_counts_instances(ctx: RunContext):
    payload = call(count_entities, ctx, group_by="family")
    assert payload["contagens"] == {"T/4": 2, "Vaga 0": 2}
    assert payload["grupos"] == 2
    assert payload["total"] == 4
    assert payload["unidade"] == "instancias"


def test_count_entities_by_family_reports_family_type_totals(ctx: RunContext):
    payload = call(count_entities, ctx, group_by="family")
    assert payload["por_tipo_familia"] == {"Tower": 2, "Vaga": 2}
    assert payload["familias_por_tipo"] == {"Tower": 1, "Vaga": 1}
    assert payload["tipo_de_cada_familia"] == {"T/4": "Tower", "Vaga 0": "Vaga"}


def test_count_entities_by_layer(ctx: RunContext):
    payload = call(count_entities, ctx, group_by="layer")
    assert payload["contagens"]["pav_tipo"] == 8
    assert payload["total"] == 18
    assert payload["unidade"] == "entidades"


def test_count_entities_by_type_with_filter(ctx: RunContext):
    payload = call(count_entities, ctx, group_by="type", layer="pav_tipo")
    assert payload["contagens"] == {"apartamento": 4, "core": 2, "varanda": 2}


def test_query_entities_by_instance(ctx: RunContext):
    payload = call(query_entities, ctx, instance="p1")
    assert payload["ids"] == ["p1.0", "p1.1", "p1.2", "p1.3", "p1.4"]


def test_query_entities_by_family_and_type(ctx: RunContext):
    payload = call(query_entities, ctx, family="t/4", entity_type="apartamento")
    assert payload["total_encontrado"] == 4


def test_query_entities_lists_every_instance_beyond_the_page(ctx: RunContext):
    payload = call(query_entities, ctx, family="T/4", limit=1)
    assert payload["devolvidas"] == 1
    assert payload["instancias"] == ["p0", "p1"]
    assert payload["total_instancias"] == 2


def test_query_entities_text_contains_searches_label(ctx: RunContext):
    payload = call(query_entities, ctx, text_contains="2 quartos")
    assert payload["total_encontrado"] == 6


def test_query_entities_brief_keys(ctx: RunContext):
    payload = call(query_entities, ctx, instance="p0", entity_type="apartamento")
    brief = payload["entidades"][0]
    assert brief["rotulo"] == "2 Quartos"
    assert brief["instancia"] == "p0"
    assert brief["familia"] == "T/4"
    assert "bloco" not in brief and "texto" not in brief


def test_query_entities_sorted_by_area_desc(ctx: RunContext):
    payload = call(query_entities, ctx, sort_by="area_desc", limit=1)
    assert payload["ids"] == ["s0"]


def _annotations_ctx() -> RunContext:
    model = build_model(with_annotations(), "cotas.json")
    return RunContext(run_id="r1", session_id="s1", dependencies={"cad": model})


def test_query_entities_sorts_by_elevation():
    payload = call(
        query_entities, _annotations_ctx(), entity_type="cota", sort_by="cota_desc"
    )
    assert payload["ids"] == ["a1", "a0"]


def test_query_entities_near_orders_by_edge_distance():
    payload = call(
        query_entities, _annotations_ctx(), entity_type="cota", near="p0", limit=1
    )
    assert payload["ids"] == ["a0"]
    # Marco em y = 5; a borda mais baixa do pavimento-tipo de p0 esta em y = 10.
    assert payload["entidades"][0]["distancia"] == 5


def test_query_entities_unknown_near_is_data(ctx: RunContext):
    payload = call(query_entities, ctx, near="zzz")
    assert "erro" in payload


def test_query_entities_rejects_malformed_bbox(ctx: RunContext):
    payload = call(query_entities, ctx, in_bbox=[0, 0, 1])
    assert "erro" in payload


def test_search_text_finds_typology(ctx: RunContext):
    payload = call(search_text, ctx, query="2 Quartos")
    assert payload["total_encontrado"] == 6


def test_search_text_invalid_regex_is_data(ctx: RunContext):
    payload = call(search_text, ctx, query="(", regex=True)
    assert "erro" in payload


def test_measure_area_of_parts(ctx: RunContext):
    payload = call(measure, ctx, ids=["p0.0", "p0.1"], metric="area")
    assert payload["area_total"] == 100
    assert payload["unidade"] == "metros"


def test_measure_area_subtracts_holes(ctx: RunContext):
    payload = call(measure, ctx, ids=["p4"], metric="area")
    assert payload["area_total"] == 276


def test_measure_area_of_linear_ring_is_absent(ctx: RunContext):
    payload = call(measure, ctx, ids=["s2"], metric="area")
    assert payload["sem_area"] == ["s2"]


def test_measure_expands_instance_id(ctx: RunContext):
    payload = call(measure, ctx, ids=["p0"], metric="area")
    assert payload["area_total"] == 311


def test_measure_distance_between_instances(ctx: RunContext):
    payload = call(measure, ctx, ids=["p0", "p1"], metric="distance")
    # Centros das caixas: p0 (25, 20) e p1 (50, 15).
    assert payload["entre"] == ["p0", "p1"]
    assert payload["distancia"] == round(math.hypot(25, 5), 3)


def test_measure_edge_distance_between_towers(ctx: RunContext):
    payload = call(measure, ctx, ids=["p0", "p1"], metric="edge_distance")
    # Core de p0 em x 20..30; p1, girado 90 graus, em x 40..60.
    assert payload["distancia"] == pytest.approx(10, abs=1e-9)
    assert "pavimento-tipo" in payload["referencia"]


def test_measure_edge_distance_needs_two_ids(ctx: RunContext):
    payload = call(measure, ctx, ids=["p0"], metric="edge_distance")
    assert "erro" in payload


def test_measure_unknown_ids_are_data(ctx: RunContext):
    payload = call(measure, ctx, ids=["x"])
    assert payload["rejeitados"] == ["x"]


def test_get_entity_details_of_instance(ctx: RunContext):
    payload = call(get_entity_details, ctx, entity_id="p0")
    assert payload["partes"] == ["p0.0", "p0.1", "p0.2", "p0.3", "p0.4"]
    assert payload["propriedades_familia"] == {"type": "Tower", "total_pavimentos": 2}
    assert payload["hid"] == "/building/torre/T/4/0i/2f/11111111"
    assert payload["tipo_familia"] == "Tower"


def test_get_entity_details_uses_the_instance_family(
    duplicate_label_model: CadModel,
):
    ctx = RunContext(
        run_id="r1", session_id="s1", dependencies={"cad": duplicate_label_model}
    )
    payload = call(get_entity_details, ctx, entity_id="p1")
    assert payload["propriedades_familia"] == {"type": "Tower", "total_pavimentos": 3}
    counts = call(count_entities, ctx, group_by="family")
    assert counts["contagens"]["T/4"] == 2


def _units_ctx() -> RunContext:
    project = build_sample_project()
    project["families"][0]["properties"] = {
        "type": "Tower",
        "n_pavimentos_unidades": 2,
        "pav_tipo": {"tipologias": {"/area/apartamento/2 Quartos/aaaa": 2}},
    }
    model = build_model(project, "unidades.json")
    return RunContext(run_id="r1", session_id="s1", dependencies={"cad": model})


def test_get_entity_details_reports_tower_units():
    payload = call(get_entity_details, _units_ctx(), entity_id="p0")
    assert payload["unidades_por_pavimento"] == 2
    assert payload["unidades_da_torre"] == 4


def test_count_entities_by_family_sums_units():
    payload = call(count_entities, _units_ctx(), group_by="family")
    assert payload["unidades_por_familia"] == {"T/4": 8}
    assert payload["total_unidades"] == 8
    assert payload["unidades_por_torre"] == {"T/4": [4]}


def test_count_entities_without_tower_units_omits_them(ctx: RunContext):
    payload = call(count_entities, ctx, group_by="family")
    assert "unidades_por_familia" not in payload


def _descriptor_ctx() -> RunContext:
    model = build_model(two_tower_families(3), "descritivos.json")
    return RunContext(run_id="r1", session_id="s1", dependencies={"cad": model})


def test_get_entity_details_links_descriptor_group():
    payload = call(get_entity_details, _descriptor_ctx(), entity_id="p1")
    assert payload["descritivos"] == ["02"]
    assert payload["descritivo"]["altura"] == 45
    assert payload["grupo"] == ["p1"]
    assert "grupo" in payload["observacao"]


def test_get_project_indicators_links_descriptors():
    payload = call(get_project_indicators, _descriptor_ctx(), tipos=["DescritivoTorre"])
    assert payload["vinculo_descritivos"] == {"01": ["p0"], "02": ["p1"]}
    assert "TOTAL" in payload["observacao"]


def test_get_entity_details_of_part(ctx: RunContext):
    payload = call(get_entity_details, ctx, entity_id="p0.0")
    assert payload["familia"] == "T/4"
    assert payload["instancia"] == "p0"
    assert payload["area"] == 50
    assert payload["fechada"] is True


def test_get_entity_details_of_site_has_no_family(ctx: RunContext):
    payload = call(get_entity_details, ctx, entity_id="s0")
    assert "familia" not in payload
    assert payload["area"] == 8000


def test_get_entity_details_unknown_id_is_data(ctx: RunContext):
    payload = call(get_entity_details, ctx, entity_id="zzz")
    assert "erro" in payload


def test_get_project_indicators(ctx: RunContext):
    payload = call(get_project_indicators, ctx)
    totals = {i["type"]: i.get("value") for i in payload["indicadores"]}
    assert totals["TotalDeUnidades"] == 37
    assert payload["notas"]["total"] == 0.65
    assert payload["terreno"] == [{"type": "AreaDoTerreno", "value": 8000}]
    assert payload["familias"][0] == {
        "familia": "T/4",
        "tipo": "Tower",
        "propriedades": {"type": "Tower", "total_pavimentos": 2},
    }
    assert "DescritivoTorre" in payload["observacao"]


def test_get_project_indicators_filters_by_type(ctx: RunContext):
    payload = call(get_project_indicators, ctx, tipos=["TotalDeTorres", "Xyz"])
    assert payload["indicadores"] == [{"type": "TotalDeTorres", "value": 2}]
    assert payload["exigidos"] == []
    assert payload["indisponiveis"] == ["Xyz"]
    assert "TotalDeUnidades" in payload["tipos_disponiveis"]
    assert "familias" not in payload


def test_get_project_indicators_reports_avg_inclination():
    project = build_sample_project()
    project["site"]["analysis"] = {"avg_inclination": 5.2591}
    model = build_model(project, "inclinacao.json")
    ctx = RunContext(run_id="r1", session_id="s1", dependencies={"cad": model})
    payload = call(get_project_indicators, ctx, tipos=["InclinacaoMedia"])
    assert payload["terreno"] == [
        {"type": "InclinacaoMedia", "value": 5.259, "unidade": "%"}
    ]
    assert "indisponiveis" not in payload


def test_compare_indicators(ctx: RunContext):
    payload = call(
        compare_indicators, ctx, projetado="CAProjetado", limite="caMaximoExigido"
    )
    assert payload["projetado"] == {"tipo": "CAProjetado", "valor": 1.78}
    assert payload["limite"]["valor"] == 2.9
    assert payload["percentual_do_limite"] == round(1.78 / 2.9 * 100, 3)
    assert payload["folga"] == round(2.9 - 1.78, 3)
    assert payload["sentido"] == "maximo"
    assert payload["atende"] is True


def _zoning_ctx(outputs: list[dict], inputs: list[dict]) -> RunContext:
    project = build_sample_project()
    project["solution"]["outputs"] += outputs
    project["site"]["inputs"] += inputs
    model = build_model(project, "zoneamento.json")
    return RunContext(run_id="r1", session_id="s1", dependencies={"cad": model})


def test_compare_indicators_minimum_is_strict():
    ctx = _zoning_ctx(
        [{"type": "PermeabilidadeProjetada", "value": 19.99}],
        [{"type": "PermeabilidadeExigida", "value": 20}],
    )
    payload = call(
        compare_indicators,
        ctx,
        projetado="PermeabilidadeProjetada",
        limite="PermeabilidadeExigida",
    )
    assert payload["sentido"] == "minimo"
    assert payload["atende"] is False
    assert payload["folga"] == -0.01


def test_compare_indicators_reads_gabarito_height():
    ctx = _zoning_ctx(
        [{"type": "GabaritoProjetado", "value": 30}],
        [{"type": "GabaritoMaximoExigido", "altura": 45, "pavimentos": 15}],
    )
    payload = call(
        compare_indicators,
        ctx,
        projetado="GabaritoProjetado",
        limite="GabaritoMaximoExigido",
    )
    assert payload["limite"] == {"tipo": "GabaritoMaximoExigido", "valor": 45}
    assert payload["atende"] is True
    assert payload["folga"] == 15


def test_check_zoning_on_sample(ctx: RunContext):
    payload = call(check_zoning, ctx)
    assert [r["indice"] for r in payload["regras"]] == [
        "CA",
        "TO",
        "Permeabilidade",
        "Gabarito",
    ]
    assert payload["regras"][0]["atende"] is True
    assert payload["regras"][1]["indisponivel"] == ["TOProjetada", "TOExigida"]
    assert payload["regras"][3]["indisponivel"] == [
        "GabaritoProjetado",
        "GabaritoMaximoExigido",
    ]
    assert payload["nao_atende"] == []
    assert payload["atende_todas"] is None


def _setbacks_ctx(offset_y0: float, entre_blocos: float) -> RunContext:
    project = build_sample_project()
    project["site"]["elements"].append(
        {
            "cad": {
                "layer": "AQG_OFFSET",
                "type": "CadPolygon",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": rect(5, offset_y0, 95, 75),
                },
            }
        }
    )
    project["site"]["inputs"].append({"type": "RecuoFrontal", "value": 5})
    project["solution"]["outputs"].append(
        {"type": "AfastamentoProjetado", "entre_blocos": entre_blocos, "lateral": 3}
    )
    model = build_model(project, "recuos.json")
    return RunContext(run_id="r1", session_id="s1", dependencies={"cad": model})


def test_check_setbacks_all_pass():
    # Torres em y >= 10, a 10 m uma da outra; offset a partir de y = 5.
    payload = call(check_setbacks, _setbacks_ctx(5, 8))
    rows = payload["recuos"]["torres"]
    assert [r["torre"] for r in rows] == ["p0", "p1"]
    assert all(r["atende"] for r in rows)
    assert rows[0]["distancia_ate_linha_de_recuo"] == 5
    assert payload["recuos"]["recuos_declarados"] == {"RecuoFrontal": 5}
    assert payload["afastamento"]["pares"][0]["distancia"] == pytest.approx(
        10, abs=1e-9
    )
    assert payload["afastamento"]["total_pares"] == 1
    assert payload["afastamento"]["pares"][0]["folga"] == pytest.approx(2, abs=1e-9)
    assert payload["torres_que_nao_atendem"] == []
    assert payload["pares_que_nao_atendem"] == []


def test_check_setbacks_reports_failures():
    payload = call(check_setbacks, _setbacks_ctx(12, 12))
    assert payload["torres_que_nao_atendem"] == ["p0", "p1"]
    assert payload["pares_que_nao_atendem"] == [["p0", "p1"]]


def test_check_setbacks_without_data_is_unavailable(ctx: RunContext):
    payload = call(check_setbacks, ctx)
    assert "layer AQG_OFFSET" in payload["recuos"]["indisponivel"]
    assert payload["afastamento"] == {
        "indisponivel": ["AfastamentoProjetado.entre_blocos"]
    }


def _program_ctx() -> RunContext:
    project = build_sample_project()
    project["families"][0]["properties"] = {
        "type": "Tower",
        "n_pavimentos_unidades": 2,
        "pav_tipo": {"tipologias": {"/area/apartamento/2 Quartos/aaaa": 2}},
    }
    project["archprog"] = [
        {"type": "CAMin", "value": 1.5},
        {"type": "MinPavimentos", "value": 2},
        {"type": "MaxPavimentos", "value": 2},
        {"type": "MinUnitsPerFloor", "value": 3},
        {"type": "ParkingLotPerUnit", "unit_hid": "/area/apartamento", "value": 1.2},
        {
            "type": "FamilyProportion",
            "hid": "/building/apartamento/2 Quartos/aaaa",
            "value": 70,
        },
        {
            "type": "FamilyProportion",
            "hid": "/building/apartamento/3 Quartos/bbbb",
            "value": 30,
        },
    ]
    project["solution"]["outputs"] += [
        {"type": "NumeroDePavimentos", "value": 3},
        {"type": "VagasPorUnidade", "value": 1},
        {
            "type": "UnidadesPorTipologia",
            "value": {"/area/apartamento/2 Quartos/aaaa": 8},
        },
    ]
    model = build_model(project, "programa.json")
    return RunContext(run_id="r1", session_id="s1", dependencies={"cad": model})


def test_compare_program():
    payload = call(compare_program, _program_ctx())
    rules = {r["regra"]: r for r in payload["regras"]}
    assert rules["CA minimo"]["diferenca"] == round(1.78 - 1.5, 3)
    assert "atende" not in rules["CA minimo"]
    assert rules["Gabarito"] == {"regra": "Gabarito", "nao_pedido": True}
    assert rules["Pavimentos"]["atende"] is False
    assert rules["Torres"] == {"regra": "Torres", "nao_pedido": True}
    assert rules["Unidades por pavimento"]["atende"] is False
    assert rules["Vagas por unidade"]["diferenca"] == -0.2
    assert "atende" not in rules["Vagas por unidade"]
    assert rules["Proporcao de tipologias"]["tipologias"] == [
        {
            "tipologia": "2 Quartos/aaaa",
            "pedido_pct": 70,
            "projetado_pct": 100,
            "diferenca_pp": 30,
        },
        {
            "tipologia": "3 Quartos/bbbb",
            "pedido_pct": 30,
            "projetado_pct": 0,
            "diferenca_pp": -30,
        },
    ]
    assert payload["regras_que_nao_atendem"] == ["Pavimentos", "Unidades por pavimento"]
    assert payload["torres_fora_da_faixa"] == ["p0", "p1"]


def test_compare_program_without_archprog(ctx: RunContext):
    payload = call(compare_program, ctx)
    assert all(r.get("nao_pedido") for r in payload["regras"])
    assert payload["regras_que_nao_atendem"] == []


def test_check_zoning_reports_failing_index():
    ctx = _zoning_ctx(
        [{"type": "PermeabilidadeProjetada", "value": 19.99}],
        [{"type": "PermeabilidadeExigida", "value": 20}],
    )
    payload = call(check_zoning, ctx)
    assert payload["nao_atende"] == ["Permeabilidade"]
    assert payload["atende_todas"] is False


def test_compare_indicators_unknown_or_non_numeric_is_data(ctx: RunContext):
    payload = call(compare_indicators, ctx, projetado="Municipio", limite="Xyz")
    assert "erro" in payload
    assert "CAProjetado" in payload["tipos_disponiveis"]
    assert "Municipio" not in payload["tipos_disponiveis"]


# --------------------------------------------------------------------------- #
# Tools de interface
# --------------------------------------------------------------------------- #


def test_highlight_expands_instance(ctx: RunContext):
    payload = call(highlight_entities, ctx, ids=["p0"])
    assert payload["destacadas"] == 5
    assert payload["bbox"] == [20, 10, 30, 30]


def test_highlight_dedupes_and_rejects(ctx: RunContext):
    payload = call(highlight_entities, ctx, ids=["p0", "p0.1", "x"])
    assert payload["destacadas"] == 5
    assert payload["rejeitados"] == ["x"]


def test_highlight_without_ids_is_data(ctx: RunContext):
    payload = call(highlight_entities, ctx, ids=[])
    assert "erro" in payload


def test_clear_highlight(ctx: RunContext):
    payload = call(clear_highlight, ctx)
    assert "resumo" in payload


def test_zoom_to_instance(ctx: RunContext):
    payload = call(zoom_to, ctx, ids=["p1"])
    assert payload["bbox"] == pytest.approx([40, 10, 60, 20], abs=1e-9)


def test_zoom_to_unknown_layer_is_data(ctx: RunContext):
    payload = call(zoom_to, ctx, target="layer", layer="NAO_EXISTE")
    assert "erro" in payload


def test_color_by_counts_groups(ctx: RunContext):
    payload = call(color_by, ctx, attribute="tipologia")
    assert payload["grupos"] == 1
    assert payload["nomes"] == ["2 Quartos"]


def test_color_by_none_restores(ctx: RunContext):
    payload = call(color_by, ctx, attribute="nenhum")
    assert payload == {"atributo": "nenhum", "resumo": payload["resumo"]}


def test_set_layer_visibility_unknown_layer_is_data(ctx: RunContext):
    payload = call(set_layer_visibility, ctx, layers=["NAO_EXISTE"])
    assert "NAO_EXISTE" in json.dumps(payload)


# --------------------------------------------------------------------------- #
# Agente
# --------------------------------------------------------------------------- #


def test_agent_builds_with_sixteen_tools_and_the_document_summary(sample_model):
    from src.ai_modules.agents import get_cad_agent

    agent = asyncio.run(get_cad_agent(user_id="local", model=sample_model))

    assert len(agent.tools) == 16
    assert agent.tool_call_limit == 14

    instructions = "\n".join(agent.instructions)
    assert "<documento_carregado>" in instructions
    assert "Nunca invente números" in instructions
    # O resumo real do projeto tem de estar la, nao so o cabecalho do bloco.
    assert "T/4" in instructions
    assert "metros" in instructions
