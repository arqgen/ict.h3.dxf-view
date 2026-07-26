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
| `runner.py`       | Gateway central de execução — `run_chat(agent, payload, user_id)` e `continue_chat(agent, payload, user_id)` (retoma run pausada) |
| `llm_settings.py` | Única fonte de instanciação do LLM — `get_model(provider, user_id)` |
| `agents/base.py`  | `get_base_agent_kwargs(db)` — defaults de plataforma comuns a todo `Agent` |

## Como Adicionar um Agent

1. Criar pasta `agents/<nome>/`
2. Criar `agents/<nome>/instructions.md` com o system prompt completo
3. Criar `agents/<nome>/<nome>.py` com a factory function
4. Exportar no `agents/__init__.py`

**Contrato obrigatório da factory:**

```python
async def get_<nome>_agent(user_id: str, db: AsyncMongoDb | None = None) -> Agent:
    model = get_model()
    instructions_path = Path(__file__).parent / "instructions.md"
    return Agent(
        **get_base_agent_kwargs(db),
        name="...",
        id="...",
        description="...",
        model=model,
        instructions=[instructions_path.read_text()],
    )
```

Regras:

- Sempre `async def`, sempre tipada
- `model` via `get_model()` — nunca instanciar `OpenAIChat` diretamente; `provider` default é `"openai"`, `user_id` é opcional para configurações futuras por usuário
- Sempre iniciar o `Agent(...)` com `**get_base_agent_kwargs(db)` (de `agents/base.py`) — cobre `db`, memória, histórico, cache de sessão e `debug_mode`/`debug_level`. Só sobrescreva uma dessas chaves na chamada se o agente precisar de comportamento diferente do default de plataforma
- `instructions` sempre carregadas do `instructions.md` da pasta do agent

`get_custom_settings(user_id)` em `llm_settings.py` é um stub (retorna `None`) — extension point para sobrescrever configurações de LLM por usuário, não implementado.

## Como Adicionar uma Tool

Ver [`tools/CLAUDE.md`](tools/CLAUDE.md) — regra de quando uma tool pertence a essa pasta (reutilizável entre agents) e como declará-la.

HITL (pausar a run para perguntar algo ao usuário) já tem tool pronta pra cada caso — `user_control_flow.py` (texto/campo tipado) e `user_feedback.py` (múltipla escolha/checklist/sim-não). Ver [`tools/CLAUDE.md`](tools/CLAUDE.md), seção "HITL", antes de criar qualquer tool nova para pedir input do usuário.

## Como Adicionar uma Skill

Skills são conhecimento carregado sob demanda (progressive disclosure): o agent vê só nome+descrição no system prompt e carrega o conteúdo via `get_skill_instructions` quando a tarefa pede. Skills **não** registram tools — as tools continuam declaradas no `Agent`.

1. Criar pasta `skills/<nome-com-hifens>/` com um `SKILL.md` dentro. O spec do agno exige: nome lowercase só com letras/dígitos/hífens e **igual ao nome da pasta** (exceção consciente à convenção snake_case), frontmatter com `name` e `description` obrigatórios. A `description` decide quando o agent carrega a skill — seja explícito sobre o gatilho.
2. Documentação detalhada consultável sob demanda vai em `skills/<nome>/references/*.md` (o agent acessa via `get_skill_reference`).
3. Nada a registrar: `get_skills()` em `skills/__init__.py` carrega todas as subpastas com `SKILL.md` automaticamente. Para um agent usar as skills, a factory sobrescreve a chave `"skills"` do dict de `get_base_agent_kwargs(db)` com `get_skills()` (ver `agents/simple_agent/simple_agent.py`).
4. No `instructions.md` do agent, deixe só um direcionamento curto ("carregue a skill X antes de...") — o conteúdo vive na skill.

Ex: `skills/layout-creation/` — fluxo de criação de layout, com `references/constraints.md` para o catálogo de constraints.

## Como Adicionar um Time

Mesma estrutura de `agents/` mas em `teams/`. Usar `Team` do agno em vez de `Agent`.

```python
async def get_<nome>_team(user_id: str, db: AsyncMongoDb | None = None) -> Team:
    ...
    return Team(members=[agent_a, agent_b], ...)
```

`runner.py` já aceita `Union[Agent, Team]` — o router passa `current_user.user_id` para `run_chat()`.

## Como Adicionar um Workflow

Criar `workflows/<nome>/<nome>.py` com classe que herda de `agno.workflow.Workflow`. Workflows são executados via router dedicado — não passam pelo `run_chat()` atual.

## Restrições

- Nunca instanciar LLM fora de `llm_settings.py`
- Nunca importar FastAPI, `Request` ou qualquer objeto HTTP aqui
- `runner.py` é o único ponto de execução — agents nunca se auto-executam
- Nunca usar `os.environ` — sempre `get_app_settings()`
- Nunca usar `print()` — importar `logger` de `src.api.logger`
