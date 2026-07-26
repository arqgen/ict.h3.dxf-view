from typing import Union

from agno.agent import Agent
from agno.media import File
from agno.models.message import Message
from agno.team import Team

from src.api.models.chat import ChatRequest, ContinueRequest


async def run_chat(agent: Union[Agent, Team], chat_content: ChatRequest, user_id: str):
    message_content = chat_content.message
    session_id = chat_content.chat_id
    files = (
        [
            File(id=a.id, url=a.download_url, filename=a.file_name, name=a.file_name)
            for a in chat_content.attachments
        ]
        if chat_content.attachments
        else None
    )

    return agent.arun(
        input=[Message(role="user", content=message_content, files=files)],
        session_id=session_id,
        user_id=user_id,
        stream=True,
        stream_events=True,
    )


async def continue_chat(
    agent: Union[Agent, Team], continue_content: ContinueRequest, user_id: str
):
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
        stream=True,
        stream_events=True,
    )
