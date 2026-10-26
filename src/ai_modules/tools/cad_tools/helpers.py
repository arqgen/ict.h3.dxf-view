"""Utilitarios compartilhados pelas tools de CAD.

Duas regras que valem para todas as tools de CAD:

1. **Elas nunca levantam excecao por dado invalido.** Um id inexistente ou um
   filtro que nao casa voltam como dado (`erro`, `rejeitados`), porque uma
   excecao encerra a rodada de tools e o modelo perde a chance de se corrigir.
2. **As chaves do resultado sao em pt-BR** e os numeros arredondados em 3 casas —
   o modelo repete essas chaves na resposta ao usuario.
"""

import json
from typing import Any

from agno.run.base import RunContext

from src.cad.geometry import BBox
from src.cad.model import CadEntity, CadModel

ROUND_DIGITS = 3


class MissingDocument(Exception):
    """O agente foi executado sem um documento CAD nas dependencies."""


def cad_model(run_context: RunContext) -> CadModel:
    """Recupera o indice injetado pelo router.

    O modelo vive em `dependencies` e nao em `session_state` porque
    `add_dependencies_to_context` e False por default no agno: assim o objeto
    Python nunca e serializado no prompt nem persistido na sessao.
    """
    model = (run_context.dependencies or {}).get("cad")
    if model is None:
        raise MissingDocument("nenhum documento CAD carregado nesta sessao")
    return model


def dump(payload: dict[str, Any], resumo: str) -> str:
    """Serializa o resultado de uma tool.

    `resumo` e uma frase curta em pt-BR para a linha do tempo do chat — o
    frontend a le do evento `ToolCallCompleted`.
    """
    return json.dumps({**payload, "resumo": resumo}, ensure_ascii=False, default=str)


def fail(mensagem: str) -> str:
    return dump({"erro": mensagem}, mensagem)


def rnd(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), ROUND_DIGITS)


def rnd_bbox(bbox: BBox | None) -> list[float] | None:
    if bbox is None:
        return None
    return [round(float(v), ROUND_DIGITS) for v in bbox]


def entity_brief(entity: CadEntity) -> dict[str, Any]:
    """Resumo de uma entidade, com as chaves que o modelo vai citar."""
    brief: dict[str, Any] = {
        "id": entity.id,
        "tipo": entity.type,
        "layer": entity.layer,
    }

    if entity.length is not None:
        brief["comprimento"] = rnd(entity.length)
    if entity.area is not None:
        brief["area"] = rnd(entity.area)
    if entity.text:
        brief["rotulo"] = entity.text
    if entity.instance:
        brief["instancia"] = entity.instance
    if entity.family:
        brief["familia"] = entity.family
    if entity.bbox:
        brief["bbox"] = rnd_bbox(entity.bbox)

    return brief


def split_known_ids(model: CadModel, ids: list[str]) -> tuple[list[str], list[str]]:
    """Separa ids validos dos rejeitados, preservando a ordem e sem duplicar.

    Um id de instancia (`p<i>`) vale por todas as partes dela — o frontend
    aplica a mesma regra ao ler o `ToolCallStarted`.
    """
    known: list[str] = []
    rejected: list[str] = []
    seen: set[str] = set()

    for raw in ids:
        ref = str(raw)
        if ref in model.by_id:
            expanded = [ref]
        elif ref in model.instances:
            expanded = model.instances[ref].entity_ids
        else:
            if ref not in rejected:
                rejected.append(ref)
            continue

        for entity_id in expanded:
            if entity_id not in seen:
                seen.add(entity_id)
                known.append(entity_id)

    return known, rejected
