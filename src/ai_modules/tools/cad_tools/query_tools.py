"""As 8 tools de consulta ao indice do projeto.

O modelo nunca ve o arquivo AQG. Ele ve o resumo textual no system prompt e o
que estas tools devolvem — e essa e a razao de existirem: sao o unico caminho
pelo qual uma quantidade, medida ou coordenada pode entrar numa resposta.
"""

import re
from collections import Counter
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
    group_by: Literal["type", "layer", "family"] = "type",
    layer: str | None = None,
    entity_type: str | None = None,
) -> str:
    """Conta entidades do desenho, agrupadas por tipo, layer ou familia.

    PREFIRA ESTA TOOL para perguntas "quantos/quantas" sobre o que esta
    desenhado. Para "quantas torres/vagas" use `group_by="family"`, que conta
    instancias, nao partes, e devolve o total pronto por tipo de familia
    (`por_tipo_familia`: Tower, Vaga, Portaria...) — cite esse total, nao some
    as contagens. `tipo_de_cada_familia` diz quais familias sao torres e
    `familias_por_tipo` quantas familias ha de cada tipo.
    NAO use para unidades habitacionais nem areas construidas: a planta mostra
    um pavimento so — use `get_project_indicators`.

    Args:
        group_by: "type" e "layer" contam entidades (partes); "family" conta
            instancias distintas por familia.
        layer: se informado, conta somente neste layer.
        entity_type: se informado, conta somente entidades deste tipo
            (ex: apartamento, core, vaga, CadPolygon).

    Returns:
        JSON com as contagens por grupo, o total e a unidade contada.
    """
    try:
        model = cad_model(run_context)
    except MissingDocument as exc:
        return fail(str(exc))

    selected = _filter_entities(model, layer=layer, entity_type=entity_type)

    counts: dict[str, int] = {}
    extra: dict[str, Any] = {}
    if group_by == "family":
        unit = "instancias"
        instances = {e.instance for e in selected if e.instance}
        family_types: dict[str, str] = {}
        by_family_type: dict[str, int] = {}
        for instance_id in instances:
            inst = model.instances[instance_id]
            counts[inst.family] = counts.get(inst.family, 0) + 1
            family_types[inst.family] = inst.family_type
            by_family_type[inst.family_type] = (
                by_family_type.get(inst.family_type, 0) + 1
            )
        total = len(instances)
        extra = {
            "por_tipo_familia": dict(sorted(by_family_type.items())),
            "familias_por_tipo": dict(sorted(Counter(family_types.values()).items())),
            "tipo_de_cada_familia": dict(sorted(family_types.items())),
        }
    else:
        unit = "entidades"
        for entity in selected:
            key = entity.type if group_by == "type" else entity.layer
            counts[key] = counts.get(key, 0) + 1
        total = len(selected)

    ordered = dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))

    return dump(
        {
            "agrupado_por": group_by,
            "contagens": ordered,
            "grupos": len(ordered),
            "total": total,
            "unidade": unit,
            **extra,
            "filtros": {"layer": layer, "tipo": entity_type},
        },
        f"{total} {unit} contadas por {group_by}",
    )


@tool
def query_entities(
    run_context: RunContext,
    entity_type: str | None = None,
    layer: str | None = None,
    layer_contains: str | None = None,
    family: str | None = None,
    instance: str | None = None,
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

    Esta e a tool para "qual e o maior apartamento", "quais entidades estao
    nesta regiao", "liste as partes da torre p3", "onde esta a tipologia X".
    Os ids devolvidos sao exatamente os que `highlight_entities` e `zoom_to`
    aceitam. `instancias` lista TODAS as instancias encontradas, sem paginacao:
    para destacar uma familia inteira, passe essa lista a `highlight_entities`.

    Args:
        entity_type: tipo exato (ex: apartamento, varanda, core, vaga, CadPolygon).
        layer: nome exato do layer.
        layer_contains: trecho do nome do layer, sem diferenciar maiusculas.
        family: label da familia (ex: "T/4"), sem diferenciar maiusculas.
        instance: id da instancia (ex: "p3"), para listar as partes dela.
        text_contains: trecho do rotulo (tipologia ou familia), sem diferenciar
            maiusculas.
        in_bbox: regiao [min_x, min_y, max_x, max_y] em metros.
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
        family=family,
        instance=instance,
        text_contains=text_contains,
        region=region,
        bbox_mode=bbox_mode,
        min_length=min_length,
        max_length=max_length,
        closed_only=closed_only,
    )

    selected = _sort_entities(selected, sort_by)
    instances = list(dict.fromkeys(e.instance for e in selected if e.instance))

    total = len(selected)
    offset = max(0, offset)
    effective_limit = max(1, min(limit, MAX_LIMIT))
    page = selected[offset : offset + effective_limit]

    return dump(
        {
            "entidades": [entity_brief(entity) for entity in page],
            "ids": [entity.id for entity in page],
            # Sem paginacao: destacar "todas as torres de uma familia" precisa
            # de todas as instancias, mesmo quando as partes passam do limite.
            "instancias": instances,
            "total_instancias": len(instances),
            "total_encontrado": total,
            "devolvidas": len(page),
            "offset": offset,
            "truncado": total > offset + len(page),
        },
        f"{total} entidades encontradas, {len(page)} devolvidas",
    )


@tool
def get_entity_details(run_context: RunContext, entity_id: str) -> str:
    """Devolve os detalhes de uma entidade ou de uma instancia (torre, vaga...).

    Use para detalhar uma torre: passe o id da instancia (`p<i>`) e receba a
    familia, as propriedades dela e os ids das partes. Com o id de uma parte
    (`p<i>.<j>`) ou do terreno (`s<i>`), devolve medidas e atributos.

    Args:
        entity_id: id de entidade ou de instancia.

    Returns:
        JSON com tipo, layer, medidas, familia e propriedades da familia.
    """
    try:
        model = cad_model(run_context)
    except MissingDocument as exc:
        return fail(str(exc))

    ref = str(entity_id)
    if ref in model.instances:
        inst = model.instances[ref]
        return dump(
            {**_instance_info(model, ref), "partes": inst.entity_ids},
            f"detalhes da instancia {ref}",
        )

    entity = model.by_id.get(ref)
    if entity is None:
        return fail(f"entidade {entity_id} nao existe neste desenho")

    payload = {**entity_brief(entity), "fechada": entity.closed, "cor": entity.color}
    if entity.instance:
        payload.update(_instance_info(model, entity.instance))

    return dump(payload, f"detalhes da entidade {entity.id}")


def _instance_info(model: CadModel, instance_id: str) -> dict[str, Any]:
    inst = model.instances[instance_id]
    family = model.families[inst.family_index]
    return {
        "instancia": inst.id,
        "hid": inst.hid,
        "familia": inst.family,
        "tipo_familia": inst.family_type,
        "propriedades_familia": family.properties,
    }


@tool
def search_text(
    run_context: RunContext,
    query: str,
    regex: bool = False,
    case_sensitive: bool = False,
    limit: int = DEFAULT_LIMIT,
) -> str:
    """Procura no rotulo das entidades: a tipologia (apartamento e varanda) ou o
    label da familia.

    Use para achar onde esta uma tipologia ("2 Quartos") ou as partes de uma
    familia. O AQG nao tem texto livre: legendas e anotacoes nao existem aqui.

    Args:
        query: termo procurado.
        regex: trata `query` como expressao regular.
        case_sensitive: diferencia maiusculas de minusculas.
        limit: maximo de resultados (teto de 200).

    Returns:
        JSON com as entidades cujo rotulo casou, incluindo seus ids.
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
        f"{len(found)} rotulos casaram com '{query}'",
    )


@tool
def measure(
    run_context: RunContext,
    ids: list[str],
    metric: Literal["length", "area", "bbox", "distance"] = "length",
) -> str:
    """Mede entidades: comprimento, area, caixa envolvente ou distancia.

    Area existe somente para poligonos, ja descontados os furos. Area em planta
    NAO e area construida: a planta mostra um pavimento so — area construida vem
    de `get_project_indicators`.

    Args:
        ids: ids das entidades a medir; o id da instancia (`p<i>`) vale por
            todas as partes dela.
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
        refs = list(dict.fromkeys(str(i) for i in ids if str(i) not in rejected))
        if len(refs) != 2:
            return fail(
                "a metrica 'distance' exige exatamente 2 ids validos, recebeu "
                f"{len(refs)}"
            )
        return _measure_distance(model, refs, rejected)

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


def _measure_distance(model: CadModel, refs: list[str], rejected: list[str]) -> str:
    import math

    from src.cad.geometry import union_bbox

    # Uma referencia de instancia vale pela caixa de todas as suas partes.
    centers: list[tuple[float, float]] = []
    for ref in refs:
        bbox = None
        for entity_id in split_known_ids(model, [ref])[0]:
            bbox = union_bbox(bbox, model.by_id[entity_id].bbox)
        if bbox is None:
            return fail(f"{ref} nao tem geometria para medir distancia")
        min_x, min_y, max_x, max_y = bbox
        centers.append(((min_x + max_x) / 2.0, (min_y + max_y) / 2.0))

    distance = math.hypot(centers[1][0] - centers[0][0], centers[1][1] - centers[0][1])

    return dump(
        {
            "metrica": "distancia",
            "entre": refs,
            "distancia": rnd(distance),
            "referencia": "centro das caixas envolventes",
            "aproximado": True,
            "rejeitados": rejected,
        },
        f"distancia de {rnd(distance)} entre 2 entidades",
    )


@tool
def get_project_indicators(
    run_context: RunContext, tipos: list[str] | None = None
) -> str:
    """Le os indicadores do projeto calculados pelo exportador.

    PREFIRA ESTA TOOL para unidades, vagas, areas construidas, CA, TO,
    permeabilidade, gabarito e indices exigidos. Esses numeros NAO saem da
    planta: ela mostra um pavimento so. Os `DescritivoTorre` (01, 02...) nao
    identificam as torres desenhadas (`p<i>`) — nao associe um ao outro.

    Args:
        tipos: filtra indicadores, exigidos e dados do terreno pelo campo
            `type` (ex: ["TotalDeUnidades", "CAMaximoExigido"]). Se omitido,
            devolve tudo, inclusive as familias com suas propriedades. Para as
            propriedades de uma torre, use `get_entity_details("p<i>")`.

    Returns:
        JSON com indicadores projetados, exigidos, dados do terreno, notas da
        solucao e, sem filtro, as familias com suas propriedades.
    """
    try:
        model = cad_model(run_context)
    except MissingDocument as exc:
        return fail(str(exc))

    groups = {
        "indicadores": model.indicators["outputs"],
        "exigidos": model.indicators["inputs"],
        "terreno": model.indicators["processed_info"],
    }
    payload: dict[str, Any] = {}

    if tipos:
        wanted = {str(t).lower() for t in tipos}
        available = sorted(
            {
                str(item.get("type"))
                for items in groups.values()
                for item in items
                if isinstance(item, dict) and item.get("type")
            }
        )
        known = {t.lower() for t in available}
        groups = {
            key: [
                item
                for item in items
                if isinstance(item, dict)
                and str(item.get("type", "")).lower() in wanted
            ]
            for key, items in groups.items()
        }
        missing = [str(t) for t in tipos if str(t).lower() not in known]
        if missing:
            payload["indisponiveis"] = missing
            payload["tipos_disponiveis"] = available

    payload.update(groups)
    payload["notas"] = model.indicators["scores"]
    if not tipos:
        payload["familias"] = [
            {"familia": f.label, "tipo": f.type, "propriedades": f.properties}
            for f in model.families
        ]
    payload["observacao"] = (
        "os DescritivoTorre (01, 02…) nao identificam as torres desenhadas (p<i>)"
    )

    count = sum(len(items) for items in groups.values())
    return dump(payload, f"{count} indicadores lidos")


# (indice, projetado, limite, campo do limite, sentido)
ZONING_RULES = (
    ("CA", "CAProjetado", "CAMaximoExigido", "value", "maximo"),
    ("TO", "TOProjetada", "TOExigida", "value", "maximo"),
    (
        "Permeabilidade",
        "PermeabilidadeProjetada",
        "PermeabilidadeExigida",
        "value",
        "minimo",
    ),
    ("Gabarito", "GabaritoProjetado", "GabaritoMaximoExigido", "altura", "maximo"),
)


@tool
def compare_indicators(run_context: RunContext, projetado: str, limite: str) -> str:
    """Compara um indicador projetado com um limite: se atende, folga e percentual.

    Para CA, TO, permeabilidade e gabarito, PREFIRA `check_zoning`, que ja
    compara os quatro com o sentido certo. Use esta tool para um par fora
    desses quatro. Voce passa os NOMES dos indicadores, nunca valores: a tool
    le os numeros do arquivo. Nao faca essas contas por conta propria.

    Args:
        projetado: tipo do indicador projetado (ex: "CAProjetado").
        limite: tipo do indicador de referencia (ex: "CAMaximoExigido").

    Returns:
        JSON com os dois valores, o `sentido` do limite (maximo ou minimo),
        se `atende`, a `folga` (positiva quando atende) e o
        `percentual_do_limite`.
    """
    try:
        model = cad_model(run_context)
    except MissingDocument as exc:
        return fail(str(exc))

    result, missing = _compare(model, projetado, limite)
    if result is None:
        return dump(
            {
                "erro": f"indicador numerico '{missing[0]}' nao existe neste projeto",
                "tipos_disponiveis": _numeric_indicator_types(model),
            },
            f"indicador '{missing[0]}' indisponivel",
        )

    verdict = "atende" if result["atende"] else "nao atende"
    return dump(result, f"{projetado} {verdict} {limite}")


@tool
def check_zoning(run_context: RunContext) -> str:
    """Verifica se o projeto atende CA, TO, permeabilidade e gabarito.

    USE ESTA TOOL para "o projeto esta dentro dos indices?" e para qualquer
    indice isolado ("atende o CA?", "qual a folga da TO?", "a permeabilidade
    atende?"). Cada indice e comparado no sentido certo: CA, TO e gabarito sao
    maximos; permeabilidade e minimo. Cite `atende`, `folga` e os totais
    prontos (`nao_atende`, `atende_todas`) — nao refaca a conta.

    Returns:
        JSON com uma comparacao por indice em `regras` (ou `indisponivel` com
        os tipos ausentes), a lista `nao_atende` e `atende_todas`, que e
        `null` quando falta dado para concluir.
    """
    try:
        model = cad_model(run_context)
    except MissingDocument as exc:
        return fail(str(exc))

    rules: list[dict[str, Any]] = []
    failing: list[str] = []
    unavailable = False
    for index, projected, limit, _, _ in ZONING_RULES:
        result, missing = _compare(model, projected, limit)
        if result is None:
            rules.append({"indice": index, "indisponivel": missing})
            unavailable = True
            continue
        rules.append({"indice": index, **result})
        if not result["atende"]:
            failing.append(index)

    if failing:
        all_ok: bool | None = False
    else:
        all_ok = None if unavailable else True

    summary = f"nao atende: {', '.join(failing)}" if failing else "nenhum indice falha"
    return dump(
        {"regras": rules, "nao_atende": failing, "atende_todas": all_ok}, summary
    )


def _compare(
    model: CadModel, projetado: str, limite: str
) -> tuple[dict[str, Any] | None, list[str]]:
    """Resultado de uma comparacao, ou None e os tipos que faltam."""
    field, sense = "value", "maximo"
    for _, _, name, rule_field, rule_sense in ZONING_RULES:
        if name.lower() == limite.lower():
            field, sense = rule_field, rule_sense

    used = _numeric_indicator(model, projetado)
    ref = _numeric_indicator(model, limite, field)
    missing = [name for name, v in ((projetado, used), (limite, ref)) if v is None]
    if used is None or ref is None:
        return None, missing

    maximum = sense == "maximo"
    return {
        "projetado": {"tipo": projetado, "valor": used},
        "limite": {"tipo": limite, "valor": ref},
        "sentido": sense,
        "atende": used <= ref if maximum else used >= ref,
        "folga": rnd(ref - used if maximum else used - ref),
        "percentual_do_limite": rnd(used / ref * 100) if ref else None,
    }, []


def _indicator_items(model: CadModel) -> list[dict[str, Any]]:
    return [
        item
        for key in ("outputs", "inputs", "processed_info")
        for item in model.indicators[key]
        if isinstance(item, dict)
    ]


def _numeric_indicator(
    model: CadModel, name: str, field: str = "value"
) -> float | None:
    for item in _indicator_items(model):
        value = item.get(field)
        if str(item.get("type", "")).lower() != name.lower():
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return None


def _numeric_indicator_types(model: CadModel) -> list[str]:
    return sorted(
        {
            str(item["type"])
            for item in _indicator_items(model)
            if item.get("type")
            and isinstance(item.get("value"), (int, float))
            and not isinstance(item.get("value"), bool)
        }
    )


def _filter_entities(
    model: CadModel,
    layer: str | None = None,
    entity_type: str | None = None,
    layer_contains: str | None = None,
    family: str | None = None,
    instance: str | None = None,
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
    family_exact = family.lower() if family else None
    type_exact = entity_type.lower() if entity_type else None
    text_part = text_contains.lower() if text_contains else None

    for entity in model.entities:
        if type_exact and entity.type.lower() != type_exact:
            continue
        if layer_exact and entity.layer.lower() != layer_exact:
            continue
        if layer_part and layer_part not in entity.layer.lower():
            continue
        if family_exact and (entity.family or "").lower() != family_exact:
            continue
        if instance and entity.instance != instance:
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
    get_project_indicators,
    compare_indicators,
    check_zoning,
]
