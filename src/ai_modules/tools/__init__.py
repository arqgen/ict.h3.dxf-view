"""Tools reutilizaveis entre agents.

So `cad_tools` e reexportado aqui. Os outros modulos desta pasta vieram do
template da plataforma e dependem de pacotes que este projeto nao instala
(`trafilatura`, `duckduckgo-search`); reexporta-los faria qualquer import de
`src.ai_modules.tools` falhar. Quem precisar deles importa o modulo direto e
adiciona a dependencia.
"""

from .cad_tools import CAD_TOOLS, QUERY_TOOLS, UI_TOOL_NAMES, UI_TOOLS

__all__ = ["CAD_TOOLS", "QUERY_TOOLS", "UI_TOOLS", "UI_TOOL_NAMES"]
