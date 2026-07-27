from typing import Any

from pydantic import BaseModel, Field


class Attachment(BaseModel):
    id: str
    file_name: str
    download_url: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    chat_id: str
    # O DXF nao viaja no chat: ele foi indexado em POST /api/documents e as tools
    # o alcancam por este id.
    document_id: str
    attachments: list[Attachment] | None = None


class ContinueRequest(BaseModel):
    """Retoma uma run pausada por tool de HITL."""

    run_id: str
    chat_id: str
    document_id: str
    field_values: dict[str, Any] | None = None
    feedback_selections: dict[str, Any] | None = None
