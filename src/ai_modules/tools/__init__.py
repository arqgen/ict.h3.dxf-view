"""Tools reutilizaveis entre agents.

So `cad_tools` e reexportado aqui. Os outros modulos desta pasta vieram do
template da plataforma e nenhum agente os usa. O `web_scrape` depende do
`trafilatura`, que este projeto nao instala; reexporta-lo faria qualquer import
de `src.ai_modules.tools` falhar. Quem precisar deles importa o modulo direto e
adiciona a dependencia.
"""

from .cad_tools import CAD_TOOLS, QUERY_TOOLS, UI_TOOL_NAMES, UI_TOOLS

__all__ = ["CAD_TOOLS", "QUERY_TOOLS", "UI_TOOLS", "UI_TOOL_NAMES"]
