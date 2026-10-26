# PRD — Migração de DXF para AQG

> Status: **revisado contra os 24 AQGs locais e o `viewer.html`, aguardando aprovação**. Nenhum código foi escrito. Branch: `feat/aqg-support`.

## Objetivo

Trocar o DXF pelo AQG (`.json` de *Project* da Arqgen) como formato do produto. O fluxo é: upload → planta 2D → conversa com um agente que entende o domínio do AQG (torres, vagas, tipologias, índices urbanísticos) e aponta de volta para o desenho.

A regra central do projeto não muda: **todo número afirmado pelo agente vem de uma tool.**

Formato e regras do AQG: [`data/aqg/README.md`](data/aqg/README.md).

## Abordagem

Migração direta, numa fase só: o AQG substitui o DXF, e o DXF sai. Não há adaptador nem período com os dois formatos.

O que sustenta isso:

- **O índice continua, o formato DXF sai.** O `CadModel` é a fonte única de verdade que as tools consultam e que o canvas desenha, e esse papel não muda. Saem os campos que só existem por causa do ezdxf.
- **A maior parte já é genérica.** Servem ao AQG sem mudança: os `Prim` de `geometry.py`, o núcleo da `CadEntity` (id, layer, cor, prims, bbox, área, comprimento), o `prims_payload()` e as 4 tools de interface. No frontend, a mudança é pequena: aceitar `.json`, trocar os campos DXF do painel e expandir o id de instância no destaque.
- **As perguntas de domínio já estão no arquivo.** `solution.outputs` traz CA e TO projetados, o total de torres e de unidades, a área construída, as unidades por tipologia e o `DescritivoTorre` de cada torre. O agente responde a maior parte dessas perguntas com uma tool de indicadores, sem depender de geometria.

## O índice

### Referência

O `viewer.html` define o que entra na planta, com um acréscimo: **curvas de nível, taludes, muros de arrimo e crista também entram**. A topografia (`CadMesh`) fica de fora.

### Instâncias e famílias

- **Família da instância:** `hid` e `class_path` casam por prefixo **nos dois sentidos**, como faz o viewer. A regra num sentido só, que o README descreve hoje, perde 1.427 vagas em 6 arquivos. Uma instância sem família vira aviso.
- **Tipo da família** vem de `properties.type`: `Tower` e `DynamicTower3d` (torre), `Vaga`, `Portaria` e os demais (`Lazer`, `Meio`, `Ponta`).
- **Posição:** `mundo = R(angle) · local + (x, y)`, com `angle` em graus, anti-horário.

### Do AQG às entidades

- **Uma entidade por parte**, não por instância. Cada polígono desenhável de `volume[]` vira uma `CadEntity` com layer e área próprios, ligada à instância a que pertence. Uma entidade por instância somaria a área de partes sobrepostas e impediria esconder ou destacar partes.
- **Partes desenhadas**, as mesmas do viewer:
  - torre: tudo, menos `/reference`, `/road_access` e `/access`;
  - vaga e portaria: só `/core`;
  - demais famílias: tudo, menos `/reference`, `/road_access`, `/access`, `/road_network` e `/core/zito`;
  - `drawing_elements[]` é ignorado, como no viewer.
- **Terreno e viário:** cada item de `site.elements` vira uma entidade, e o mesmo vale para cada `PlacedElement` e `PlacedAuxiliaryArea`. O layer é o `cad.layer` normalizado como no viewer: maiúsculas e prefixo `AQG_`, de modo que `talude` vira `AQG_TALUDE`. `CadMesh` não entra.
- **Geometria:** cada anel ou linha do GeoJSON vira um `PolylinePrim`, e `Point` vira `PointPrim`. Só `Polygon` e `MultiPolygon` têm área: Σ (externo − furos), calculada no parser, porque o `_area_of` atual somaria os anéis. `LinearRing` (curva de nível fechada) e linhas não têm área.
- **Cor:** por layer ou parte, com o `viewer.html` como referência.

### Campos da `CadEntity`

| campo | valor |
| --- | --- |
| `id` | `p<i>` para a instância `placed_objects[i]` (e para o `PlacedElement` em `i`), `p<i>.<j>` para a parte `volume[j]` dela, `s<i>` para `site.elements[i]` |
| `type` | categoria da parte (`apartamento`, `varanda`, `circ_vertical`, `shaft`, `core`, `building_pad`, `afastamento`…). Em terreno e viário, o `cad.type` |
| `layer` | nas partes de família, o agrupamento do viewer (`pav_tipo`, `shaft`, `projecao_plato`, `afastamento`, `viario_vaga`, `portaria`, `familia:<tipo>`). No terreno e no viário, o `cad.layer` normalizado |
| `text` | rótulo da parte: a tipologia em apartamento e varanda (tirada do `class_path`) e o label da família nas demais |
| `instance`, `family` | substituem `block`: o id da instância (`p<i>`) e o label da família |

O id é opaco de propósito. Os rótulos "01", "02"… dos `DescritivoTorre` não seguem a ordem de `placed_objects`, e um id legível como `torre-03` levaria o modelo a confundir a torre desenhada com a torre 03 dos indicadores.

### O que muda no `CadModel`

- **Sai:** `doc`, `header`, `acad_version`, `block_names`, `insert_counts` e `entity_raw_props()`.
- **Fica:** `filename`, `entities`, `by_id`, `layers`, `by_type`, `bbox`, `units` (sempre metros) e `warnings`.
- **Entra:**
  - `instances`: id, hid, família, tipo da família, posição e ids das partes;
  - `families`: `class_path`, label e `properties`;
  - indicadores: `solution.outputs`, `site.inputs`, `site.processed_info` e `solution.scores`.
- `CadLayer.frozen` e `on` não existem no AQG e ficam com o padrão (descongelado, ligado).

Os nomes (`CadModel`, `CadEntity`, `src/cad/`) ficam como estão.

## Tools

| Tool | Destino |
| --- | --- |
| `list_layers`, `measure` | ficam |
| `count_entities` | `group_by` passa a ser `type`, `layer` ou `family`. Com `family`, conta **instâncias distintas** ("quantas torres?"), não partes |
| `query_entities` | o filtro `block_name` vira `family`, e entra o filtro `instance` |
| `search_text` | fica, mas passa a buscar no rótulo (tipologia ou família), porque o AQG não tem texto |
| `get_entity_details` | mostra o `hid`, a família e as `properties` dela no lugar das props DXF |
| `highlight_entities`, `zoom_to` | aceitam também o id da instância: `p12` vale por todas as partes dela |
| `clear_highlight`, `set_layer_visibility` | ficam sem mudança |
| `get_header_variables`, `get_block_definition` | saem |
| `get_project_indicators` | nova: expõe `solution.outputs`, `site.inputs`, `site.processed_info`, `solution.scores` e as `properties` das famílias |

**Id de instância:** `split_known_ids` expande `p<i>` nas partes da instância, o que vale para `measure`, `highlight_entities` e `zoom_to`. O frontend aplica a mesma regra ao ler o `ToolCallStarted`: uma entidade casa se `id === x || id.startsWith(x + ".")`. Os nomes e os parâmetros das 4 tools de interface não mudam, então o formato do stream também não muda.

## Regras para o agente

Estas regras entram no `instructions.md`:

- **Área em planta não é área construída.** A planta mostra um pavimento, e a área construída vem dos indicadores.
- **Contagem em planta não é contagem de unidades.** Os polígonos de apartamento de uma torre são as unidades **por pavimento** (7 numa torre de 35 unidades). Unidades, vagas e áreas vêm de `get_project_indicators`.
- **O `DescritivoTorre` não identifica a torre desenhada.** O agente não associa "torre 02" a uma instância.

## Entregas

1. **Parser AQG** em `src/cad/`, que constrói o `CadModel` direto. Substitui o `loader.py` e a parte DXF de `model.py`.
2. **Upload e API:**
   - o upload aceita só `.json`;
   - o `DocumentResponse` perde `acad_version`, `block_count` e `insert_count`;
   - o detalhe de entidade devolve instância, família e `properties` no lugar de `block` e `raw`.
3. **Tools** conforme a tabela acima.
4. **`describe_model()` e `instructions.md` reescritos para o AQG.**
   - O resumo lista o que existe (layers, famílias, tipos de indicador disponíveis), **sem contagens nem medidas**. Isso é mais estrito que o `describe_model()` atual.
   - As instruções trazem as regras da seção acima.
5. **Frontend:**
   - aceitar `.json`;
   - os textos "DXF" viram genéricos;
   - `SidePanel.tsx` e `types.ts` perdem os campos DXF (versão, blocos, props DXF);
   - o id de instância é expandido em `client.ts`.
   - o chat renderiza markdown com `react-markdown` + `remark-gfm` (tabelas, listas numeradas, links), no lugar do `Markdownish.tsx`;
   - as sugestões do chat passam a ser perguntas do domínio AQG.
6. **Testes:**
   - Fixture sintética de AQG com geometria exata, no mesmo princípio de `tests/make_sample.py`. Ela cobre:
     - instância rotacionada;
     - vaga com o prefixo invertido;
     - polígono com furo, com área exata (ex.: 20 × 14 − 2 × 2 = 276);
     - contagem por família;
     - expansão de id de instância;
     - a tool de indicadores.
   - Smoke test sobre `data/aqg/**` quando a pasta existir (pula quando não existir): nenhuma exceção e toda `PlacedFamily` resolvida.
   - Os testes de DXF saem. O teste do frontend contra `recorded-stream.txt` continua valendo.
7. **Remoção do DXF da aplicação:** sai o `loader.py` e todo o caminho DXF de `src/`. A dependência do ezdxf e a pasta `data/dxf/` ficam, porque `experiments/dxf_context_analysis.ipynb` usa os dois.
8. **Documentação:**
   - `CLAUDE.md` da raiz (contagem de tools, arquitetura);
   - `src/cad/CLAUDE.md` (sai a seção de ezdxf, entram as regras do AQG, e a regra do resumo passa a ser "sem contagens");
   - `src/ai_modules/tools/CLAUDE.md`;
   - `README.md`;
   - `data/aqg/README.md` (regra de instanciação nos dois sentidos).

## Fora do escopo

Ficam para depois, a partir do uso real:

- tools de domínio: detalhar torre, programa pedido × projetado via `archprog`, verificação de índices urbanísticos;
- `archprog` e `solution.annotations` (cotas de nível e setas de declive) na tool de indicadores;
- 3D;
- topografia em mesh (`CadMesh`);
- blocos externos de `families[].blocks`;
- preenchimento de polígonos no canvas;
- comparação entre soluções de um mesmo terreno;
- escrita de AQG.

## Achados nos dados

Base: 24 arquivos, 15 em `avaliadas/` e 9 em `favoritadas/`.

- **Identidade:** nem `hid` nem `(hid, index)` são únicos dentro de um arquivo. O id tem de incluir a posição em `placed_objects`.
- **Instanciação invertida:** em 6 arquivos (v16.4 a 18.0), 1.427 vagas têm o `hid` `/equipment/vaga/simples/front_access`, e a família delas é `.../front_access/P/0`. Com a regra nos dois sentidos, todas as `PlacedFamily` dos 24 arquivos encontram família.
- **Ordem das torres:** a ordem dos `DescritivoTorre` difere da de `placed_objects` em 6 arquivos. Testei várias ordenações (x, y, raio, unidades, hid), e nenhuma explica os 8 arquivos em que dá para conferir.
- **Furos:** 12 polígonos de talude (dentro de `MultiPolygon`) e 1 `AQG_RUA`.
- **Layers fora do padrão:** `talude` e `topografia`, em minúsculas e sem o prefixo `AQG_`.
- **Texto:** nenhum. `site.elements` só tem geometria.
- **`road_network`** pode vir `null`.
- **Versões do exportador:** de 7.0.2 a 18.0.0, com o mesmo esquema de topo nos 24 arquivos.
- **Tamanho:** até 18 MB e até 792 entidades por arquivo com as regras acima. Cabe no `MAX_UPLOAD_MB=64` atual.

## Decisões tomadas

- **DXF sai da aplicação:** o projeto muda completamente para o AQG, e nenhum uso do upload de DXF precisa ser preservado.
- **`ezdxf` continua como dependência**, para os experimentos em notebook.
- **Entidade e grupo:** uma entidade por parte, agrupada por instância.
- **Id opaco por posição** (`p<i>`, `p<i>.<j>`, `s<i>`), e as tools de interface aceitam o id da instância.
- **Referência = `viewer.html`, mais curvas de nível, taludes, muros de arrimo e crista.**
- **Furos:** área = externo − internos.
- **`DescritivoTorre` não é vinculado a instância** até a regra ser conhecida.
- **Indicadores expostos:** `solution.outputs`, `site.inputs`, `site.processed_info` e `solution.scores`.
- **Markdown no chat:** `react-markdown` + `remark-gfm`, sem HTML cru, em vez de estender o parser próprio.
- **Label de família duplicado:** aceito como limitação. Famílias diferentes com o mesmo label (caso real: `I/15`, 1 de 24 arquivos) compartilham as `properties` da primeira no detalhe e somam na contagem por família.
- **Sem versão mínima:** o parser é tolerante, o que ele não reconhece vira aviso, e as 24 versões do acervo têm de passar.

## Decisões em aberto

1. **Torre ↔ descritivo:** qual regra liga `DescritivoTorre.order_index` à instância em `placed_objects`? Depende do time do exportador. Até haver resposta, os descritivos ficam sem vínculo com o desenho.
