"""As 4 tools que agem sobre o viewer.

Elas sao o que transforma uma resposta de texto numa resposta *apontada*: o
usuario ve no desenho as entidades que a frase menciona.

Como o efeito visual chega ao browser: o servidor apenas valida e devolve o que
seria aplicado. O frontend observa o stream SSE e, ao ver um evento
`ToolCallStarted` cujo `tool.tool_name` esta entre estas quatro, aplica
`tool.tool_args` no canvas. Verificado em `agno/run/agent.py:416` e
`agno/models/response.py:28` — nao existe canal paralelo nem `CustomEvent` aqui,
e de proposito: um so caminho de dados, um so lugar para depurar.
"""

from typing import Literal

from agno.run.base import RunContext
from agno.tools import tool

from src.cad.geometry import union_bbox

from .helpers import (
    MissingDocument,
    cad_model,
    dump,
    fail,
    rnd_bbox,
    split_known_ids,
)

MAX_HIGHLIGHT = 5000


@tool
def highlight_entities(
    run_context: RunContext,
    ids: list[str],
    label: str = "",
    zoom: bool = True,
) -> str:
    """ACAO DE INTERFACE: destaca entidades no desenho para o usuario ver.

    Use SEMPRE que citar entidades especificas na resposta. Ligar a frase ao
    desenho e o principal valor desta ferramenta — uma resposta com ids que o
    usuario nao consegue localizar visualmente vale muito menos.

    Args:
        ids: ids das entidades a destacar (maximo 5000).
        label: rotulo curto mostrado no viewer (ex: "paredes externas").
        zoom: se True, tambem reenquadra a vista sobre o destaque.

    Returns:
        JSON com quantas entidades foram destacadas e quais ids foram rejeitados.
    """
    try:
        model = cad_model(run_context)
    except MissingDocument as exc:
        return fail(str(exc))

    if not ids:
        return fail("nenhum id informado")

    known, rejected = split_known_ids(model, ids)

    truncated = len(known) > MAX_HIGHLIGHT
    applied = known[:MAX_HIGHLIGHT]

    if not applied:
        return dump(
            {"destacadas": 0, "rejeitados": rejected},
            "nenhum id valido para destacar",
        )

    bbox = None
    for entity_id in applied:
        bbox = union_bbox(bbox, model.by_id[entity_id].bbox)

    return dump(
        {
            "destacadas": len(applied),
            "rotulo": label or None,
            "zoom": zoom,
            "bbox": rnd_bbox(bbox),
            "rejeitados": rejected,
            "truncado": truncated,
        },
        f"{len(applied)} entidades destacadas no desenho",
    )


@tool
def clear_highlight(run_context: RunContext) -> str:
    """ACAO DE INTERFACE: remove o destaque atual do desenho.

    Use quando o destaque anterior nao for mais relevante para o assunto.

    Returns:
        JSON confirmando a limpeza.
    """
    try:
        cad_model(run_context)
    except MissingDocument as exc:
        return fail(str(exc))

    return dump({"destaque_removido": True}, "destaque removido")


@tool
def zoom_to(
    run_context: RunContext,
    ids: list[str] | None = None,
    layer: str | None = None,
    bbox: list[float] | None = None,
    target: Literal["ids", "layer", "bbox", "all"] = "ids",
) -> str:
    """ACAO DE INTERFACE: reenquadra a vista do desenho.

    Use para levar o usuario ate a regiao de que a resposta fala. Nao repita o
    mesmo enquadramento que ja esta ativo.

    Args:
        ids: ids a enquadrar, quando target="ids".
        layer: nome do layer a enquadrar, quando target="layer".
        bbox: regiao [min_x, min_y, max_x, max_y], quando target="bbox".
        target: o que enquadrar — "ids", "layer", "bbox" ou "all" (desenho todo).

    Returns:
        JSON com a caixa efetivamente enquadrada.
    """
    try:
        model = cad_model(run_context)
    except MissingDocument as exc:
        return fail(str(exc))

    if target == "all":
        return dump(
            {"alvo": "all", "bbox": rnd_bbox(model.bbox)},
            "vista enquadrada no desenho completo",
        )

    if target == "bbox":
        if not bbox or len(bbox) != 4:
            return fail("bbox precisa de 4 numeros: [min_x, min_y, max_x, max_y]")
        region = (
            min(bbox[0], bbox[2]),
            min(bbox[1], bbox[3]),
            max(bbox[0], bbox[2]),
            max(bbox[1], bbox[3]),
        )
        return dump(
            {"alvo": "bbox", "bbox": rnd_bbox(region)},
            "vista enquadrada na regiao informada",
        )

    if target == "layer":
        if not layer:
            return fail("informe o nome do layer")
        found = model.layer(layer)
        if found is None:
            return dump(
                {
                    "erro": f"layer '{layer}' nao existe",
                    "layers_disponiveis": model.layer_names[:30],
                },
                f"layer '{layer}' nao encontrado",
            )
        if found.bbox is None:
            return fail(f"layer '{found.name}' nao tem geometria para enquadrar")
        return dump(
            {"alvo": "layer", "layer": found.name, "bbox": rnd_bbox(found.bbox)},
            f"vista enquadrada no layer {found.name}",
        )

    if not ids:
        return fail("nenhum id informado")

    known, rejected = split_known_ids(model, ids)
    if not known:
        return dump(
            {"erro": "nenhum id valido", "rejeitados": rejected},
            "nenhum id valido para enquadrar",
        )

    region = None
    for entity_id in known:
        region = union_bbox(region, model.by_id[entity_id].bbox)

    if region is None:
        return fail("as entidades informadas nao possuem geometria")

    return dump(
        {
            "alvo": "ids",
            "entidades": len(known),
            "bbox": rnd_bbox(region),
            "rejeitados": rejected,
        },
        f"vista enquadrada em {len(known)} entidades",
    )


@tool
def set_layer_visibility(
    run_context: RunContext,
    layers: list[str],
    visible: bool = True,
    isolate: bool = False,
) -> str:
    """ACAO DE INTERFACE: mostra ou oculta layers no viewer.

    Use com isolate=True quando a resposta tratar de um layer especifico e o
    resto do desenho estiver poluindo a leitura.

    Args:
        layers: nomes dos layers afetados.
        visible: True mostra, False oculta.
        isolate: se True, deixa visiveis apenas os layers informados.

    Returns:
        JSON com os layers aplicados e os nomes nao reconhecidos.
    """
    try:
        model = cad_model(run_context)
    except MissingDocument as exc:
        return fail(str(exc))

    if not layers:
        return fail("nenhum layer informado")

    applied: list[str] = []
    unknown: list[str] = []

    for raw in layers:
        found = model.layer(str(raw))
        if found is None:
            unknown.append(str(raw))
        else:
            applied.append(found.name)

    if not applied:
        return dump(
            {
                "erro": "nenhum layer valido",
                "desconhecidos": unknown,
                "layers_disponiveis": model.layer_names[:30],
            },
            "nenhum layer valido",
        )

    action = "isolados" if isolate else ("visiveis" if visible else "ocultos")

    return dump(
        {
            "layers": applied,
            "visivel": visible,
            "isolar": isolate,
            "desconhecidos": unknown,
        },
        f"{len(applied)} layers {action}",
    )


UI_TOOLS = [
    highlight_entities,
    clear_highlight,
    zoom_to,
    set_layer_visibility,
]

# Nomes que o frontend precisa reconhecer no stream para aplicar no canvas.
UI_TOOL_NAMES = [
    "highlight_entities",
    "clear_highlight",
    "zoom_to",
    "set_layer_visibility",
]
