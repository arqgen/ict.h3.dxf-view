from typing import Union

from agno.agent import Agent
from agno.media import File
from agno.models.message import Message
from agno.team import Team

from src.api.models.chat import ChatRequest, ContinueRequest
from src.cad.model import CadModel


async def run_chat(
    agent: Union[Agent, Team],
    chat_content: ChatRequest,
    user_id: str,
    cad_model: CadModel,
):
    """Executa uma pergunta sobre o desenho.

    O indice vai em `dependencies` e nao em `session_state`: o agno so serializa
    `session_state` (que precisa ser JSON e e persistido na sessao), enquanto
    `dependencies` fica fora do prompt — `add_dependencies_to_context` e False
    por default. Assim as 12 tools recebem o objeto Python vivo sem que uma
    linha dele chegue ao modelo.
    """
    files = (
        [
            File(id=a.id, url=a.download_url, filename=a.file_name, name=a.file_name)
            for a in chat_content.attachments
        ]
        if chat_content.attachments
        else None
    )

    return agent.arun(
        input=[Message(role="user", content=chat_content.message, files=files)],
        session_id=chat_content.chat_id,
        user_id=user_id,
        dependencies={"cad": cad_model},
        stream=True,
        stream_events=True,
    )


async def continue_chat(
    agent: Union[Agent, Team],
    continue_content: ContinueRequest,
    user_id: str,
    cad_model: CadModel,
):
    """Retoma uma run pausada por tool de HITL."""
    run_id = continue_content.run_id
    session_id = continue_content.chat_id

    run_output = await agent.aget_run_output(
        run_id=run_id, session_id=session_id, user_id=user_id
    )
    if run_output is None or not run_output.requirements:
        raise ValueError(f"No paused run found for run_id={run_id}")

    for requirement in run_output.requirements:
        if requirement.needs_user_input:
            requirement.provide_user_input(continue_content.field_values)
        if requirement.needs_user_feedback:
            requirement.provide_user_feedback(continue_content.feedback_selections)

    return agent.acontinue_run(
        run_id=run_id,
        session_id=session_id,
        user_id=user_id,
        requirements=run_output.requirements,
        dependencies={"cad": cad_model},
        stream=True,
        stream_events=True,
    )
