# cad_viewer

Visualizador de desenhos DXF com um assistente de IA que responde perguntas sobre o desenho e aponta de volta para ele: destaca as entidades citadas, reenquadra a vista e isola layers.

A IA nunca vê o arquivo. Ela vê um resumo textual do desenho e o que 12 ferramentas devolvem ao consultar o índice geométrico, então nenhuma quantidade, medida ou coordenada entra numa resposta sem ter saído de uma ferramenta.

## Arquitetura

```
browser: arquivo .dxf
   │  POST /api/documents
   ▼
server: ezdxf → Prim[] + índice (store em memória)
   ├── GET /api/documents/{id}/prims ──► canvas 2D desenha
   └── POST /api/chat ─► agno ─► 12 tools consultam o índice
                          │
                          └─ SSE ─► o frontend lê `ToolCallStarted.tool_args`
                                     e aplica destaque / zoom / isolar layer
```

| Camada              | Onde              | Responsabilidade                                |
| ------------------- | ----------------- | ----------------------------------------------- |
| Motor de informação | `src/cad/`        | Lê o DXF, achata a geometria, mantém o índice   |
| HTTP                | `src/api/`        | Rotas, store em memória, SSE                    |
| IA                  | `src/ai_modules/` | Agente, ferramentas, prompt                     |
| Render              | `web/src/viewer/` | Desenha; não sabe o que as entidades significam |

As rotas ficam documentadas em `http://localhost:8787/docs` com o backend rodando.

## Execução

Requisitos: Python ≥ 3.11 com [uv](https://docs.astral.sh/uv/), Node ≥ 20.

```bash
make install                 # uv sync + npm install em web/
cp .env.example .env         # preencha PROXY_AI_BASE_URL e LITELLM_API_KEY
```

Cada variável está comentada no [`.env.example`](.env.example). Em dois terminais:

```bash
make dev        # backend  → http://localhost:8787
make dev-web    # frontend → http://localhost:5173
```

Abra `http://localhost:5173` e arraste um `.dxf`. Para outras portas: `make dev PORT=8788` e `make dev-web VITE_PORT=5174 VITE_API_PORT=8788`.

### Observabilidade

Os traces do agente vão para um [Arize Phoenix](https://phoenix.arize.com/) local, em Docker:

```bash
make phoenix-up      # UI em http://localhost:6006, projeto CAD_VIEWER
make phoenix-down
```

Se a 6006 já estiver ocupada por outro Phoenix, os traces vão parar nele sem erro nenhum. Nesse caso use `PHOENIX_PORT=6007` no `make` e `COLLECTOR_ENDPOINT="http://localhost:6007"` no `.env`. Com `COLLECTOR_ENDPOINT` vazio, o tracing fica desligado.

## Notebooks

Os experimentos ficam em [`experiments/`](experiments/README.md) e os dados de teste em [`data/`](data/README.md). Os notebooks usam um dependency-group próprio:

```bash
uv sync --group notebooks
uv run python -m ipykernel install --user --name cad-viewer --display-name "cad-viewer (.venv)"
```

## Testes e Lint

```bash
make test && make lint                                  # backend
npm --prefix web test && npm --prefix web run typecheck # frontend
```

## Workflow de Desenvolvimento

As branches seguem o padrão:

| Tipo         | Padrão              | Quando usar                                              |
| ------------ | ------------------- | -------------------------------------------------------- |
| Feature      | `feature/<nome>`    | Nova funcionalidade ou componente                        |
| Fix          | `fix/<nome>`        | Correção de bug                                          |
| Chore        | `chore/<nome>`      | Manutenção, dependências, configuração ou infraestrutura |
| Refactor     | `refactor/<nome>`   | Mudança de código sem alterar o comportamento            |
| Documentação | `docs/<nome>`       | Mudanças só de documentação                              |
| Experimento  | `experiment/<nome>` | Experimento de pesquisa                                  |

Os commits seguem o padrão:

> \<tipo>(\<escopo-opcional>): \<descrição-curta>

A descrição é em inglês, no imperativo e sem ponto final (`add`, `fix`, `remove`), com no máximo 72 caracteres na primeira linha.

| Tipo       | Quando usar                                       |
| ---------- | ------------------------------------------------- |
| `feat`     | Nova funcionalidade ou capacidade                 |
| `fix`      | Correção de bug                                   |
| `refactor` | Mudança de código sem alterar o comportamento     |
| `chore`    | Manutenção, dependências, configuração ou scripts |
| `docs`     | Mudanças só de documentação                       |
| `test`     | Adição ou alteração de testes                     |
| `perf`     | Melhoria de performance                           |
| `ci`       | Mudanças no pipeline de CI/CD                     |
| `exp`      | Mudanças exclusivamente nos experimentos          |

## Limites Conhecidos

- DXF ASCII 2D apenas. Sem DWG, sem DXF binário; a coordenada Z é ignorada.
- HATCH e LEADER entram na contagem mas não têm geometria: não são medidos nem destacados.
- Comprimentos e áreas são aproximações sobre a geometria achatada; área existe só para entidades fechadas.
- O documento vive em memória: reiniciar o servidor exige reenviar o arquivo.
- Sem autenticação e sem multiusuário.
