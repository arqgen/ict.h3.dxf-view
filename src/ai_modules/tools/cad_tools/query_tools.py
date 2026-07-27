"""As 8 tools de consulta ao indice do desenho.

O modelo nunca ve o arquivo DXF. Ele ve o resumo textual no system prompt e o
que estas tools devolvem — e essa e a razao de existirem: sao o unico caminho
pelo qual uma quantidade, medida ou coordenada pode entrar numa resposta.
"""

import re
from typing import Any, Literal

from agno.run.base import RunContext
from agno.tools import tool

from src.cad.geometry import bbox_contains, bbox_intersects
from src.cad.model import CadEntity, CadModel

from .helpers import (
    MissingDocument,
    cad_model,
    dump,
    entity_brief,
    fail,
    rnd,
    rnd_bbox,
    split_known_ids,
)

DEFAULT_LIMIT = 40
MAX_LIMIT = 200


@tool
def list_layers(
    run_context: RunContext,
    sort_by: Literal["count", "name"] = "count",
) -> str:
    """Lista todos os layers do desenho com contagem de entidades e cor.

    Use para responder "quais layers existem" ou antes de filtrar por layer,
    quando nao souber o nome exato — nomes de layer sao sensiveis a grafia.

    Args:
        sort_by: "count" ordena do layer mais populoso ao menos; "name" ordena
            alfabeticamente.

    Returns:
        JSON com a lista de layers (nome, contagem, cor, tipos, congelada).
    """
    try:
        model = cad_model(run_context)
    except MissingDocument as exc:
        return fail(str(exc))

    layers = list(model.layers)
    if sort_by == "count":
        layers.sort(key=lambda layer: (-layer.count, layer.name.lower()))
    else:
        layers.sort(key=lambda layer: layer.name.lower())

    payload = [
        {
            "nome": layer.name,
            "contagem": layer.count,
            "cor": layer.color,
            "tipos": layer.by_type,
            "congelada": layer.frozen,
            "visivel": layer.on,
        }
        for layer in layers
    ]

    return dump(
        {"layers": payload, "total": len(payload)},
        f"{len(payload)} layers listados",
    )


@tool
def count_entities(
    run_context: RunContext,
    group_by: Literal["type", "layer", "block"] = "type",
    layer: str | None = None,
    entity_type: str | None = None,
) -> str:
    """Conta entidades, agrupadas por tipo, layer ou bloco.

    PREFIRA ESTA TOOL para qualquer pergunta do tipo "quantos/quantas". Ela e
    mais barata e mais confiavel que listar entidades e contar o resultado.

    Args:
        group_by: dimensao do agrupamento — "type", "layer" ou "block".
        layer: se informado, conta somente neste layer.
        entity_type: se informado, conta somente entidades deste tipo DXF
            (ex: LINE, LWPOLYLINE, INSERT).

    Returns:
        JSON com as contagens por grupo e o total filtrado.
    """
    try:
        model = cad_model(run_context)
    except MissingDocument as exc:
        return fail(str(exc))

    selected = _filter_entities(model, layer=layer, entity_type=entity_type)

    counts: dict[str, int] = {}
    for entity in selected:
        if group_by == "type":
            key = entity.type
        elif group_by == "layer":
            key = entity.layer
        else:
            key = entity.block or "(sem bloco)"
        counts[key] = counts.get(key, 0) + 1

    ordered = dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))

    return dump(
        {
            "agrupado_por": group_by,
            "contagens": ordered,
            "total": len(selected),
            "filtros": {"layer": layer, "tipo": entity_type},
        },
        f"{len(selected)} entidades contadas por {group_by}",
    )


@tool
def query_entities(
    run_context: RunContext,
    entity_type: str | None = None,
    layer: str | None = None,
    layer_contains: str | None = None,
    block_name: str | None = None,
    text_contains: str | None = None,
    in_bbox: list[float] | None = None,
    bbox_mode: Literal["intersects", "contains"] = "intersects",
    min_length: float | None = None,
    max_length: float | None = None,
    closed_only: bool = False,
    sort_by: Literal[
        "length_desc", "length_asc", "area_desc", "area_asc", "none"
    ] = "none",
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> str:
    """Busca entidades por filtros combinados e devolve seus ids e medidas.

    Esta e a tool para "qual e a maior parede", "quais entidades estao nesta
    regiao", "liste as pecas do layer X". Os ids devolvidos sao exatamente os
    que `highlight_entities` e `zoom_to` aceitam.

    Args:
        entity_type: tipo DXF exato (ex: LINE, LWPOLYLINE, CIRCLE, INSERT).
        layer: nome exato do layer.
        layer_contains: trecho do nome do layer, sem diferenciar maiusculas.
        block_name: nome do bloco, para filtrar insercoes.
        text_contains: trecho do texto da entidade, sem diferenciar maiusculas.
        in_bbox: regiao [min_x, min_y, max_x, max_y] em unidades do desenho.
        bbox_mode: "intersects" pega quem toca a regiao; "contains" so quem
            esta inteiramente dentro dela.
        min_length: comprimento minimo.
        max_length: comprimento maximo.
        closed_only: apenas entidades fechadas (as unicas que possuem area).
        sort_by: ordenacao por comprimento ou area.
        limit: maximo de entidades devolvidas (teto de 200).
        offset: quantas entidades pular, para paginar.

    Returns:
        JSON com as entidades encontradas, o total antes da paginacao e os ids.
    """
    try:
        model = cad_model(run_context)
    except MissingDocument as exc:
        return fail(str(exc))

    region: tuple[float, float, float, float] | None = None
    if in_bbox is not None:
        if len(in_bbox) != 4:
            return fail("in_bbox precisa de 4 numeros: [min_x, min_y, max_x, max_y]")
        region = (
            min(in_bbox[0], in_bbox[2]),
            min(in_bbox[1], in_bbox[3]),
            max(in_bbox[0], in_bbox[2]),
            max(in_bbox[1], in_bbox[3]),
        )

    selected = _filter_entities(
        model,
        layer=layer,
        entity_type=entity_type,
        layer_contains=layer_contains,
        block_name=block_name,
        text_contains=text_contains,
        region=region,
        bbox_mode=bbox_mode,
        min_length=min_length,
        max_length=max_length,
        closed_only=closed_only,
    )

    selected = _sort_entities(selected, sort_by)

    total = len(selected)
    offset = max(0, offset)
    effective_limit = max(1, min(limit, MAX_LIMIT))
    page = selected[offset : offset + effective_limit]

    return dump(
        {
            "entidades": [entity_brief(entity) for entity in page],
            "ids": [entity.id for entity in page],
            "total_encontrado": total,
            "devolvidas": len(page),
            "offset": offset,
            "truncado": total > offset + len(page),
        },
        f"{total} entidades encontradas, {len(page)} devolvidas",
    )


@tool
def get_entity_details(run_context: RunContext, entity_id: str) -> str:
    """Devolve todos os atributos DXF crus de uma entidade especifica.

    Use quando precisar de uma propriedade que as outras tools nao expoem
    (raio, angulos, escala de insercao, estilo de texto).

    Args:
        entity_id: id da entidade, como devolvido por `query_entities`.

    Returns:
        JSON com tipo, layer, medidas e os atributos DXF crus.
    """
    try:
        model = cad_model(run_context)
    except MissingDocument as exc:
        return fail(str(exc))

    entity = model.by_id.get(str(entity_id))
    if entity is None:
        return fail(f"entidade {entity_id} nao existe neste desenho")

    from src.cad.model import entity_raw_props

    return dump(
        {
            **entity_brief(entity),
            "fechada": entity.closed,
            "cor": entity.color,
            "props_dxf": entity_raw_props(model, entity.id) or {},
        },
        f"detalhes da entidade {entity.id}",
    )


@tool
def search_text(
    run_context: RunContext,
    query: str,
    regex: bool = False,
    case_sensitive: bool = False,
    limit: int = DEFAULT_LIMIT,
) -> str:
    """Procura texto entre as entidades de texto do desenho (TEXT, MTEXT, cotas).

    Use para achar legendas, titulos, numeros de ambiente ou qualquer anotacao.

    Args:
        query: termo procurado.
        regex: trata `query` como expressao regular.
        case_sensitive: diferencia maiusculas de minusculas.
        limit: maximo de resultados (teto de 200).

    Returns:
        JSON com as entidades cujo texto casou, incluindo seus ids.
    """
    try:
        model = cad_model(run_context)
    except MissingDocument as exc:
        return fail(str(exc))

    if not query:
        return fail("query vazia")

    if regex:
        try:
            pattern = re.compile(query, 0 if case_sensitive else re.IGNORECASE)
        except re.error as exc:
            return fail(f"expressao regular invalida: {exc}")

        def matches(text: str) -> bool:
            return pattern.search(text) is not None
    else:
        needle = query if case_sensitive else query.lower()

        def matches(text: str) -> bool:
            return needle in (text if case_sensitive else text.lower())

    found = [
        entity for entity in model.entities if entity.text and matches(entity.text)
    ]

    effective_limit = max(1, min(limit, MAX_LIMIT))
    page = found[:effective_limit]

    return dump(
        {
            "entidades": [entity_brief(entity) for entity in page],
            "ids": [entity.id for entity in page],
            "total_encontrado": len(found),
            "truncado": len(found) > len(page),
        },
        f"{len(found)} textos casaram com '{query}'",
    )


@tool
def measure(
    run_context: RunContext,
    ids: list[str],
    metric: Literal["length", "area", "bbox", "distance"] = "length",
) -> str:
    """Mede entidades: comprimento, area, caixa envolvente ou distancia.

    As medidas sao aproximacoes calculadas sobre a geometria achatada, e area
    existe somente para entidades fechadas. Declare isso ao usuario.

    Args:
        ids: ids das entidades a medir.
        metric: "length" soma comprimentos; "area" soma areas; "bbox" devolve a
            caixa envolvente do conjunto; "distance" exige exatamente 2 ids e
            devolve a distancia entre os centros das suas caixas.

    Returns:
        JSON com a medida pedida, por entidade e o total.
    """
    try:
        model = cad_model(run_context)
    except MissingDocument as exc:
        return fail(str(exc))

    known, rejected = split_known_ids(model, ids)
    if not known:
        return dump(
            {"erro": "nenhum id valido", "rejeitados": rejected},
            "nenhum id valido para medir",
        )

    entities = [model.by_id[entity_id] for entity_id in known]

    if metric == "distance":
        if len(entities) != 2:
            return fail(
                "a metrica 'distance' exige exatamente 2 ids validos, recebeu "
                f"{len(entities)}"
            )
        return _measure_distance(entities, rejected)

    if metric == "bbox":
        from src.cad.geometry import union_bbox

        total_bbox = None
        for entity in entities:
            total_bbox = union_bbox(total_bbox, entity.bbox)
        return dump(
            {
                "bbox": rnd_bbox(total_bbox),
                "entidades": len(entities),
                "rejeitados": rejected,
            },
            f"bbox de {len(entities)} entidades",
        )

    key = "comprimento" if metric == "length" else "area"
    per_entity: list[dict[str, Any]] = []
    total = 0.0
    without_metric: list[str] = []

    for entity in entities:
        value = entity.length if metric == "length" else entity.area
        if value is None:
            without_metric.append(entity.id)
            continue
        total += value
        per_entity.append({"id": entity.id, "tipo": entity.type, key: rnd(value)})

    payload: dict[str, Any] = {
        "metrica": key,
        "por_entidade": per_entity,
        f"{key}_total": rnd(total),
        "unidade": model.units,
        "aproximado": True,
        "rejeitados": rejected,
    }
    if without_metric:
        payload["sem_" + key] = without_metric

    return dump(payload, f"{key} total de {len(per_entity)} entidades: {rnd(total)}")


def _measure_distance(entities: list[CadEntity], rejected: list[str]) -> str:
    import math

    centers: list[tuple[float, float]] = []
    for entity in entities:
        if entity.bbox is None:
            return fail(f"entidade {entity.id} nao tem geometria para medir distancia")
        min_x, min_y, max_x, max_y = entity.bbox
        centers.append(((min_x + max_x) / 2.0, (min_y + max_y) / 2.0))

    distance = math.hypot(centers[1][0] - centers[0][0], centers[1][1] - centers[0][1])

    return dump(
        {
            "metrica": "distancia",
            "entre": [entities[0].id, entities[1].id],
            "distancia": rnd(distance),
            "referencia": "centro das caixas envolventes",
            "aproximado": True,
            "rejeitados": rejected,
        },
        f"distancia de {rnd(distance)} entre 2 entidades",
    )


@tool
def get_block_definition(run_context: RunContext, name: str) -> str:
    """Descreve a definicao de um bloco: o que ele contem e quantas vezes e usado.

    Use quando o usuario perguntar o que um bloco representa ou quantas vezes
    aparece no desenho.

    Args:
        name: nome do bloco, como aparece em `count_entities(group_by="block")`.

    Returns:
        JSON com os tipos de entidade dentro do bloco e o numero de insercoes.
    """
    try:
        model = cad_model(run_context)
    except MissingDocument as exc:
        return fail(str(exc))

    if name not in model.doc.blocks:
        available = model.block_names[:20]
        return dump(
            {
                "erro": f"bloco '{name}' nao existe neste desenho",
                "blocos_disponiveis": available,
            },
            f"bloco '{name}' nao encontrado",
        )

    block = model.doc.blocks[name]

    counts: dict[str, int] = {}
    for entity in block:
        counts[entity.dxftype()] = counts.get(entity.dxftype(), 0) + 1

    insert_ids = [entity.id for entity in model.entities if entity.block == name]

    return dump(
        {
            "bloco": name,
            "conteudo": dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))),
            "total_entidades": sum(counts.values()),
            "insercoes": len(insert_ids),
            "ids_das_insercoes": insert_ids[:MAX_LIMIT],
        },
        f"bloco '{name}' com {sum(counts.values())} entidades e "
        f"{len(insert_ids)} insercoes",
    )


@tool
def get_header_variables(
    run_context: RunContext, names: list[str] | None = None
) -> str:
    """Le variaveis do cabecalho do DXF ($INSUNITS, $ACADVER, $LTSCALE, ...).

    Use quando a pergunta depender de configuracao do arquivo, em especial a
    unidade de desenho.

    Args:
        names: variaveis desejadas. Se omitido, devolve todas as disponiveis.

    Returns:
        JSON com as variaveis encontradas e as nao disponiveis.
    """
    try:
        model = cad_model(run_context)
    except MissingDocument as exc:
        return fail(str(exc))

    if not names:
        return dump(
            {"variaveis": model.header, "unidade": model.units},
            f"{len(model.header)} variaveis de cabecalho",
        )

    found: dict[str, Any] = {}
    missing: list[str] = []
    for raw_name in names:
        key = str(raw_name).upper()
        if not key.startswith("$"):
            key = "$" + key
        if key in model.header:
            found[key] = model.header[key]
        else:
            missing.append(key)

    return dump(
        {"variaveis": found, "indisponiveis": missing, "unidade": model.units},
        f"{len(found)} variaveis lidas",
    )


def _filter_entities(
    model: CadModel,
    layer: str | None = None,
    entity_type: str | None = None,
    layer_contains: str | None = None,
    block_name: str | None = None,
    text_contains: str | None = None,
    region: tuple[float, float, float, float] | None = None,
    bbox_mode: str = "intersects",
    min_length: float | None = None,
    max_length: float | None = None,
    closed_only: bool = False,
) -> list[CadEntity]:
    result: list[CadEntity] = []

    layer_exact = layer.lower() if layer else None
    layer_part = layer_contains.lower() if layer_contains else None
    block_exact = block_name.lower() if block_name else None
    type_exact = entity_type.upper() if entity_type else None
    text_part = text_contains.lower() if text_contains else None

    for entity in model.entities:
        if type_exact and entity.type != type_exact:
            continue
        if layer_exact and entity.layer.lower() != layer_exact:
            continue
        if layer_part and layer_part not in entity.layer.lower():
            continue
        if block_exact and (entity.block or "").lower() != block_exact:
            continue
        if text_part and (not entity.text or text_part not in entity.text.lower()):
            continue
        if closed_only and not entity.closed:
            continue
        if min_length is not None and (
            entity.length is None or entity.length < min_length
        ):
            continue
        if max_length is not None and (
            entity.length is None or entity.length > max_length
        ):
            continue
        if region is not None:
            if entity.bbox is None:
                continue
            if bbox_mode == "contains":
                if not bbox_contains(region, entity.bbox):
                    continue
            elif not bbox_intersects(region, entity.bbox):
                continue

        result.append(entity)

    return result


def _sort_entities(entities: list[CadEntity], sort_by: str) -> list[CadEntity]:
    if sort_by == "none":
        return entities

    metric = "length" if sort_by.startswith("length") else "area"
    descending = sort_by.endswith("_desc")

    # Entidades sem a metrica vao para o fim em qualquer direcao — sao ruido
    # numa pergunta do tipo "qual a maior".
    with_metric = [e for e in entities if getattr(e, metric) is not None]
    without_metric = [e for e in entities if getattr(e, metric) is None]

    with_metric.sort(key=lambda e: getattr(e, metric), reverse=descending)

    return with_metric + without_metric


QUERY_TOOLS = [
    list_layers,
    count_entities,
    query_entities,
    get_entity_details,
    search_text,
    measure,
    get_block_definition,
    get_header_variables,
]
