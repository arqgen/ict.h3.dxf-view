# CLAUDE.md — `src/ai_modules/`

Toda lógica de IA vive aqui. Nenhum import de FastAPI, Request ou objetos HTTP deve entrar neste módulo.

## Mapa de Subdiretórios

| Dir / Arquivo     | Papel                                                               |
| ----------------- | ------------------------------------------------------------------- |
| `agents/`         | Factories de `Agent` (agno) — uma pasta por agent                   |
| `teams/`          | Factories de `Team` (agno) — uma pasta por time                     |
| `tools/`          | Funções `@tool` e instâncias de toolkits reutilizáveis entre agents — ver [`tools/CLAUDE.md`](tools/CLAUDE.md) |
| `skills/`         | Skills agno (Agent Skills spec) — pastas com `SKILL.md`, carregadas via `get_skills()` |
| `workflows/`      | Fluxos multi-step usando agno `Workflow`                            |
| `prompts/`        | Prompt templates compartilhados                                     |
| `runner.py`       | Gateway central de execução — `run_chat(agent, payload, user_id, cad_model)` e `continue_chat(...)` (retoma run pausada) |
| `llm_settings.py` | Única fonte de instanciação do LLM — `get_model(provider, user_id)` |
| `agents/base.py`  | `get_base_agent_kwargs(db)` e `get_agent_db()` — defaults comuns a todo `Agent` |

## O Índice CAD nas Tools

`run_chat()` passa o `CadModel` em `dependencies={"cad": ...}`. Toda tool que precise do desenho declara `run_context: RunContext` como primeiro parâmetro e chama `cad_model(run_context)`.

Por que `dependencies` e não `session_state`: `add_dependencies_to_context` é `False` por default no agno, então o objeto Python nunca é serializado no prompt nem persistido na sessão. `session_state` é persistido e precisa ser JSON. E `ToolResult.metadata` não serve para nada disso — é descartado pelo agno e nunca chega a evento nenhum.

## Como Adicionar um Agent

1. Criar pasta `agents/<nome>/`
2. Criar `agents/<nome>/instructions.md` com o system prompt completo
3. Criar `agents/<nome>/<nome>.py` com a factory function
4. Exportar no `agents/__init__.py`

**Contrato obrigatório da factory:**

```python
async def get_<nome>_agent(user_id: str, db: BaseDb | None = None) -> Agent:
    instructions_path = Path(__file__).parent / "instructions.md"
    return Agent(
        **get_base_agent_kwargs(db),
        name="...",
        id="...",
        description="...",
        model=await get_model(user_id=user_id),
        instructions=[instructions_path.read_text(encoding="utf-8")],
    )
```

Regras:

- Sempre `async def`, sempre tipada
- `model` via `await get_model()` — nunca instanciar `Claude` ou `OpenAIChat` diretamente. O provider vem de `LLM_PROVIDER` no `.env` (`anthropic` default, `openai` suportado)
- Sempre iniciar o `Agent(...)` com `**get_base_agent_kwargs(db)` (de `agents/base.py`) — cobre `db`, histórico, cache de sessão e `debug_mode`/`debug_level`. Só sobrescreva uma dessas chaves se o agente precisar de comportamento diferente do default
- `instructions` sempre carregadas do `instructions.md` da pasta do agent

Sem `db` explícito, `get_base_agent_kwargs` usa o `InMemoryDb` de `get_agent_db()`. É o que dá histórico multi-turno sem banco externo — sem `db` o agente não lembraria da pergunta anterior.

**Exemplo real:** `agents/cad_agent/`. Ele acrescenta duas coisas ao contrato: `tool_call_limit=14` e o resumo do desenho (`describe_model(model)`) como segundo item de `instructions`, dentro de um bloco `<documento_carregado>`. Esse resumo é a única visão que o modelo tem do desenho fora das tools.

## Como Adicionar uma Tool

Ver [`tools/CLAUDE.md`](tools/CLAUDE.md) — regra de quando uma tool pertence a essa pasta (reutilizável entre agents) e como declará-la.

HITL (pausar a run para perguntar algo ao usuário) já tem tool pronta pra cada caso — `user_control_flow.py` (texto/campo tipado) e `user_feedback.py` (múltipla escolha/checklist/sim-não). Ver [`tools/CLAUDE.md`](tools/CLAUDE.md), seção "HITL", antes de criar qualquer tool nova para pedir input do usuário.

## Como Adicionar uma Skill

Skills são conhecimento carregado sob demanda (progressive disclosure): o agent vê só nome+descrição no system prompt e carrega o conteúdo via `get_skill_instructions` quando a tarefa pede. Skills **não** registram tools — as tools continuam declaradas no `Agent`.

1. Criar pasta `skills/<nome-com-hifens>/` com um `SKILL.md` dentro. O spec do agno exige: nome lowercase só com letras/dígitos/hífens e **igual ao nome da pasta** (exceção consciente à convenção snake_case), frontmatter com `name` e `description` obrigatórios. A `description` decide quando o agent carrega a skill — seja explícito sobre o gatilho.
2. Documentação detalhada consultável sob demanda vai em `skills/<nome>/references/*.md` (o agent acessa via `get_skill_reference`).
3. Nada a registrar: `get_skills()` em `skills/__init__.py` carrega todas as subpastas com `SKILL.md` automaticamente. Para um agent usar as skills, a factory passa `skills=get_skills()` no `Agent(...)`.
4. No `instructions.md` do agent, deixe só um direcionamento curto ("carregue a skill X antes de...") — o conteúdo vive na skill.

**Não há skill neste projeto hoje** — `get_skills()` carregaria zero skills, e por isso nenhum agente passa `skills=`. A pasta existe como ponto de extensão.

## Como Adicionar um Time

Mesma estrutura de `agents/` mas em `teams/`. Usar `Team` do agno em vez de `Agent`.

```python
async def get_<nome>_team(user_id: str, db: BaseDb | None = None) -> Team:
    ...
    return Team(members=[agent_a, agent_b], ...)
```

`runner.py` já aceita `Union[Agent, Team]`.

## Como Adicionar um Workflow

Criar `workflows/<nome>/<nome>.py` com classe que herda de `agno.workflow.Workflow`. Workflows são executados via router dedicado — não passam pelo `run_chat()` atual.

## Restrições

- Nunca instanciar LLM fora de `llm_settings.py`
- Nunca importar FastAPI, `Request` ou qualquer objeto HTTP aqui
- `runner.py` é o único ponto de execução — agents nunca se auto-executam
- Nunca usar `os.environ` — sempre `get_app_settings()`
- Nunca usar `print()` — importar `logger` de `src.api.logger`
- Nunca deixar o modelo afirmar número que não veio de tool — ver a regra central no [`CLAUDE.md`](../../CLAUDE.md) da raiz
