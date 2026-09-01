# cad_viewer

Visualizador de desenhos DXF com um assistente de IA que responde perguntas sobre o desenho **e aponta de volta para ele**: destaca as entidades citadas, reenquadra a vista e isola layers.

A ideia central: a IA nunca vê o arquivo. Ela vê um resumo textual do desenho e o que 12 ferramentas devolvem quando consultam o índice geométrico. Isso é controle de alucinação, não economia de token — nenhuma quantidade, medida ou coordenada pode entrar numa resposta sem ter saído de uma ferramenta.

## Arquitetura

Monorepo com dois lados:

```
src/     backend Python — FastAPI + agno + ezdxf
web/     frontend — React + TypeScript + Vite, canvas 2D
```

O DXF é enviado ao backend, que o indexa com `ezdxf` e mantém o resultado em memória. Desse mesmo índice saem duas coisas: a geometria achatada que o canvas desenha e as respostas das ferramentas do agente. Uma única fonte de parse, portanto o id que a IA cita é o mesmo id que o canvas destaca.

```
browser: arquivo .dxf
   │  POST /api/documents
   ▼
server: ezdxf → Prim[] + índice (store em memória)
   ├── GET /prims ──────────────► canvas 2D desenha
   └── POST /api/chat ─► agno ─► 12 tools consultam o índice
                          │
                          └─ SSE ─► o frontend lê `ToolCallStarted.tool_args`
                                     e aplica destaque / zoom / isolar layer
```

As 4 ferramentas de interface (`highlight_entities`, `clear_highlight`, `zoom_to`, `set_layer_visibility`) não têm canal próprio: no servidor elas só validam e devolvem o que seria aplicado, e o efeito visual acontece porque o frontend observa os eventos do agno no stream.

### Camadas

| Camada | Onde | Responsabilidade |
| --- | --- | --- |
| Motor de informação | `src/cad/` | Lê o DXF, achata a geometria, mantém o índice. Não desenha e não sabe o que é IA. |
| HTTP | `src/api/` | Rotas, store em memória, SSE. Sem lógica de negócio. |
| IA | `src/ai_modules/` | Agente, ferramentas, prompt. Não importa nada de HTTP. |
| Render | `web/src/viewer/` | Desenha. Não sabe o que as entidades significam. |

A abstração que unifica tudo é `Prim`: cerca de 15 tipos de entidade DXF colapsam em três primitivas (`polyline`, `point`, `text`), então bbox, comprimento, área e hit-test derivam de um lugar só.

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

Abra `http://localhost:5173` e arraste um `.dxf`.

> A porta do backend aparece em dois lugares: `PORT` no `.env` e o proxy em `web/vite.config.ts` (que aceita `VITE_API_PORT`). O default dos dois é **8787** — se mudar um, mude o outro.

### Observabilidade (opcional)

Os traces do agente — cada chamada de LLM e cada tool de CAD, com entradas e
saídas — vão para um [Arize Phoenix](https://phoenix.arize.com/) local, que sobe
em Docker a partir deste repositório:

```bash
make phoenix-up      # collector + UI em http://localhost:6006
make phoenix-logs    # acompanha o container
make phoenix-down    # derruba (os traces ficam no volume phoenix_data)
```

Com o Phoenix no ar, `make dev` deve logar `observabilidade ativa — projeto
CAD_VIEWER em http://localhost:6006`. Abra `http://localhost:6006` e escolha o
projeto `CAD_VIEWER`.

Se a 6006 já estiver ocupada (outro Phoenix na máquina, por exemplo), suba em
outra porta e aponte o `.env` para ela:

```bash
make phoenix-up PHOENIX_PORT=6007     # e COLLECTOR_ENDPOINT="http://localhost:6007"
```

Para desligar, esvazie `COLLECTOR_ENDPOINT` no `.env` — o backend sobe igual, sem
erro e sem tracing.

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

| Variável | Default | Para que serve |
| --- | --- | --- |
| `LLM_PROVIDER` | `anthropic` | `anthropic` ou `openai` |
| `PROXY_AI_BASE_URL` | — | obrigatória; endpoint do gateway LiteLLM — sem ela o startup falha |
| `LITELLM_API_KEY` | — | credencial do gateway, usada para os dois providers |
| `ANTHROPIC_MODEL` | `claude-opus-5` | alias registrado no gateway |
| `ANTHROPIC_MAX_TOKENS` | `16000` | |
| `ANTHROPIC_EFFORT` | `medium` | `low`…`max`; o default da API é `high`, `medium` troca profundidade por latência de chat |
| `OPENAI_MODEL` | `gpt-4.1` | alias registrado no gateway, usado quando `LLM_PROVIDER=openai` |
| `MAX_UPLOAD_MB` | `64` | teto do arquivo enviado |
| `MAX_DOCUMENTS` | `8` | documentos simultâneos no store |
| `DOCUMENT_TTL_SECONDS` | `7200` | expiração de um documento ocioso |
| `COLLECTOR_ENDPOINT` | `http://localhost:6006` | URL base do Arize Phoenix (OTLP); **vazio desliga sem erro** |
| `COLLECTOR_PROJECT_NAME` | `CAD_VIEWER` | |

## Testes e lint

```bash
make test     # pytest — backend
make lint     # ruff check
make format   # ruff format + fixes

npm --prefix web test        # vitest — parser SSE e despacho das ferramentas de UI
npm --prefix web run typecheck
```

Para um DXF de teste em disco (útil para `curl` na API):

```bash
uv run python tests/make_sample.py   # → tests/fixtures/sample.dxf
```

O DXF sintético dos testes é gerado por `tests/make_sample.py` e as assertivas são **exatas** de propósito: o contorno é um retângulo 20 × 14, logo perímetro 68 e área 280, sem tolerância. Assertiva aproximada aqui já esteve escondendo perda silenciosa de geometria na implementação de referência.

`web/src/api/__tests__/recorded-stream.txt` é um stream SSE real capturado do agno. O teste roda contra ele — se o formato de evento do agno mudar, a suíte quebra em vez de o destaque silenciosamente parar de funcionar.

## Limites conhecidos

- **DXF ASCII apenas.** Sem DWG e sem DXF binário.
- **2D.** A coordenada Z é ignorada.
- **HATCH e LEADER** entram na contagem mas não têm geometria: não são medidos nem destacados.
- Comprimentos e áreas são aproximações sobre a geometria achatada; **área existe só para entidades fechadas**.
- O documento vive em memória. Reiniciar o servidor exige reenviar o arquivo.
- Sem autenticação e sem multiusuário — um usuário lógico (`local`).
- O texto é desenhado com fonte do sistema, não com as fontes SHX/TTF do CAD: as métricas diferem do AutoCAD.

## Documentação para agentes

- [`CLAUDE.md`](CLAUDE.md) — regras globais do projeto
- [`src/ai_modules/CLAUDE.md`](src/ai_modules/CLAUDE.md) — como adicionar agente, ferramenta, skill, time
- [`src/ai_modules/tools/CLAUDE.md`](src/ai_modules/tools/CLAUDE.md) — convenções das ferramentas
- [`commit-rules.md`](commit-rules.md) — commit, branch, push e PR
