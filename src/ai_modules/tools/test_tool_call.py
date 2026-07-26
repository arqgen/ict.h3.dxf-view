from agno.tools import tool

from src.api.logger import logger


@tool
def test_tool_call(message: str) -> str:
    """Use esta tool sempre que o usuário pedir para testar a chamada de tool
    (tool calling), sem ambiguidade com nenhuma outra tool.

    Recebe uma mensagem em texto e devolve um eco dela, confirmando que a
    tool foi executada e que o resultado voltou para o agent.

    Args:
        message: Texto enviado pelo usuário para o teste.

    Returns:
        str: Confirmação de execução contendo a mensagem recebida.
    """
    logger.debug(f"test_tool_call executada com message={message!r}")
    return f"Tool de teste executada com sucesso. Mensagem recebida: {message}"
