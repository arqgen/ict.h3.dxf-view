# CLAUDE.md — `src/ai_modules/tools/`

## Regra

Toda tool que **não** for específica de um único agent — ou seja, que pode ser reaproveitada por outros agents/teams — deve ser declarada aqui, não dentro da pasta do agent. Se um comportamento só faz sentido para um agent específico e não deve ser reutilizado, ele não pertence a esta pasta.

## Tools existentes

| Arquivo                | Exporta                                                                            | Papel                                                                                           |
| ---------------------- | ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `test_tool_call.py`    | `test_tool_call`                                                                   | Tool de função simples, para testar tool calling                                                |
| `web_search.py`        | `web_search`                                                                       | `DuckDuckGoTools` pré-configurado                                                               |
| `web_scrape.py`        | `web_scrape`                                                                       | `TrafilaturaTools` pré-configurado                                                              |
| `fetch_pdf.py`         | `fetch_pdf`                                                                        | Baixa um PDF de uma URL e o retorna como `ToolResult(files=[File(...)])` — o modelo lê o PDF nativamente (requer `send_media_to_model=True`, default em `agents/base.py`) |
| `user_control_flow.py` | `user_control_flow`                                                                | `UserControlFlowTools` — pausa a run para pedir input livre/tipado do usuário (`get_user_input`) |
| `user_feedback.py`     | `user_feedback`                                                                    | `UserFeedbackTools` — pausa a run para apresentar uma pergunta estruturada com opções (`ask_user`, single ou multi-select) |
| `layout_solver/`       | `generate_solutions`, `list_families`, `list_sites`, `list_zones`, `select_site`, `select_zone`, `set_program` | Fluxo de posicionamento de mobiliário em plantas                                                |

## Como Adicionar uma Tool

1. Criar `tools/<nome>.py`:
   - Tool de função: decorar com `@tool` (agno) — docstring completa (o que faz, quando usar, `Args`/`Returns`), já que o agent lê essa docstring para decidir quando chamar. Ex: `test_tool_call.py`.
   - Toolkit pré-configurado do agno (ex: `DuckDuckGoTools`, `TrafilaturaTools`, `UserControlFlowTools`): instanciar no módulo e exportar a instância como variável de módulo (não dentro de função) — ex: `web_search`, `web_scrape`, `user_control_flow`.
2. Exportar em `tools/__init__.py` (import + `__all__`).
3. Importar do pacote `src.ai_modules.tools` e passar no parâmetro `tools=[...]` da factory do(s) agent(s) que a usam.

**Agrupando por assunto:** quando várias tools pertencerem ao mesmo assunto/fluxo (múltiplas tools que operam sobre o mesmo domínio, como catálogo, estado e geração de soluções de um solver), não as espalhe soltas em `tools/`. Agrupe-as em uma subpasta `tools/<assunto>/` com um `__init__.py` exportando as tools públicas, e um arquivo por responsabilidade dentro dela. Ex: `tools/layout_solver/` (`catalog.py`, `selection.py`, `state.py`, `program.py`, `solutions.py`), que exporta `generate_solutions`, `list_families`, `list_sites`, `list_zones`, `select_site`, `select_zone`, `set_program` via `tools/layout_solver/__init__.py` — reexportado depois em `tools/__init__.py` como qualquer outra tool.

**Listagem via wrapper:** quando uma tool de seleção/definição aceita um parâmetro que, se vazio, apenas lista as opções disponíveis em vez de selecionar/definir algo (ex: `select_site("")` lista os sites, `select_zone("")` lista as zonas), não deixe esse comportamento exposto só na docstring — depender do LLM inferir que deve passar `""` é frágil. Crie uma tool `@tool` explícita `list_<algo>` que apenas chama a tool original com o parâmetro vazio, dando ao agent um nome de tool autoexplicativo. Ex: `list_sites`/`list_zones` em `tools/layout_solver/selection.py`, wrappers de `select_site`/`select_zone`.

**Toolkits com parâmetro `instructions`** (ex: `UserControlFlowTools`, `UserFeedbackTools`): prefira configurar o comportamento pela própria tool (`instructions=...`, `add_instructions=True`) em vez de duplicar a mesma orientação no `instructions.md` do agent — evita as duas fontes divergirem.

**HITL — qual tool usar para qual tipo de pergunta:** `get_user_input` (`user_control_flow.py`) para texto livre ou campo tipado; `ask_user` (`user_feedback.py`) para múltipla escolha ou checklist (via `multi_select`), incluindo sim/não como uma pergunta de 2 opções. Não crie uma tool custom para isso — as duas já cobrem os casos de pausa/pergunta ao usuário nativamente no agno. Ambas emitem `RunPausedEvent`, mapeado para o evento SSE `user_input` em `src/api/stream_response.py` (ver [`src/api/CLAUDE.md`](../../api/CLAUDE.md), seção "Como Adicionar um Continue").

## Restrições

- Nunca importar FastAPI, `Request` ou qualquer objeto HTTP aqui (herda a restrição de `src/ai_modules/CLAUDE.md`)
- Nunca instanciar LLM aqui — isso é responsabilidade de `llm_settings.py`
