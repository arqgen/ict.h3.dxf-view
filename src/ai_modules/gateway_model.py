"""O `OpenAIChat` do gateway, imune às tool calls fantasma do agno.

Ao juntar um stream, o agno indexa as tool calls pela posição (`index`) que o
provider manda e preenche os buracos com `{}`
(`agno/models/openai/chat.py::parse_tool_calls`); no fim, carimba um uuid em toda
entrada que ficou sem `id`
(`agno/models/base.py::_populate_assistant_message_from_stream_data`). Sobra na
mensagem do assistente um `{"id": "<uuid>"}` sozinho — sem `function`, sem nome e
sem execução correspondente em `tools[]`.

Não é inofensivo. A entrada é persistida na sessão e volta ao modelo tanto no
resto do próprio turno (junto do resultado da tool) quanto em todo turno
seguinte, e o gateway recusa a request inteira:

    tool call not supported: {'id': 'call_00000000000000000000000000000000000'}

O `call_...` é o mesmo fantasma: `reformat_tool_call_ids` renomeia todo id que
não começa com `call_` antes de enviar. A partir daí a conversa não anda mais.

Por isso são duas defesas: `parse_tool_calls` impede que o fantasma seja gravado
daqui para frente, e `_format_all_messages` o tira das sessões que já foram
gravadas com ele — sem elas, uma conversa envenenada continuaria morta.
"""

from dataclasses import dataclass
from typing import Any

from agno.models.message import Message
from agno.models.openai import OpenAIChat

from src.api.logger import logger


def _is_phantom(tool_call: dict[str, Any]) -> bool:
    """Tool call sem `function.name` — não é chamável, exibível nem enviável."""
    return not (tool_call.get("function") or {}).get("name")


def _without_phantoms(messages: list[Message]) -> list[Message]:
    """Cópia das mensagens sem as tool calls fantasma."""
    cleaned: list[Message] = []
    for message in messages:
        phantoms = [tc for tc in (message.tool_calls or []) if _is_phantom(tc)]
        if not phantoms:
            cleaned.append(message)
            continue

        logger.warning(
            f"{len(phantoms)} tool call(s) fantasma removida(s) do histórico "
            f"enviado ao modelo: {phantoms}"
        )
        real = [tc for tc in message.tool_calls or [] if not _is_phantom(tc)]

        # Mensagem que só tinha fantasma e não tem texto não carrega nada — e
        # assistant vazio é o próximo 400 esperando para acontecer.
        if not real and not message.content:
            continue

        copy = message.model_copy(deep=True)
        copy.tool_calls = real or None
        cleaned.append(copy)
    return cleaned


@dataclass
class GatewayChat(OpenAIChat):
    """`OpenAIChat` apontado ao gateway, sem as tool calls fantasma do agno."""

    @staticmethod
    def parse_tool_calls(tool_calls_data: list[Any]) -> list[dict[str, Any]]:
        """Descarta os buracos que o agno preenche com `{}` ao juntar os deltas."""
        parsed = OpenAIChat.parse_tool_calls(tool_calls_data)
        return [tc for tc in parsed if not _is_phantom(tc)]

    def _format_all_messages(
        self, messages: list[Message], compress_tool_results: bool = False
    ) -> list[dict[str, Any]]:
        return super()._format_all_messages(
            _without_phantoms(messages), compress_tool_results
        )
