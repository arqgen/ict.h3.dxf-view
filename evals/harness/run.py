"""Runs one benchmark variant with a real model, through the gateway.

    uv run python -m evals.harness.run --variant baseline --tasks L1 L2

Each case runs with a fresh history: the variant's policy, the protocol and the
view of the initial state go in the system message; the task goes in the user
message; the tools get the session state. The case ends when the model calls
`responder` or at the call limit. Each case becomes one JSON line in
`evals/results/harness/`, written as soon as it finishes.
"""

import argparse
import asyncio
import json
import math
import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from time import perf_counter
from typing import Any

from agno.models.message import Message

from evals.benchmark.controles import avaliar
from evals.benchmark.historico import ROOT
from evals.harness.formats import PROTOCOL, task_message
from evals.harness.session import Session, ViewTooLarge, tool_schemas
from evals.harness.variants import EDIT_GROUPS, VARIANTS, Variant, initial_versions
from src.ai_modules.llm_settings import get_model
from src.api.core.config import require_ai_gateway
from src.api.logger import logger

BENCHMARK = ROOT / "evals" / "benchmark"
RESULTS = ROOT / "evals" / "results" / "harness"
# L7 takes 17.5 calls on average in the baseline; the limit only stops loops.
CALL_LIMIT = 40
METRICS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens")
# The keys of `controles.avaliar` with this run's names.
SCORE_KEYS = {
    "acerto": "correct",
    "dano_colateral": "collateral_damage",
    "estado_esperado": "expected_state",
    "fora_do_roteiro": "off_script",
}


def load_cases(
    variant: Variant, tasks: list[str] | None, files: list[str] | None
) -> list[dict]:
    """The cases that apply to the variant, filtered by task and by file substring."""
    reading = json.loads((BENCHMARK / "casos.json").read_text())
    cases = [c for c in reading if c["status"] == "ok"]
    if variant.edits:
        cases += json.loads((BENCHMARK / "casos_edicao.json").read_text())
    if tasks:
        cases = [c for c in cases if c["tarefa"] in tasks]
    if files:
        cases = [c for c in cases if any(f in c["arquivo"] for f in files)]
    return cases


def json_equal(a: Any, b: Any) -> bool:
    """JSON equality: equivalent numbers are equal, booleans are not numbers."""
    if type(a) is bool or type(b) is bool:
        return a is b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(json_equal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(
            json_equal(x, y) for x, y in zip(a, b, strict=True)
        )
    return a == b


def score(case: dict, session: Session) -> dict[str, Any]:
    """Checks the answer's JSON, and uses the official evaluator on edits."""
    correct = session.answered and json_equal(session.answer, case["resposta_esperada"])
    if "historico" not in case:
        return {"correct": correct}
    out = avaliar(case, session.calls, session.answer)
    result = {SCORE_KEYS[k]: out[k] for k in SCORE_KEYS}
    result["correct"] = correct and result["correct"]
    return result


async def play(
    row: dict, session: Session, case: dict, variant: Variant, provider: str | None
) -> str:
    view = session.document()
    row["view_bytes"] = session.view_bytes
    groups = EDIT_GROUPS if "historico" in case else variant.read_groups
    schemas = tool_schemas(groups)
    tools = [{"type": "function", "function": schemas[k]} for k in sorted(schemas)]
    instructions = [
        variant.instructions,
        PROTOCOL,
        f"<documento_carregado>\n{view}\n</documento_carregado>",
    ]
    system = "- " + "\n- ".join(instructions)
    messages = [
        Message(role="system", content=system),
        Message(role="user", content=task_message(case)),
    ]
    model = await get_model(provider)
    row["model"] = model.id
    while True:
        row["n_requests"] += 1
        assistant = Message(role="assistant")
        reply = await model.ainvoke(messages, assistant, tools=tools)
        usage = reply.response_usage
        if usage is not None:
            for key in METRICS:
                row[key] += getattr(usage, key) or 0
            row["peak_input_tokens"] = max(row["peak_input_tokens"], usage.input_tokens)
        row["text"] = reply.content
        if not reply.tool_calls:
            return "no_answer"
        assistant.content = reply.content
        assistant.tool_calls = reply.tool_calls
        messages.append(assistant)
        batch = iter(reply.tool_calls)
        try:
            for call in batch:
                result = session.call(call["function"], schemas)
                if session.answered:
                    return "ok"
                if session.domain_attempts + session.answer_attempts >= CALL_LIMIT:
                    return "call_limit"
                messages.append(
                    Message(
                        role="tool",
                        tool_call_id=call["id"],
                        content=json.dumps(result, ensure_ascii=False),
                    )
                )
        finally:
            session.rejected_calls.extend(c["function"] for c in batch)


async def run_case(
    variant_name: str, case: dict, provider: str | None, max_bytes: int
) -> dict[str, Any]:
    variant = VARIANTS[variant_name]
    session = Session(initial_versions(case), variant.view, max_bytes)
    row = {
        "variant": variant_name,
        "task": case["tarefa"],
        "file": case["arquivo"],
        "n_requests": 0,
        "peak_input_tokens": 0,
        **dict.fromkeys(METRICS, 0),
    }
    start = perf_counter()
    try:
        status = await play(row, session, case, variant, provider)
    except ViewTooLarge as exc:
        status = "too_large"
        row["error"] = str(exc)
    except Exception as exc:
        status = "error"
        row["error"] = f"{type(exc).__name__}: {exc}"
    row.update(
        status=status,
        seconds=round(perf_counter() - start, 1),
        calls=session.calls,
        invalid_calls=session.invalid_calls,
        rejected_calls=session.rejected_calls,
        n_answer_attempts=session.answer_attempts,
        n_calls=session.domain_attempts,
        answer=session.answer,
        expected=case["resposta_esperada"],
    )
    row.setdefault("view_bytes", session.view_bytes)
    row["last_view_bytes"] = session.view_bytes
    return {**row, **score(case, session)}


def _mean(rows: list[dict], key: str) -> float:
    return math.fsum(row[key] for row in rows) / len(rows)


def summarize(rows: list[dict]) -> str:
    """Per task: cases, correct, damage, and mean calls and tokens of those that ran."""
    by_task: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_task[row["task"]].append(row)
    lines = [
        "task  cases  ran  answered  correct  damage  calls  tokens_in"
        "  cache_read  tokens_out"
    ]
    for task, group in sorted(by_task.items()):
        ran = [g for g in group if g.get("n_requests")]
        if not ran:
            lines.append(f"{task:<4}  {len(group):>5}  {0:>3}")
            continue
        answered = sum(g["status"] == "ok" for g in ran)
        correct = sum(g.get("correct", False) for g in ran)
        damage = sum(g.get("collateral_damage", False) for g in ran)
        lines.append(
            f"{task:<4}  {len(group):>5}  {len(ran):>3}  {answered:>8}"
            f"  {correct:>7}  {damage:>6}"
            f"  {_mean(ran, 'n_calls'):>5.1f}  {_mean(ran, 'input_tokens'):>9.0f}"
            f"  {_mean(ran, 'cache_read_tokens'):>10.0f}"
            f"  {_mean(ran, 'output_tokens'):>10.0f}"
        )
    lines.append(f"status: {dict(Counter(row['status'] for row in rows))}")
    return "\n".join(lines)


async def run(args: argparse.Namespace) -> None:
    cases = load_cases(VARIANTS[args.variant], args.tasks, args.files)
    cases = cases[: args.limit]
    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path = RESULTS / f"{stamp}-{args.variant}.jsonl"
    logger.info(f"{len(cases)} cases of variant {args.variant} -> {path}")
    # The code behind each number; `-dirty` flags changes outside the commit.
    commit = subprocess.run(
        ["git", "describe", "--always", "--dirty"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    semaphore = asyncio.Semaphore(args.concurrency)
    rows: list[dict] = []

    async def one(case: dict) -> None:
        async with semaphore:
            try:
                row = await run_case(
                    args.variant, case, args.provider, args.max_view_kb * 1024
                )
            except Exception as exc:
                logger.exception("Failed to prepare or score the case")
                row = {
                    "variant": args.variant,
                    "task": case["tarefa"],
                    "file": case["arquivo"],
                    "status": "error",
                    "error": f"{type(exc).__name__}: {exc}",
                }
        row["commit"] = commit
        rows.append(row)
        with path.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        logger.info(
            f"[{len(rows)}/{len(cases)}] {row['task']} {row['file']}: "
            f"{row['status']} correct={row.get('correct')}"
        )

    await asyncio.gather(*(one(c) for c in cases))
    logger.info("\n" + summarize(rows))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--variant", choices=sorted(VARIANTS), required=True)
    parser.add_argument("--tasks", nargs="*", help="e.g. L1 D1 G4")
    parser.add_argument("--files", nargs="*", help="substrings of the AQG path")
    parser.add_argument("--limit", type=int, help="at most N cases")
    parser.add_argument(
        "--max-view-kb",
        type=int,
        default=512,
        help="a larger view does not run (status too_large)",
    )
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--provider", help="anthropic or openai; default from .env")
    args = parser.parse_args()
    if (
        args.concurrency < 1
        or args.max_view_kb < 1
        or (args.limit is not None and args.limit < 0)
    ):
        parser.error(
            "concurrency and max-view-kb must be positive and limit non-negative"
        )
    require_ai_gateway()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
