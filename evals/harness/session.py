"""Sequential tool execution and the observed state of a single case.

What the model reads (schema descriptions, errors returned to it) stays in pt-BR,
like the benchmark's tools.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from jsonschema import Draft202012Validator

from evals.benchmark.controles import executar
from evals.benchmark.tools import GRUPOS, esquemas

Call = dict[str, Any]
View = Callable[[str], str]
HISTORY = "history"

ANSWER_SCHEMA = {
    "name": "responder",
    "description": "Entrega a resposta final da tarefa e encerra a rodada.",
    "parameters": {
        "type": "object",
        "properties": {
            "valor_json": {
                "type": "string",
                "description": "a resposta, em JSON, no formato pedido na tarefa",
            }
        },
        "required": ["valor_json"],
    },
}


def _history_schema(name: str, description: str, indices: list[str]) -> dict:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "required": indices,
            "properties": {key: {"type": "integer"} for key in indices},
        },
    }


# The names are the ones in the benchmark's `chamadas_esperadas`.
HISTORY_SCHEMAS = [
    _history_schema("desfazer", "Volta o projeto n versões.", ["n"]),
    _history_schema(
        "diff_versoes",
        "O que mudou da versão mae à filha (0 é a base).",
        ["mae", "filha"],
    ),
]


def tool_schemas(groups: list[str]) -> dict[str, dict]:
    """The schemas of the groups (plus `history`, from this harness) and `responder`."""
    schemas = esquemas([g for g in groups if g != HISTORY])
    if HISTORY in groups:
        schemas += HISTORY_SCHEMAS
    return {s["name"]: s for s in [*schemas, ANSWER_SCHEMA]}


class ViewTooLarge(Exception):
    pass


def _non_json(value: str) -> None:
    raise ValueError(f"número inválido em JSON: {value}")


@dataclass
class Session:
    versions: list[str]
    view: View
    max_bytes: int
    calls: list[Call] = field(default_factory=list)
    invalid_calls: list[Call] = field(default_factory=list)
    rejected_calls: list[Call] = field(default_factory=list)
    domain_attempts: int = 0
    answer_attempts: int = 0
    view_bytes: int = 0
    answer: Any = None
    answered: bool = False

    def document(self) -> str:
        view = self.view(self.versions[-1])
        self.view_bytes = len(view.encode())
        if self.view_bytes > self.max_bytes:
            raise ViewTooLarge(
                f"view of {self.view_bytes} bytes exceeds {self.max_bytes}"
            )
        return view

    def call(self, function: dict, schemas: dict[str, dict]) -> dict:
        name = function["name"]
        raw = function["arguments"]
        args = raw
        if name == "responder":
            self.answer_attempts += 1
        else:
            self.domain_attempts += 1
        try:
            # A tool without parameters may arrive with empty `arguments`.
            args = json.loads(raw or "{}", parse_constant=_non_json)
            if name not in schemas:
                raise ValueError("tool indisponível para este caso")
            params = schemas[name]["parameters"]
            validator = Draft202012Validator({**params, "additionalProperties": False})
            error = next(validator.iter_errors(args), None)
            if error:
                raise ValueError(error.message)
            if name == "diff_versoes" and not all(
                0 <= i < len(self.versions) for i in args.values()
            ):
                raise ValueError("versão inexistente")
            if name == "responder":
                self.answer = json.loads(args["valor_json"], parse_constant=_non_json)
                self.answered = True
                return {}
        except (TypeError, ValueError) as exc:
            self.invalid_calls.append({"tool": name, "args": args, "error": str(exc)})
            return {"erro": str(exc)}

        # JSON Schema accepts 2.0 where the index is an integer.
        if name in ("desfazer", "diff_versoes"):
            args = {k: int(v) for k, v in args.items()}
        previous_count = len(self.versions)
        call = {"tool": name, "args": args}
        self.versions, (result,) = executar({"historico": self.versions}, [call])
        self.calls.append(call)
        if name in GRUPOS["edicao"]:
            result = {"resposta": result}
        if len(self.versions) != previous_count:
            if name == "desfazer":
                result = {}
            result.update(versao=len(self.versions) - 1, documento=self.document())
        return result
