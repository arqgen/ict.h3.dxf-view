"""SSE sobre o stream de eventos do agno.

Nao ha reempacotamento: os eventos do agno vao ao browser como sao, porque o
frontend depende de campos deles. Em particular, e observando
`ToolCallStarted.tool.tool_args` que o viewer aplica as acoes de UI que a IA
pediu (destacar, dar zoom, isolar layer) — verificado em
`agno/run/agent.py:416` e `agno/models/response.py:28`.
"""

import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import Request
from fastapi.responses import StreamingResponse

from src.api.logger import logger

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    # Sem isto um proxy nginx bufferiza a resposta e o streaming deixa de
    # existir sem nenhum erro visivel.
    "X-Accel-Buffering": "no",
}


def _frame(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


async def event_stream(
    events: AsyncIterator[Any], request: Request
) -> AsyncIterator[str]:
    """Encaminha os eventos do agno como frames SSE.

    Aborta quando o cliente desconecta. Checamos `request.is_disconnected()` a
    cada evento em vez de confiar no cancelamento da task: sem essa checagem uma
    aba fechada no meio de uma resposta longa deixaria o agente rodando (e
    gastando tokens) ate o fim.
    """
    try:
        async for event in events:
            if await request.is_disconnected():
                logger.info("cliente desconectou — interrompendo a run")
                break

            yield _frame(event.to_dict())
    except Exception as exc:
        logger.exception("erro durante o streaming da run")
        yield _frame({"event": "RunError", "error": str(exc)})


def EventStreamResponse(  # noqa: N802 — nome de fabrica, imita um construtor
    events: AsyncIterator[Any], request: Request
) -> StreamingResponse:
    return StreamingResponse(
        event_stream(events, request),
        media_type="text/event-stream; charset=utf-8",
        headers=SSE_HEADERS,
    )
