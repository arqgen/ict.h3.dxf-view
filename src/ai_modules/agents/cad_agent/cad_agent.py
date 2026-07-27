from pathlib import Path

from agno.agent import Agent
from agno.db.base import BaseDb

from src.ai_modules.agents.base import get_base_agent_kwargs
from src.ai_modules.llm_settings import get_model
from src.ai_modules.tools import CAD_TOOLS
from src.cad.model import CadModel, describe_model

# Teto de rodadas de tool por resposta. A implementacao de referencia usa 14 e
# nenhuma pergunta legitima chegou perto disso — o limite existe para conter
# loop, nao para restringir o trabalho.
MAX_TOOL_ROUNDS = 14

_INSTRUCTIONS_PATH = Path(__file__).parent / "instructions.md"


async def get_cad_agent(
    user_id: str,
    model: CadModel,
    db: BaseDb | None = None,
) -> Agent:
    """Cria o agente que responde sobre o desenho carregado.

    O resumo do desenho entra nas instrucoes num bloco delimitado. Isso e
    deliberado: fora das tools, esse texto e a unica visao que o modelo tem do
    arquivo, e delimita-lo deixa claro para o modelo onde termina a politica e
    comeca o dado.
    """
    base = get_base_agent_kwargs(db)
    base["tool_call_limit"] = MAX_TOOL_ROUNDS

    document_block = (
        "<documento_carregado>\n" + describe_model(model) + "\n</documento_carregado>"
    )

    return Agent(
        **base,
        name="Assistente CAD",
        id="cad-agent",
        description="Especialista em leitura de desenhos tecnicos DXF",
        model=await get_model(user_id=user_id),
        instructions=[_INSTRUCTIONS_PATH.read_text(encoding="utf-8"), document_block],
        tools=CAD_TOOLS,
    )
