# cad_viewer

Visualizador de projetos AQG (o JSON de *Project* exportado pela Arqgen) com um assistente de IA que responde perguntas sobre o projeto — torres, vagas, tipologias, índices urbanísticos — **e aponta de volta para o desenho**: destaca as entidades citadas, reenquadra a vista e isola layers.

A ideia central: a IA nunca vê o arquivo. Ela vê um resumo textual do projeto e o que 12 ferramentas devolvem quando consultam o índice geométrico. Isso é controle de alucinação, não economia de token — nenhuma quantidade, medida ou coordenada pode entrar numa resposta sem ter saído de uma ferramenta.

## Arquitetura

Monorepo com dois lados:

```
src/     backend Python — FastAPI + agno + parser AQG próprio
web/     frontend — React + TypeScript + Vite, canvas 2D
```

O AQG é enviado ao backend, que o indexa em `src/cad/` e mantém o resultado em memória. Desse mesmo índice saem duas coisas: a geometria achatada que o canvas desenha e as respostas das ferramentas do agente. Uma única fonte de parse, portanto o id que a IA cita é o mesmo id que o canvas destaca.

```
browser: arquivo .json (AQG)
   │  POST /api/documents
   ▼
server: load_aqg → Prim[] + índice (store em memória)
   ├── GET /api/documents/{id}/prims ──► canvas 2D desenha
   └── POST /api/chat ─► agno ─► 12 tools consultam o índice
                          │
                          └─ SSE ─► o frontend lê `ToolCallStarted.tool_args`
                                     e aplica destaque / zoom / isolar layer
```

As 4 ferramentas de interface (`highlight_entities`, `clear_highlight`, `zoom_to`, `set_layer_visibility`) não têm canal próprio: no servidor elas só validam e devolvem o que seria aplicado, e o efeito visual acontece porque o frontend observa os eventos do agno no stream.

### Camadas

| Camada | Onde | Responsabilidade |
| --- | --- | --- |
| Motor de informação | `src/cad/` | Lê o AQG, achata a geometria, mantém o índice. Não desenha e não sabe o que é IA. |
| HTTP | `src/api/` | Rotas, store em memória, SSE. Sem lógica de negócio. |
| IA | `src/ai_modules/` | Agente, ferramentas, prompt. Não importa nada de HTTP. |
| Render | `web/src/viewer/` | Desenha. Não sabe o que as entidades significam. |

A abstração que unifica tudo é `Prim`: toda geometria GeoJSON do AQG colapsa em três primitivas (`polyline`, `point`, `text`), então bbox, comprimento, área e hit-test derivam de um lugar só.

### Endpoints

| Rota | Para que serve |
| --- | --- |
| `POST /api/documents` | envia o `.json` (AQG), indexa e devolve o `document_id` |
| `GET /api/documents/{id}` | metadados e resumo textual do documento |
| `GET /api/documents/{id}/prims` | geometria achatada que o canvas desenha |
| `GET /api/documents/{id}/entities/{entity_id}` | detalhe de uma entidade |
| `POST /api/chat` | conversa com o agente (resposta SSE) |
| `GET /health` | status, ambiente, provider e se o gateway está configurado |

## Rodando

Requisitos: Python ≥ 3.11 com [uv](https://docs.astral.sh/uv/), Node ≥ 20.

```bash
make install                 # uv sync + npm install em web/
cp .env.example .env         # e preencha PROXY_AI_BASE_URL/LITELLM_API_KEY
```

Dois terminais:

```bash
make dev        # backend  → http://localhost:8787
make dev-web    # frontend → http://localhost:5173
```

Abra `http://localhost:5173` e arraste um `.json` de `data/aqg/` (ver [`data/aqg/README.md`](data/aqg/README.md)).

Uma conversa útil para começar: "quantas torres e quantas unidades?", "destaque as torres", "isole o layer pav_tipo".

> A porta do backend aparece em dois lugares: `PORT` no `.env` e o proxy em `web/vite.config.ts` (que aceita `VITE_API_PORT`). O default dos dois é **8787** — se mudar um, mude o outro.

### Observabilidade (opcional)

Os traces do agente — cada chamada de LLM e cada tool de CAD, com entradas e
saídas — vão para um [Arize Phoenix](https://phoenix.arize.com/) local, que sobe
em Docker a partir deste repositório.

**Antes de subir, confira de quem é a 6006.** É a porta default do Phoenix, então
é comum já haver um de outro projeto ocupando ela:

```bash
docker ps --filter publish=6006 --format '{{.Names}}\t{{.Ports}}'
```

Se algo responder e não for o `cad_viewer_phoenix`, use outra porta — ver abaixo.
Ignorar esse passo não gera erro nenhum: `make phoenix-up` falha ao bindar, o
backend continua enviando para a 6006 e **os seus traces vão parar no Phoenix do
outro projeto**, com o log dizendo `observabilidade ativa` normalmente.

Com a porta livre:

```bash
make phoenix-up      # collector + UI em http://localhost:6006
make phoenix-logs    # acompanha o container
make phoenix-down    # derruba (os traces ficam no volume phoenix_data)
```

`make dev` deve logar `observabilidade ativa — projeto CAD_VIEWER em
http://localhost:6006`. Abra `http://localhost:6006` e escolha o projeto
`CAD_VIEWER`.

Em outra porta, `PHOENIX_PORT` vale para o `up` e para o `down` — os dois falam
com o mesmo `docker compose`:

```bash
make phoenix-up PHOENIX_PORT=6007     # e COLLECTOR_ENDPOINT="http://localhost:6007"
make phoenix-down PHOENIX_PORT=6007
```

`COLLECTOR_ENDPOINT` é a **URL base**, sem caminho: o `/v1/traces` é anexado pelo
backend em `src/api/observability.py`.

Para desligar, esvazie `COLLECTOR_ENDPOINT` no `.env` — o backend sobe igual, sem
erro e sem tracing.

## Notebooks (`experiments/`)

Notebooks de EDA e exploração ficam em `experiments/` — ver [`experiments/README.md`](experiments/README.md) para o propósito de cada um. Como os notebooks utilizam pacotes que não fazem parte do backend da aplicação, ficam num dependency-group separado:

```bash
# Instala os pacotes do grupo
uv sync --group notebooks
# Registra o kernel
uv run python -m ipykernel install --user \
  --name cad-viewer --display-name "cad-viewer (.venv)"
```

Abra o `.ipynb` e selecione o kernel `cad-viewer (.venv)`.

## Rodando em portas alternativas

Para demonstrar este projeto ao lado de outro (evitando conflito de porta),
tanto `make dev` quanto `make dev-web` aceitam override por variável, sem
precisar editar `.env` nem `vite.config.ts`:

```bash
make dev PORT=8788
make dev-web VITE_PORT=5174 VITE_API_PORT=8788
```

Abra `http://localhost:5174`. Sem argumentos, os dois comandos continuam
usando os defaults 8787/5173.

## Configuração

Tudo via `.env`, acessado somente por `get_app_settings()` em `src/api/core/config.py`.

A coluna **Default** é o default do código — o que vale quando não há `.env`.
Onde o `.env.example` traz outro valor, está anotado.

| Variável | Default | Para que serve |
| --- | --- | --- |
| `ENVIRONMENT` | `local` | `local` \| `dev` \| `prod`; fora de `local`/`dev` o CORS deixa de ser permissivo |
| `HOST` | `0.0.0.0` | interface do uvicorn |
| `PORT` | `8787` | porta do backend — pareada com `VITE_API_PORT` no frontend |
| `LLM_PROVIDER` | `anthropic` | `anthropic` ou `openai` |
| `PROXY_AI_BASE_URL` | — | **obrigatória**; endpoint do gateway LiteLLM — sem ela o startup falha |
| `LITELLM_API_KEY` | — | **obrigatória**; credencial do gateway, usada para os dois providers — sem ela o startup falha |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | alias registrado no gateway |
| `ANTHROPIC_MAX_TOKENS` | `16000` | |
| `ANTHROPIC_EFFORT` | `medium` | `low`…`max`; o default da API é `high`, `medium` troca profundidade por latência de chat |
| `OPENAI_MODEL` | `gpt-5.5` | alias registrado no gateway, usado quando `LLM_PROVIDER=openai` |
| `MAX_UPLOAD_MB` | `64` | teto do arquivo enviado |
| `MAX_DOCUMENTS` | `8` | documentos simultâneos no store |
| `DOCUMENT_TTL_SECONDS` | `7200` | expiração de um documento ocioso |
| `COLLECTOR_ENDPOINT` | `""` (desligado) | URL base do Arize Phoenix (OTLP); o `.env.example` já vem com `http://localhost:6006` |
| `COLLECTOR_PROJECT_NAME` | `CAD_VIEWER` | |

## Testes e lint

```bash
make test     # pytest — backend
make lint     # ruff check
make format   # ruff format + fixes

npm --prefix web test        # vitest — parser SSE e despacho das ferramentas de UI
npm --prefix web run typecheck

make build-web               # build de produção do frontend → web/dist
```

O AQG sintético dos testes é gerado por `tests/make_aqg_sample.py` e as assertivas são **exatas** de propósito: o terreno é um retângulo 100 × 80 (área 8000) e o talude tem um furo, com área 20 × 14 − 2 × 2 = 276, sem tolerância. Assertiva aproximada aqui já esteve escondendo perda silenciosa de geometria na implementação de referência.

`tests/test_corpus.py` roda o parser nos AQGs reais de `data/aqg/` — a pasta não é versionada, e o teste pula quando ela não existe.

### Eval do agente

```bash
make eval     # 5 projetos × 7 perguntas contra o LLM real
```

Mede se o agente acerta as perguntas de domínio (torres, unidades, área construída, CA, vagas, destaque) e se **todo número da resposta tem procedência numa tool**. Usa o gateway (tem custo) e `data/aqg/`; o resultado completo vai para `evals/results/`. `uv run python -m evals.agent_eval --all` roda os 15 de `avaliadas/`.

`web/src/api/__tests__/recorded-stream.txt` é um stream SSE real capturado do agno. O teste roda contra ele — se o formato de evento do agno mudar, a suíte quebra em vez de o destaque silenciosamente parar de funcionar.

## Limites conhecidos

- **2D, um pavimento.** A planta mostra o pavimento-tipo das torres; unidades, vagas e áreas construídas vêm dos indicadores do arquivo. A coordenada Z é ignorada.
- **Fora do índice:** topografia em mesh (`CadMesh`), anotações (`solution.annotations`), `archprog` e blocos externos de `families[].blocks`.
- **Os `DescritivoTorre` não são ligados às torres desenhadas** — a regra que os associa não é conhecida.
- **Área existe só para polígonos**, já descontados os furos.
- O documento vive em memória. Reiniciar o servidor exige reenviar o arquivo.
- Sem autenticação e sem multiusuário — um usuário lógico (`local`).

## Documentação para agentes

- [`CLAUDE.md`](CLAUDE.md) — regras globais do projeto
- [`src/cad/CLAUDE.md`](src/cad/CLAUDE.md) — motor de informação: parser AQG, primitivas, regras do formato, armadilhas
- [`src/ai_modules/CLAUDE.md`](src/ai_modules/CLAUDE.md) — como adicionar agente, ferramenta, skill, time
- [`src/ai_modules/tools/CLAUDE.md`](src/ai_modules/tools/CLAUDE.md) — convenções das ferramentas
- [`commit-rules.md`](commit-rules.md) — commit, branch, push e PR
- [`PRD.md`](PRD.md) e [`IMPLEMENTATION.md`](IMPLEMENTATION.md) — requisitos e plano da migração DXF → AQG
