# CLAUDE.md — `src/ai_modules/tools/`

## Regra

Toda tool que **não** for específica de um único agent — ou seja, que pode ser reaproveitada por outros agents/teams — deve ser declarada aqui, não dentro da pasta do agent. Se um comportamento só faz sentido para um agent específico e não deve ser reutilizado, ele não pertence a esta pasta.

## Tools existentes

| Arquivo / pasta        | Exporta        | Papel                                                                 |
| ---------------------- | -------------- | --------------------------------------------------------------------- |
| `cad_tools/`           | `CAD_TOOLS`    | As 12 tools do desenho — 8 de consulta e 4 de interface. Ver abaixo.  |
| `test_tool_call.py`    | `test_tool_call` | Tool de função simples, para testar tool calling                    |
| `fetch_pdf.py`         | `fetch_pdf`    | Baixa um PDF de uma URL e o devolve como `ToolResult(files=[File(...)])` |
| `user_control_flow.py` | `user_control_flow` | `UserControlFlowTools` — pausa a run para pedir input livre/tipado |
| `user_feedback.py`     | `user_feedback` | `UserFeedbackTools` — pausa a run com pergunta de múltipla escolha  |
| `web_search.py`        | `web_search`   | `DuckDuckGoTools` pré-configurado                                     |
| `web_scrape.py`        | `web_scrape`   | `TrafilaturaTools` pré-configurado                                    |

**Só `cad_tools` é reexportado em `tools/__init__.py`.** Os outros módulos vieram do template da plataforma e alguns dependem de pacotes que este projeto não instala (`trafilatura`, `duckduckgo-search`) — reexportá-los faria qualquer `import src.ai_modules.tools` estourar `ImportError`. Para usar um deles, importe o módulo direto e acrescente a dependência ao `pyproject.toml`.

## As Tools de CAD

`cad_tools/` tem três arquivos: `helpers.py` (acesso ao índice, serialização, utilitários), `query_tools.py` (as 8 de consulta) e `ui_tools.py` (as 4 de interface).

### Acesso ao índice

```python
@tool
def minha_tool(run_context: RunContext, algum_filtro: str | None = None) -> str:
    try:
        model = cad_model(run_context)
    except MissingDocument as exc:
        return fail(str(exc))
    ...
    return dump({"contagens": ...}, "frase curta pro chat")
```

O agno injeta `run_context` **por nome** e o remove do schema JSON que vai ao modelo — há teste garantindo isso (`test_run_context_is_hidden_from_the_model_schema`). Nunca use `session_state` para o índice (é serializado e persistido) nem `ToolResult.metadata` (é descartado e nunca chega a evento nenhum).

### Contrato de resultado

Toda tool devolve uma string JSON via `dump(payload, resumo)`:

- **Chaves em pt-BR** (`tipo`, `comprimento`, `area`, `texto`, `bloco`, `contagens`, `destacadas`), números arredondados em 3 casas. O modelo repete essas chaves na resposta ao usuário.
- **`resumo`** é uma frase curta em pt-BR para a linha do tempo do chat, não para o modelo — o frontend a lê do evento `ToolCallCompleted`. Toda tool tem de ter um; há teste verificando.

### Dado inválido volta como dado

**Uma tool nunca levanta exceção por dado ruim.** Id inexistente, bloco que não existe, bbox malformado, layer desconhecido: tudo volta como `erro`, `rejeitados`, `desconhecidos` ou `indisponiveis`, junto com o que *deu* para fazer e, quando útil, a lista de opções válidas.

O motivo é prático: exceção encerra a rodada de tools e o modelo perde a chance de se corrigir. Devolvendo `{"erro": "layer 'PAREDE' não existe", "layers_disponiveis": [...]}` ele acerta na tentativa seguinte.

### Descrições prescritivas

As docstrings são o que o modelo lê para decidir quando chamar a tool, e elas são deliberadamente imperativas: `"AÇÃO DE INTERFACE: ..."`, `"PREFIRA ESTA TOOL para qualquer pergunta do tipo 'quantos'"`, `"Use SEMPRE que citar entidades específicas"`. Isso muda a taxa de ativação de forma mensurável. Ao editar uma docstring, não a torne meramente descritiva.

### As 4 tools de interface

`highlight_entities`, `clear_highlight`, `zoom_to`, `set_layer_visibility`.

No servidor elas **apenas validam e devolvem o que seria aplicado** — não existe estado de UI no backend. O efeito visual acontece porque o frontend observa o evento `ToolCallStarted` no stream SSE e lê `tool.tool_args` (`web/src/api/client.ts`).

Consequências:

- Não invente um canal paralelo (`CustomEvent`, campo extra no payload) para ação de interface. Um caminho de dados só. `CustomEvent` foi avaliado e descartado: seu `__init__` custom quebra `to_dict()` e o `repr` do evento acaba concatenado no resultado que o modelo lê.
- Ao renomear uma dessas tools ou mudar seus parâmetros, atualize **junto**: `UI_TOOL_NAMES` em `ui_tools.py` e `UI_TOOLS` + `applyUiTool` em `web/src/api/client.ts`.

## Como Adicionar uma Tool

1. Criar `tools/<nome>.py`:
   - Tool de função: decorar com `@tool` (agno) — docstring completa (o que faz, quando usar, `Args`/`Returns`), já que o agent lê essa docstring para decidir quando chamar.
   - Toolkit pré-configurado do agno: instanciar no módulo e exportar a instância como variável de módulo (não dentro de função).
2. Exportar em `tools/__init__.py` (import + `__all__`), desde que o módulo importe sem dependência ausente.
3. Importar do pacote `src.ai_modules.tools` e passar no parâmetro `tools=[...]` da factory do(s) agent(s) que a usam.

**Agrupando por assunto:** quando várias tools pertencerem ao mesmo domínio, não as espalhe soltas em `tools/`. Agrupe numa subpasta `tools/<assunto>/` com um `__init__.py` exportando as tools públicas e um arquivo por responsabilidade — como `tools/cad_tools/`.

**Listagem via wrapper:** quando uma tool de seleção aceita um parâmetro que, se vazio, apenas lista as opções disponíveis, não deixe esse comportamento só na docstring — depender do LLM inferir que deve passar `""` é frágil. Crie uma tool `@tool` explícita `list_<algo>`.

**Toolkits com parâmetro `instructions`** (ex: `UserControlFlowTools`, `UserFeedbackTools`): prefira configurar pela própria tool (`instructions=...`, `add_instructions=True`) em vez de duplicar a orientação no `instructions.md` do agent — evita as duas fontes divergirem.

**HITL — qual tool usar:** `get_user_input` (`user_control_flow.py`) para texto livre ou campo tipado; `ask_user` (`user_feedback.py`) para múltipla escolha ou checklist (via `multi_select`), incluindo sim/não como pergunta de 2 opções. Não crie tool custom para isso. Ambas emitem `RunPausedEvent` — o frontend atual **não trata** esse evento, então usar HITL exige tratá-lo em `web/src/api/client.ts` e uma rota de continue usando `continue_chat()`.

## Restrições

- Nunca importar FastAPI, `Request` ou qualquer objeto HTTP aqui (herda a restrição de [`../CLAUDE.md`](../CLAUDE.md))
- Nunca instanciar LLM aqui — isso é responsabilidade de `llm_settings.py`
- Nunca levantar exceção por dado inválido — devolva o erro como dado
