"""Utilitarios compartilhados pelas tools de CAD.

Duas regras que valem para todas as 12 tools:

1. **Elas nunca levantam excecao por dado invalido.** Um id inexistente ou um
   bloco que nao existe voltam como dado (`erro`, `rejeitados`), porque uma
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
        brief["texto"] = entity.text
    if entity.block:
        brief["bloco"] = entity.block
    if entity.bbox:
        brief["bbox"] = rnd_bbox(entity.bbox)

    return brief


def split_known_ids(model: CadModel, ids: list[str]) -> tuple[list[str], list[str]]:
    """Separa ids validos dos rejeitados, preservando a ordem e sem duplicar."""
    known: list[str] = []
    rejected: list[str] = []
    seen: set[str] = set()

    for raw in ids:
        entity_id = str(raw)
        if entity_id in seen:
            continue
        seen.add(entity_id)

        if entity_id in model.by_id:
            known.append(entity_id)
        else:
            rejected.append(entity_id)

    return known, rejected
