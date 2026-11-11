"""Tools do benchmark entregues à RECOD: funções Python e o JSON Schema de cada uma.

Toda tool, exceto `calcular`, recebe `estado` (o caminho do AQG atual) como
primeiro argumento. Quem passa é o harness; o schema que vai ao modelo não o
inclui. Nada aqui importa o código de motor da Arqgen (VT, `buildings`, `maga`).

    from evals.benchmark.tools import GRUPOS, esquemas
    tools = GRUPOS["calculo"] | GRUPOS["edicao"]   # nome -> função
    schemas = esquemas(["calculo", "edicao"])      # o que vai ao modelo
"""

from collections.abc import Callable
from typing import Any

from agno.tools.function import Function

from . import calculo, edicao
from .linha_de_base import LINHA_DE_BASE

_CALCULO = [calculo.calcular, calculo.medir, calculo.relacao_espacial, calculo.caminho]
_EDICAO = [
    edicao.mover_torre,
    edicao.remover_torre,
    edicao.definir_pavimentos,
    edicao.alterar_programa,
    edicao.resolver_terraplenagem,
    edicao.trocar_familia,
    edicao.resolver_estacionamento,
    edicao.recalcular_indicadores,
    edicao.validar,
]

GRUPOS: dict[str, dict[str, Callable[..., dict]]] = {
    "calculo": {f.__name__: f for f in _CALCULO},
    "edicao": {f.__name__: f for f in _EDICAO},
    "linha_de_base": {nome: f for nome, (f, _) in LINHA_DE_BASE.items()},
}


def _esquema(f: Callable[..., dict]) -> dict[str, Any]:
    schema = Function.from_callable(f).to_dict()
    params = schema["parameters"]
    params["properties"].pop("estado", None)
    params["required"] = [p for p in params.get("required", []) if p != "estado"]
    return schema


def esquemas(grupos: list[str]) -> list[dict[str, Any]]:
    """Nome, descrição e parâmetros de cada tool dos grupos, sem `estado`.

    A linha de base (D10) só entra nas tarefas de leitura.
    """
    out = []
    for grupo in grupos:
        if grupo == "linha_de_base":
            for _, tool in LINHA_DE_BASE.values():
                tool.process_entrypoint()
                out.append(tool.to_dict())
            continue
        out.extend(_esquema(f) for f in GRUPOS[grupo].values())
    return out
