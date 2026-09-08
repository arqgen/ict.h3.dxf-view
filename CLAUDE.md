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

Este `CLAUDE.md` é o índice global do projeto — contém só o que vale para **todo** o código. Regras técnicas de um módulo específico, exemplos de implementação, anatomia de rotas ou schemas ficam no `CLAUDE.md` interno daquela pasta (`<pasta>/CLAUDE.md`). Não coloque aqui exemplos de código, detalhes de implementação nem padrões de um módulo só.

Crie um sub-CLAUDE quando um módulo tiver padrões que desviam do global ou que precisam de exemplos para serem seguidos corretamente. Mantenha-o atualizado — um sub-CLAUDE desatualizado é pior que nenhum.

**Sub-CLAUDEs existentes:**

- [`src/cad/CLAUDE.md`](src/cad/CLAUDE.md) — motor de informação: primitivas, divisão de trabalho com o ezdxf, armadilhas
- [`src/ai_modules/CLAUDE.md`](src/ai_modules/CLAUDE.md) — agents, tools, skills, workflows, teams: padrões e como adicionar
- [`src/ai_modules/tools/CLAUDE.md`](src/ai_modules/tools/CLAUDE.md) — convenções das tools, incluindo as de CAD

**Arquivos auxiliares na raiz:**

A raiz pode conter arquivos `.md` com regras pontuais (ex: `commit-rules.md`). Eles complementam este arquivo com detalhe que não cabe aqui. Liste-os na seção **Arquivos Auxiliares** e mantenha a lista atualizada.

**Regras deste arquivo:**

- Máximo de **200 linhas** — se ultrapassar, mova conteúdo para o sub-CLAUDE correto
- Regras de uma camada específica → `CLAUDE.md` daquela pasta; regras globais → seção **Regras Globais** ou **O que NÃO Fazer**, sem exemplo de código
- Nunca adicione blocos de código longos neste arquivo — inclua no sub-CLAUDE correto e coloque aqui apenas um link
- **Antes de planejar:** consulte o `CLAUDE.md` de cada módulo, service ou camada que será modificada — esses arquivos contêm regras e padrões específicos que o plano deve respeitar

---

## Arquivos Auxiliares

- [`commit-rules.md`](commit-rules.md) — regras de commit, branch, push e PR

## O Que Este Projeto É

Monorepo de um visualizador DXF com assistente de IA. O usuário abre um desenho, vê o desenho renderizado, e conversa sobre ele — o assistente responde **e aponta de volta para o desenho** (destaca entidades, reenquadra, isola layer).

**A regra que define a arquitetura:** a IA nunca vê o arquivo. Ela vê um resumo textual e o que 12 tools devolvem ao consultar o índice geométrico. Toda quantidade, medida ou coordenada numa resposta veio de uma tool call — é controle de alucinação, não economia de token, e é o requisito de produto mais importante do projeto. Qualquer mudança que permita ao modelo afirmar um número sem passar por uma tool está errada, por mais conveniente que pareça.

Como o agente roda em Python, o índice roda em Python: não existe parse de DXF no browser.

## Arquitetura em Uma Linha

FastAPI + agno (agente e loop de tools) + ezdxf (parse e índice) no backend; React + Vite + canvas 2D no frontend (`web/`). Estado de documento em memória — sem banco, sem auth. Observabilidade opcional via Arize Phoenix/OTLP.

**Camadas:** `src/cad/` (motor de informação) · `src/api/` (HTTP) · `src/ai_modules/` (IA) · `web/src/viewer/` (render)

As 4 tools de interface não têm canal próprio: no servidor apenas validam, e o frontend aplica o efeito visual ao ver o evento `ToolCallStarted` no stream SSE. Se você mudar o formato do stream, quebra o destaque.

## Mapa de Arquivos Críticos

- `src/main.py` — entry point (uvicorn + uvloop)
- `src/cad/` — `geometry.py` (tipos `Prim` e medidas), `loader.py` (`load_dxf()`), `model.py` (`build_model()`, `describe_model()`, `prims_payload()`)
- `src/api/server.py` — FastAPI app, CORS, health check, registro de routers
- `src/api/core/config.py` — Pydantic Settings com lru_cache
- `src/api/store.py` — store de documentos em memória (`get_document_store()`)
- `src/api/stream_response.py` — SSE / `EventStreamResponse`
- `src/api/routers/` — `documents.py` (upload, prims, entidade) e `chat.py` (chat SSE)
- `src/api/observability.py` — tracer Phoenix/OTLP (`init_observability()`)
- `src/ai_modules/llm_settings.py` — instanciação do modelo LLM (`get_model()`)
- `src/ai_modules/runner.py` — execução do chat (`run_chat()`)
- `src/ai_modules/agents/base.py` — defaults comuns a todo `Agent`; `agents/cad_agent/` — a fábrica + `instructions.md`
- `src/ai_modules/tools/cad_tools/` — as 12 tools (8 de consulta, 4 de interface)
- `web/src/App.tsx` — dono de todo o estado do frontend e do seam `ToolUI`
- `web/src/api/client.ts` — parser SSE e despacho das tools de interface
- `web/src/viewer/CadCanvas.tsx` — render canvas 2D e hit-test

## Como Adicionar uma Feature

Agente novo: contrato em [`src/ai_modules/CLAUDE.md`](src/ai_modules/CLAUDE.md). Tool nova: [`src/ai_modules/tools/CLAUDE.md`](src/ai_modules/tools/CLAUDE.md).

**Tool que consulta o desenho:** declare `run_context: RunContext` como primeiro parâmetro e recupere o índice com `cad_model(run_context)` — o agno injeta esse parâmetro por nome e o remove do schema que vai ao modelo. Nunca use `session_state` (é serializado e persistido) nem `ToolResult.metadata` (é descartado e nunca chega a evento nenhum).

## Como Rodar o Projeto

Ver [`README.md`](README.md) — instalação, execução do backend e do frontend, portas e variáveis.

## Convenções de Nomenclatura

| Elemento              | Convenção                      | Exemplo                     |
| --------------------- | ------------------------------ | --------------------------- |
| Arquivos Python       | snake_case                     | `cad_agent.py`, `chat.py`   |
| Arquivos de componente| PascalCase                     | `CadCanvas.tsx`             |
| Classes/Types         | PascalCase                     | `ChatRequest`, `CadModel`   |
| Funções/variáveis     | snake_case (Py) / camelCase (TS) | `build_model`, `toolLabel` |
| Rotas HTTP            | kebab-case                     | `/api/documents`            |
| Módulo de agente      | pasta + arquivo com mesmo nome | `cad_agent/cad_agent.py`    |

Chaves dos resultados de tool e strings de interface são em **pt-BR** (`tipo`, `comprimento`, `area`) — o modelo repete essas chaves na resposta ao usuário. Identificadores de código permanecem em inglês.

## Commits, Branches e PRs

Consulte [commit-rules.md](commit-rules.md) para regras de commit, branch, push e PR.

## Regras Globais

### Auth e Estado

**Não há autenticação.** Um usuário lógico (`"local"`), sem JWT e sem rate limiting. Não adicione nenhum dos dois sem discutir — não existe emissor de token neste ecossistema.

**Não há banco.** O documento vive no store em memória de `src/api/store.py` (teto de itens + TTL) e as sessões do agno num `InMemoryDb` (`get_agent_db()` em `agents/base.py`). Somem juntas quando o processo cai, e isso é intencional. `store.py` é o único lugar que guarda estado de documento — não crie um segundo.

### Ferramentas e Geometria

Duas regras globais, detalhadas nos sub-CLAUDEs:

- **Uma tool nunca levanta exceção por dado inválido** — devolve o erro como dado. Ver [`src/ai_modules/tools/CLAUDE.md`](src/ai_modules/tools/CLAUDE.md).
- **Nunca reimplemente geometria que o `ezdxf` já faz**, e conheça as armadilhas que falham em silêncio. Ver [`src/cad/CLAUDE.md`](src/cad/CLAUDE.md).

### Observabilidade

Arize Phoenix via OTLP. `init_observability()` é chamado no `lifespan` e instrumenta as chamadas do agno; `shutdown_observability()` faz o flush dos spans após o `yield`. Se `COLLECTOR_ENDPOINT` estiver vazio, retorna silenciosamente — sem crash. O collector sobe pelo `docker-compose.yml` da raiz (`make phoenix-up`, UI em http://localhost:6006). Variáveis: `COLLECTOR_ENDPOINT` (URL base, sem `/v1/traces`) e `COLLECTOR_PROJECT_NAME`.

### Tratamento de Erros

`stream_response.py` captura exceções e emite um evento SSE `RunError`. Validação Pydantic retorna 422 automaticamente. Documento ausente ou expirado retorna 404 com instrução de reenviar o arquivo.

### Logging

`from src.api.logger import logger`. Nunca use `print()` nem `logging.getLogger()` — o logger central já tem nível, formatação e handler. `debug` para detalhes de execução, `info` para lifecycle, `warning` para degradado mas não fatal, `error` para falha.

### Variáveis de Ambiente

Acesse sempre via `get_app_settings()` de `src.api.core.config`. Nunca use `os.environ` diretamente.

### Testes

Backend: pytest via `make test`. Frontend: `npm --prefix web test`.

**Assertivas sobre geometria e contagem são exatas, sem tolerância.** O DXF sintético de `tests/make_sample.py` tem um contorno 20 × 14 justamente para que perímetro seja 68 e área 280 em ponto flutuante fechado. Trocar isso por `>= 60` transforma perda silenciosa de geometria num teste verde.

O teste do frontend roda contra `web/src/api/__tests__/recorded-stream.txt`, um stream SSE real gravado do agno: se o formato de evento mudar, a suíte quebra em vez de o destaque parar de funcionar em silêncio.

### Lint e Formatação

Ruff (`make lint` + `make format`). Line-length 88, rules E/F/I/B. Rodar antes de todo commit. No frontend, `npm --prefix web run typecheck`.

## Segurança

`LITELLM_API_KEY` nunca commitar — `.env` está no `.gitignore`. Todo tráfego de LLM passa pelo gateway (`PROXY_AI_BASE_URL`); não há mais caminho direto para `api.anthropic.com`/`api.openai.com`. CORS permissivo apenas em `local`/`dev`; produção deve restringir origens.

O arquivo DXF é enviado ao servidor (diferente da implementação de referência, que o mantinha no browser). Se o conteúdo dos desenhos for sensível, isso é uma mudança de postura a considerar antes de expor a aplicação.

## O que NÃO Fazer

- **Não deixe o modelo afirmar número que não veio de tool** — é o requisito central do produto
- **Não acesse env via `os.environ`** — use `get_app_settings()`
- **Não instancie modelos LLM fora de `llm_settings.py`**
- **Não chame `AgnoInstrumentor` ou `phoenix.otel.register` fora de `observability.py`**
- **Não coloque lógica de negócio nos routers** — use `runner.py` ou `src/cad/`
- **Não parseie DXF no frontend** — há uma única fonte de parse, no Python
- **Não levante exceção numa tool por dado inválido** — devolva o erro como dado
- **Não crie um segundo canal para ações de interface** — o stream de eventos do agno já é o canal
- **Não use `print()` nem `logging.getLogger()` direto** — importe `logger` de `src.api.logger`
- **Não commite `.env`**
- **Não adicione co-autoria nos commits** — nunca inclua linhas `Co-Authored-By:` em nenhuma mensagem de commit
