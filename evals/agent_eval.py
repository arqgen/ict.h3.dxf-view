"""Eval do agente CAD contra o LLM real.

Mede se o agente acerta as perguntas de dominio e se todo numero da resposta
tem procedencia num resultado de tool, na pergunta ou no resumo do desenho.
Roda manualmente: precisa do gateway e de `data/aqg/`.

    uv run python -m evals.agent_eval [--all] [--files CAMINHO ...]
"""

import argparse
import asyncio
import json
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from agno.run.agent import RunContentEvent, ToolCallCompletedEvent

from src.ai_modules.agents.cad_agent import get_cad_agent
from src.ai_modules.runner import run_chat
from src.ai_modules.tools.cad_tools.helpers import split_known_ids
from src.ai_modules.tools.cad_tools.query_tools import ZONING_RULES
from src.api.logger import logger
from src.api.models.chat import ChatRequest
from src.cad.model import (
    CadModel,
    _category,
    describe_model,
    descriptor_groups,
    load_aqg,
    tower_units,
)

AQG_DIR = Path("data/aqg/avaliadas")
RESULTS_DIR = Path(__file__).parent / "results"

# Grupos `\d{1,3}(\.\d{3})+` sem virgula sao milhar (pt-BR); fora disso, ponto ou
# virgula seguidos de digitos sao separador decimal.
_NUMBER_RE = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?")
# Numeros como a maquina escreve (JSON dos resultados de tool): ponto decimal.
_PLAIN_RE = re.compile(r"\d+(?:\.\d+)?")

# (id, pergunta, valores esperados na resposta; None pula o caso)
Expected = Callable[[CadModel], list[float | None]]


def _indicator(
    model: CadModel, section: str, indicator_type: str, field: str = "value"
) -> float | None:
    for item in model.indicators[section]:
        if not isinstance(item, dict) or item.get("type") != indicator_type:
            continue
        value = item.get(field)
        if isinstance(value, int | float) and not isinstance(value, bool):
            return float(value)
    return None


def _outputs(*types: str) -> Expected:
    return lambda model: [_indicator(model, "outputs", t) for t in types]


def _zoning(model: CadModel) -> list[float | None]:
    return [
        value
        for _, projected, limit, field, _ in ZONING_RULES
        for value in (
            _indicator(model, "outputs", projected),
            _indicator(model, "inputs", limit, field),
        )
    ]


def _tower_units(model: CadModel) -> list[tuple[str, int]]:
    """(familia, unidades da torre) de cada torre com o dado."""
    result = []
    for inst in model.instances.values():
        units = tower_units(model.families[inst.family_index].properties)
        if _category(inst.family_type) == "torre" and units:
            result.append((inst.family, units[1]))
    return result


def _first_tower(model: CadModel) -> str | None:
    """Troca `{torre}` nas perguntas: a primeira torre em ordem de id."""
    return next(
        (i.id for i in model.instances.values() if _category(i.family_type) == "torre"),
        None,
    )


def _tower_height(model: CadModel) -> list[float | None]:
    tower = _first_tower(model)
    labels = [label for label, ids in descriptor_groups(model).items() if tower in ids]
    for item in model.indicators["outputs"]:
        if item.get("type") == "DescritivoTorre" and labels:
            if str(item.get("label")) == labels[0]:
                return [float(item["altura"])]
    return [None]


def _floors_program(model: CadModel) -> list[float | None]:
    limits = [
        float(item["value"])
        for item in model.indicators["archprog"]
        if item.get("type") in ("MinPavimentos", "MaxPavimentos")
    ]
    if not limits:
        return [None]
    return [_indicator(model, "outputs", "NumeroDePavimentos"), *limits]


def _units_per_tower(model: CadModel) -> list[float | None]:
    return sorted({float(units) for _, units in _tower_units(model)}) or [None]


def _units_per_family(model: CadModel) -> list[float | None]:
    by_family: dict[str, int] = {}
    for family, units in _tower_units(model):
        by_family[family] = by_family.get(family, 0) + units
    return [float(v) for v in by_family.values()] or [None]


CASES: list[tuple[str, str, Expected]] = [
    ("torres", "Quantas torres tem este projeto?", _outputs("TotalDeTorres")),
    (
        "unidades",
        "Quantas unidades habitacionais o projeto tem no total?",
        _outputs("TotalDeUnidades"),
    ),
    ("area", "Qual é a área total construída?", _outputs("AreaTotalConstruida")),
    (
        "ca",
        "Qual o CA projetado e qual o CA máximo permitido?",
        lambda m: [
            _indicator(m, "outputs", "CAProjetado"),
            _indicator(m, "inputs", "CAMaximoExigido"),
        ],
    ),
    (
        "vagas",
        "Quantas vagas de estacionamento foram projetadas?",
        _outputs("NumeroDeVagasProjetado"),
    ),
    ("destaque", "Destaque todas as torres no desenho.", lambda m: []),
    (
        "vinculo",
        "Qual das torres desenhadas é a torre 02 dos indicadores?",
        lambda m: [],
    ),
    (
        "zoneamento",
        "O projeto atende CA, TO, permeabilidade e gabarito?",
        _zoning,
    ),
    ("unidades_torre", "Quantas unidades tem cada torre?", _units_per_tower),
    (
        "unidades_familia",
        "Quantas unidades há em cada família de torre?",
        _units_per_family,
    ),
    (
        "terra",
        "Quanto de corte e aterro o projeto prevê?",
        lambda m: [
            _indicator(m, "outputs", "MovimentoDeTerra", "corte"),
            _indicator(m, "outputs", "MovimentoDeTerra", "aterro"),
        ],
    ),
    ("altura", "Qual a altura da torre {torre}?", _tower_height),
    (
        "cota",
        "Qual a maior cota marcada no terreno?",
        lambda m: [
            max((float(e.text) for e in m.entities if e.type == "cota"), default=None)
        ],
    ),
    (
        "programa",
        "O número de pavimentos está dentro do pedido no programa?",
        _floors_program,
    ),
    (
        "afastamento",
        "As torres respeitam o afastamento entre blocos?",
        lambda m: [_indicator(m, "outputs", "AfastamentoProjetado", "entre_blocos")],
    ),
    (
        "inclinacao",
        "Qual a inclinação média do terreno?",
        lambda m: [m.indicators["inclinacao_media"]],
    ),
]

# Casos em que acertar o numero nao basta: a tool tem de ter sido chamada.
REQUIRED_TOOL = {
    "zoneamento": "check_zoning",
    "afastamento": "check_setbacks",
    "programa": "compare_program",
}


def _parse(raw: str) -> tuple[float, int]:
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", raw):
        raw = raw.replace(".", "")
    raw = raw.replace(",", ".")
    decimals = len(raw.split(".")[1]) if "." in raw else 0
    return float(raw), decimals


def extract_numbers(text: str) -> list[tuple[float, int]]:
    """Numeros do texto, com as casas decimais escritas."""
    return [_parse(raw) for raw in _NUMBER_RE.findall(text)]


def is_sourced(value: float, decimals: int, sources: list[float]) -> bool:
    """Algum `s` arredondado nas casas do valor citado da o valor."""
    return any(round(s, decimals) == value for s in sources)


def unsourced(answer: str, tool_results: list[str], allowed_text: str) -> list[str]:
    """Numeros da resposta sem procedencia nas tools nem no texto permitido."""
    sources: list[float] = []
    for text in [*tool_results, allowed_text]:
        sources += [value for value, _ in extract_numbers(text)]
        sources += [float(raw) for raw in _PLAIN_RE.findall(text)]

    return [
        raw
        for raw in _NUMBER_RE.findall(answer)
        if not is_sourced(*_parse(raw), sources)
    ]


def _tower_parts(model: CadModel) -> set[str]:
    return {
        entity_id
        for instance in model.instances.values()
        if _category(instance.family_type) == "torre"
        for entity_id in instance.entity_ids
    }


def _covers(model: CadModel, tools: list[dict[str, Any]], needed: set[str]) -> bool:
    """Algum highlight cobre, expandindo ids de instancia, as partes pedidas."""
    for call in tools:
        if call["tool"] != "highlight_entities":
            continue
        ids = (call["args"] or {}).get("ids") or []
        known, _ = split_known_ids(model, [str(i) for i in ids])
        if needed <= set(known):
            return True
    return False


async def _ask(model: CadModel, question: str) -> tuple[str, list[dict[str, Any]]]:
    agent = await get_cad_agent(user_id="eval", model=model)
    request = ChatRequest(message=question, chat_id=uuid4().hex, document_id="eval")
    answer = ""
    tools: list[dict[str, Any]] = []

    async for event in await run_chat(agent, request, "eval", model):
        if isinstance(event, RunContentEvent) and isinstance(event.content, str):
            answer += event.content
        if isinstance(event, ToolCallCompletedEvent) and event.tool:
            tools.append(
                {
                    "tool": event.tool.tool_name,
                    "args": event.tool.tool_args,
                    "result": event.tool.result,
                }
            )
    return answer, tools


async def _run_case(
    model: CadModel, case_id: str, question: str, expected_of: Expected
) -> dict[str, Any]:
    question = question.replace("{torre}", _first_tower(model) or "")
    result: dict[str, Any] = {"caso": case_id, "pergunta": question}

    expected = expected_of(model)
    group_02 = descriptor_groups(model).get("02")
    if None in expected:
        return {**result, "status": "pulado", "motivo": "indicador ausente no arquivo"}
    if case_id == "destaque" and not _tower_parts(model):
        return {**result, "status": "pulado", "motivo": "nenhuma torre desenhada"}
    if case_id == "vinculo" and not group_02:
        return {**result, "status": "pulado", "motivo": "descritivo 02 sem grupo"}

    try:
        answer, tools = await _ask(model, question)
    except Exception as exc:
        logger.error(f"eval: caso {case_id} falhou: {exc}")
        return {**result, "status": "falha", "erro": str(exc)}

    allowed = question + "\n" + describe_model(model)
    missing = unsourced(answer, [str(t["result"]) for t in tools], allowed)
    numbers = extract_numbers(answer)
    hits = [
        any(is_sourced(value, decimals, [target]) for value, decimals in numbers)
        for target in expected
    ]
    result |= {
        "resposta": answer,
        "tools": tools,
        "esperado": expected,
        "numeros": [value for value, _ in numbers],
        "sem_procedencia": missing,
        "procedencia": not missing,
    }

    if case_id == "destaque":
        hit = _covers(model, tools, _tower_parts(model))
    elif case_id == "vinculo":
        parts = {e for i in group_02 or [] for e in model.instances[i].entity_ids}
        hit = _covers(model, tools, parts)
    else:
        hit = all(hits)
    if case_id in REQUIRED_TOOL:
        hit = hit and any(t["tool"] == REQUIRED_TOOL[case_id] for t in tools)
    result["acerto"] = hit
    return {**result, "status": "ok" if hit and not missing else "falha"}


async def run_eval(paths: list[Path]) -> list[dict[str, Any]]:
    report: list[dict[str, Any]] = []
    for path in paths:
        logger.info(f"eval: {path}")
        model = load_aqg(path.read_bytes(), path.name)
        for case_id, question, expected_of in CASES:
            case = await _run_case(model, case_id, question, expected_of)
            report.append({"arquivo": str(path), **case})
    return report


def _print_table(report: list[dict[str, Any]]) -> None:
    print(f"{'arquivo':<50} {'caso':<10} {'status':<8} sem procedencia")
    for row in report:
        missing = ", ".join(row.get("sem_procedencia", []))
        print(f"{row['arquivo']:<50} {row['caso']:<10} {row['status']:<8} {missing}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Eval do agente CAD (usa o LLM).")
    parser.add_argument(
        "--all", action="store_true", help="os 15 arquivos de avaliadas/"
    )
    parser.add_argument(
        "--files", nargs="+", type=Path, help="arquivos AQG especificos"
    )
    args = parser.parse_args()

    pattern = "*/*.json" if args.all else "*/otimo_*.json"
    paths = args.files or sorted(AQG_DIR.glob(pattern))
    if not paths:
        parser.error(f"nenhum AQG encontrado em {AQG_DIR}")

    report = asyncio.run(run_eval(paths))
    _print_table(report)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / f"{datetime.now():%Y%m%d-%H%M%S}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nresultado completo: {out}")


if __name__ == "__main__":
    main()
