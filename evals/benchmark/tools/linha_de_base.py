"""As 16 tools deste repo como linha de base (D10), sem o `RunContext` do agno.

Mesma função, mesma descrição e mesmo schema que o agente deste repo usa; só o
documento vem de `estado` em vez do `RunContext`. Só nas tarefas de leitura.
"""

import json
from collections.abc import Callable
from typing import Any

from agno.tools.function import Function

from src.ai_modules.tools.cad_tools import CAD_TOOLS

from .calculo import _carregar, contexto


def _sem_contexto(tool: Function) -> Callable[..., dict]:
    def chamar(estado: str, *args: Any, **kwargs: Any) -> dict:
        model = _carregar(estado)
        if isinstance(model, dict):
            return model
        ctx = contexto(model)
        return json.loads(tool.entrypoint(ctx, *args, **kwargs))

    chamar.__name__ = tool.name
    return chamar


LINHA_DE_BASE = {tool.name: (_sem_contexto(tool), tool) for tool in CAD_TOOLS}
