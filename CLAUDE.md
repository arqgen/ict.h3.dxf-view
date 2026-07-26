# CLAUDE.md — GUIDELINES

Guia para agentes de IA que vão trabalhar neste projeto. Leia antes de criar ou modificar qualquer coisa.

## Antes de Começar

Antes de iniciar qualquer implementação, verifique a branch atual. Evite trabalhar em `main`, `staging` ou `develop`, crie uma nova branch seguindo as convenções em [commit-rules.md](commit-rules.md).

**Tasks pontuais** (uma implementação focada que termina em um ciclo): todo commit exige autorização. Mesmo que já tenha commitado várias vezes na mesma sessão, **nunca assuma que a autorização se repete**. Após cada implementação, rode as validações (lint, testes) e pergunte sobre o commit.

**Tasks longas e complexas** (múltiplas etapas com validações intermediárias): se necessário, comite as evoluções ao longo da implementação e, ao concluir tudo, pergunte sobre o push e o PR u siga as reras estipuladas para isso.

## Filosofia

**KISS — Keep It Simple, Stupid.** Toda decisão de código deve favorecer a solução mais simples que resolve o problema. Não adicione abstrações, configurabilidade ou generalização antecipada. Prefira nomes claros, estrutura óbvia e comentários onde a lógica não é autoevidente a soluções "inteligentes" que exigem decifração.

Regras práticas que derivam disso:

- Prefira **funções a classes** — só use classes quando houver estado real a manter
- Funções devem ser **sempre tipadas** (parâmetros e retorno)
- Use **early return** para evitar aninhamento desnecessário
- **Código mínimo que resolve o problema. Nada especulativo.**

**Toque só o que precisa. Limpe só a sua bagunça.** Esta é uma regra de escopo, não de estilo. Altere apenas o que é necessário para cumprir a tarefa. Não refatore código adjacente, não renomeie variáveis fora do problema, não faça "melhorias" oportunistas ("já que estou aqui", "esse nome está ruim", "esse trecho pode ser mais elegante" — não). Se você introduziu algo, você organiza. O resto fica como estava.

**Seja honesto — nunca invente.** Se não sabe, diga diretamente e aponte o que precisa verificar. Se está em dúvida, consulte a fonte (código, documentação, testes) antes de afirmar. Nunca entregue uma resposta plausível no lugar de uma correta.

**Não assuma — pergunte.** Se durante a implementação bater em um problema que não tem certeza de como resolver, pare e pergunte. Não adivinhe o caminho. Descreva o bloqueio, mostre as opções se houver, e deixe o time decidir.

**Tente antes de interromper — mas saiba a hora de parar.** Se uma tentativa falhar e a correção não exigir tocar em nada fora do escopo da tarefa, tente novamente. Até 2-3 tentativas são aceitáveis sem avisar. Depois disso, pare.

**Quando travar de verdade — pare e explique.** Interrompa imediatamente (sem esperar o limite de tentativas) se o bloqueio for externo à tarefa:

- precisa alterar arquivo ou módulo fora do escopo
- depende de algo fora do seu controle (config, variável de ambiente, serviço, permissão)
- exige uma decisão de design que impacta outras partes do sistema
- a tentativa quebrou código que já funcionava

Ao parar: descreva o bloqueio e sugira 1-2 opções de caminho. Sem histórico de tentativas — direto ao ponto. Deixe o time decidir. **Exceção:** ao iniciar uma tarefa, pergunte ao usuário se prefere ser notificado a cada bloqueio ou se quer que você tente resolver de forma autônoma até o fim — e siga a preferência declarada durante toda aquela sessão.

**Ao concluir uma implementação planejada — registre o resultado.** Escreva um resumo curto do que foi feito e se houve desvios do plano. Exemplo com desvio: "Previa reusar uma função existente, mas o contexto não tinha os dados necessários — criada uma função paralela para manter a mesma lógica sem acoplamento desnecessário."

## Como Manter Este Arquivo

Este `CLAUDE.md` é o índice global do projeto — contém só o que vale para **todo** o código. Regras técnicas de um módulo específico, exemplos de implementação, anatomia de rotas ou schemas ficam no `CLAUDE.md` interno daquela pasta. Não coloque aqui: exemplos de código, detalhes de implementação, padrões de um módulo específico. Se a informação só faz sentido dentro de `src/modules/users/`, ela pertence ao `src/modules/users/CLAUDE.md`.

**Estrutura de sub-CLAUDEs:**

```
CLAUDE.md                          ← este arquivo (regras globais)
src/
  modules/
    <modulo>/
      CLAUDE.md                    ← regras, padrões e exemplos do módulo
  <outra-camada>/
    CLAUDE.md                      ← se a camada tiver padrões próprios
```

Crie um sub-CLAUDE quando um módulo ou camada tiver padrões que desviam do global ou que precisam de exemplos para serem seguidos corretamente. Mantenha-o atualizado — um sub-CLAUDE desatualizado é pior que nenhum.

**Sub-CLAUDEs existentes:**

- [`src/ai_modules/CLAUDE.md`](src/ai_modules/CLAUDE.md) — agents, tools, skills, workflows, teams: padrões e como adicionar
- [`src/api/CLAUDE.md`](src/api/CLAUDE.md) — routers, models, SSE, config: padrões e como adicionar

**Arquivos auxiliares na raiz:**

Além dos sub-CLAUDEs por módulo, a raiz do projeto pode conter arquivos `.md` com regras pontuais e focadas (ex: `commit-rules.md`, `security.md`, `migration-guide.md`). Esses arquivos não substituem o `CLAUDE.md` global — complementam com detalhe que não cabe aqui. Liste-os na seção **Arquivos Auxiliares** abaixo da linha divisória e mantenha a lista atualizada.

**Regras deste arquivo:**

- Máximo de **200 linhas** — se ultrapassar, mova conteúdo para o sub-CLAUDE correto
- Regras de uma camada específica → `CLAUDE.md` daquela pasta; regras globais → seção **Regras Globais** ou **O que NÃO Fazer**, sem exemplo de código
- Nunca adicione blocos de código longos neste arquivo — inclua no sub-CLAUDE correto e coloque aqui apenas um link
- **Antes de planejar:** consulte o `CLAUDE.md` de cada módulo, service ou camada que será modificada — esses arquivos contêm regras e padrões específicos que o plano deve respeitar

---

## Arquivos Auxiliares

- [`commit-rules.md`](commit-rules.md) — regras de commit, branch, push e PR

## Ecossistema e Responsabilidades

Este serviço é o **core de IA** do ecossistema H3, composto por três repositórios:

| Serviço        | Repositório         | Responsabilidade                                          |
| -------------- | ------------------- | --------------------------------------------------------- |
| Frontend       | `llm.h3.frontend`   | Interface do usuário                                      |
| API de negócio | `llm.h3.api`        | CRUD, autenticação, gestão de usuários, regras de negócio |
| **AI API**     | **`llm.h3.ai-api`** | **Orquestração de agentes, sessões e respostas via LLM**  |

**Esta API não faz CRUD e não gerencia usuários.** Ela consome dados do banco principal (gerenciado pela `llm.h3.api`) e grava apenas nas coleções `agno_*` (sessões e memórias dos agentes). Tokens JWT são emitidos pela `llm.h3.api` — aqui só são validados.

Qualquer feature que envolva criar, alterar ou deletar entidades de negócio (usuários, planos, configurações) pertence à `llm.h3.api`, não aqui.

## Arquitetura em Uma Linha

FastAPI + Agno (LLM framework) + MongoDB (coleções `agno_*` para sessões e memórias) + Arize Phoenix (observability via OTLP); código em `src/api/` (routers, models, config) e `src/ai_modules/` (agents, teams, workflows).

**Módulos:** `agents`, `teams` (stub), `workflows` (stub)

## Mapa de Arquivos Críticos

- `src/main.py` — entry point (uvicorn + uvloop)
- `src/api/server.py` — FastAPI app, CORS, health check, registro de routers
- `src/api/core/config.py` — Pydantic Settings com lru_cache
- `src/api/core/auth.py` — dependency `get_current_user()` → `TokenData`
- `src/api/core/database.py` — dependency `get_mongo_db()` → `AsyncMongoDb | None`
- `src/api/core/rate_limiter.py` — dependency `get_rate_limiter()`, aplicado via `_auth` em `server.py`
- `src/api/models/chat.py` — schema `ChatRequest`
- `src/api/stream_response.py` — SSE / EventStreamResponse
- `src/ai_modules/llm_settings.py` — instanciação do modelo LLM (`get_model()`)
- `src/ai_modules/runner.py` — execução do chat (`run_chat()`)
- `src/ai_modules/agents/base.py` — defaults de plataforma comuns a todo `Agent` (`get_base_agent_kwargs()`)
- `src/ai_modules/agents/simple_agent/simple_agent.py` — fábrica de agente (`get_simple_agent()`)
- `src/api/observability.py` — inicialização do tracer Phoenix/OTLP (`init_observability()`)
- `src/integrations/repositories.py` — client e leitura do banco principal ("common-db"), gerenciado pela `llm.h3.api`

## Como Adicionar uma Feature

Para adicionar um novo agente, siga o contrato documentado em [`src/ai_modules/CLAUDE.md`](src/ai_modules/CLAUDE.md) (seção "Como Adicionar um Agent") e registre a rota conforme [`src/api/CLAUDE.md`](src/api/CLAUDE.md) (seção "Como Adicionar um Router").

## Como Rodar o Projeto

Ver `README.md` — comandos de instalação, execução local e Docker estão lá.

## Convenções de Nomenclatura

| Elemento          | Convenção                      | Exemplo                        |
| ----------------- | ------------------------------ | ------------------------------ |
| Arquivos          | snake_case                     | `simple_agent.py`, `chat.py`   |
| Classes/Types     | PascalCase                     | `ChatRequest`, `Settings`      |
| Funções/variáveis | snake_case                     | `get_simple_agent`, `run_chat` |
| Rotas HTTP        | kebab-case                     | `/api/agents/chat`             |
| Módulo de agente  | pasta + arquivo com mesmo nome | `simple_agent/simple_agent.py` |

## Commits, Branches e PRs

Consulte [commit-rules.md](commit-rules.md) para regras de commit, branch, push e PR.

## Regras Globais

### Auth e Autorização

JWT via `HTTPBearer` — tokens emitidos pela `llm.h3.api`. Dependency `get_current_user()` em `src/api/core/auth.py` valida o token e retorna `TokenData(user_id, role)`. Aplicada globalmente via `dependencies=_auth` em `server.py` — nunca validar JWT diretamente no router.

### Rate Limiting

`get_rate_limiter()` em `src/api/core/rate_limiter.py` limita requisições por usuário. Aplicado globalmente via `_auth` em `server.py`, junto com `get_current_user()`. Configurado via `RATE_LIMIT_REQUESTS` (default: 20 req) e `RATE_LIMIT_WINDOW_SECONDS` (default: 60s).

### Banco de Dados

MongoDB via `MONGO_URL`. Agno usa `db` no `Agent()` para persistência de sessão e memória nas coleções `agno_sessions` e `agno_memories`. Esta API não escreve em outras coleções — o banco principal é de responsabilidade da `llm.h3.api`. Leitura do banco principal ("common-db", via `COMMON_DB_MONGO_*`) é feita somente através de `src/integrations/repositories.py` (`find_documents`) — nunca instanciar outro client Mongo fora daí.

### Observabilidade

Arize Phoenix via OTLP. `init_observability()` é chamado no `lifespan` do FastAPI e instrumenta automaticamente todas as chamadas do Agno. Se `COLLECTOR_ENDPOINT` estiver vazio, a função retorna silenciosamente — sem crash. Em desenvolvimento local sem Docker, basta deixar `COLLECTOR_ENDPOINT` em branco no `.env`.

Variáveis relevantes: `COLLECTOR_ENDPOINT` (ex: `http://phoenix:6006`) e `COLLECTOR_PROJECT_NAME` (default: `H3_AI_API`).

### Tratamento de Erros

`stream_response.py` captura exceções e emite evento SSE com `type: "error"`. Validação Pydantic retorna 422 automaticamente.

### Logging

Importe sempre o logger de `src.api.logger`: `from src.api.logger import logger`. Nunca use `print()` nem instancie um novo logger via `logging.getLogger()` — o logger central já tem nível, formatação e handler configurados. Use o nível adequado: `logger.debug` para detalhes de execução, `logger.info` para eventos de lifecycle, `logger.warning` para situações degradadas mas não fatais, `logger.error` para falhas.

### Variáveis de Ambiente

Acesse sempre via `get_app_settings()` de `src.api.core.config`. Nunca use `os.environ` diretamente.

### Testes

pytest via `make test`. Cobrir routers e `runner.py`.

### Lint e Formatação

Ruff (`make lint` + `make format`). Line-length 88, rules E/F/I/B. Rodar antes de todo commit.

## Segurança

`JWT_SECRET` e `OPENAI_API_KEY` nunca commitar. CORS permissivo apenas em `dev`/`local` — produção deve restringir origens. `.env` está no `.gitignore`.

## O que NÃO Fazer

- **Não acesse env via `os.environ`** — use `get_app_settings()`
- **Não instancie modelos LLM fora de `llm_settings.py`**
- **Não chame `AgnoInstrumentor` ou `phoenix.otel.register` fora de `observability.py`**
- **Não coloque lógica de negócio nos routers** — use `runner.py` ou `services/`
- **Não use `print()` nem `logging.getLogger()` direto** — importe `logger` de `src.api.logger`
- **Não commite `.env`**
- **Não adicione co-autoria nos commits** — nunca inclua linhas `Co-Authored-By:` em nenhuma mensagem de commit
