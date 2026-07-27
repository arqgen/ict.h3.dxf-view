from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from src.ai_modules.agents import get_cad_agent
from src.ai_modules.runner import run_chat
from src.api.models.chat import ChatRequest
from src.api.store import DocumentStore, get_document_store
from src.api.stream_response import EventStreamResponse

router = APIRouter(prefix="/api", tags=["chat"])

StoreDep = Annotated[DocumentStore, Depends(get_document_store)]

# Sem autenticacao nesta aplicacao: a sessao do agno e identificada pelo
# `chat_id` que o frontend gera. Um unico usuario logico.
DEFAULT_USER_ID = "local"


@router.post("/chat")
async def chat(
    payload: ChatRequest, request: Request, store: StoreDep
) -> StreamingResponse:
    """Responde uma pergunta sobre o desenho, em streaming SSE.

    Nao ha loop agentico aqui — o agno e o loop. Esta rota so resolve o
    documento, monta o agente e encaminha os eventos.
    """
    model = store.get(payload.document_id)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="documento nao encontrado ou expirado — envie o arquivo novamente",
        )

    agent = await get_cad_agent(user_id=DEFAULT_USER_ID, model=model)
    events = await run_chat(agent, payload, DEFAULT_USER_ID, model)

    return EventStreamResponse(events, request)
