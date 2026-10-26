# IMPLEMENTATION — Migração de DXF para AQG

> Guia de construção do [`PRD.md`](PRD.md) em tasks para sub-agents. O PRD define **o quê**; este documento define **como**, em que ordem, com quais contratos e como cada peça é testada e avaliada. Branch: `feat/aqg-support`.

## 0. Como usar este documento

### 0.1 Para o orquestrador

O orquestrador é a sessão principal. Ele não implementa as tasks: despacha, valida e conversa com o usuário.

1. **Antes da onda 1:** confirme que a branch é `feat/aqg-support` e pergunte ao usuário se ele prefere ser avisado a cada bloqueio ou que os sub-agents tentem resolver sozinhos até o fim (regra do `CLAUDE.md`). Repasse a resposta em todo brief.
2. **Em cada onda:** despache em paralelo as tasks da onda (`Agent`, `subagent_type: general-purpose`), uma chamada por task, todas na mesma mensagem.
3. **Ao fim de cada onda:**
   - rode as validações da seção 4;
   - revise o diff de cada task contra os critérios de aceite e o checklist de revisão dela;
   - devolva ao sub-agent o que falhar, via `SendMessage` (ele mantém o contexto);
   - com a onda verde, peça ao usuário autorização para commitar.
4. **Na onda 4:** conduza a avaliação final (seção 6) com o usuário.

Nunca commite, faça push ou abra PR sem autorização explícita do usuário ([`commit-rules.md`](commit-rules.md)).

### 0.2 Brief padrão para um sub-agent

```text
Você vai executar a task <Tn> do IMPLEMENTATION.md, na branch feat/aqg-support.

Leia, nesta ordem: CLAUDE.md da raiz, o CLAUDE.md de cada pasta que você vai tocar,
as seções 1, 2 e 3 do IMPLEMENTATION.md e a seção <Tn>.

Regras:
- Toque só nos arquivos listados em "Arquivos" da task. Precisou de outro? Pare e reporte.
- Os contratos da seção 2 são fixos. Achou um problema neles? Pare e reporte; não improvise.
- Não commite, não faça push.
- Preferência de bloqueio do usuário: <avisar a cada bloqueio | seguir até o fim>.

Termine com o relatório da seção 0.3.
```

### 0.3 Relatório que o sub-agent devolve

```text
Task: <Tn>
Arquivos alterados/criados/apagados: <lista>
Validações rodadas: <comando → resultado (passou/falhou, com a saída das falhas)>
Critérios de aceite: <cada um → ok | falhou + motivo>
Desvios do plano: <o que mudou e por quê, ou "nenhum">
Bloqueios: <descrição + 1-2 opções, ou "nenhum">
```

## 1. Contexto comum

### 1.1 O produto e a regra central

O usuário abre um AQG (o JSON de *Project* exportado pela Arqgen), vê a planta 2D e conversa com um agente que responde **e aponta de volta para o desenho**. A IA nunca vê o arquivo: vê um resumo textual (`describe_model()`) e o que as tools devolvem.

**Todo número que o agente afirma vem de uma tool.** É o requisito central do produto. Qualquer mudança que deixe o modelo afirmar uma quantidade, medida ou coordenada sem tool call está errada, por mais conveniente que pareça.

### 1.2 Regras de código

Estas são as regras do `CLAUDE.md` que mais pesam nesta migração. Elas não substituem a leitura do arquivo.

- **KISS:** código mínimo que resolve o problema. Funções em vez de classes, sempre tipadas, com early return. Sem abstração especulativa.
- **Toque só no que a task pede.** Não refatore código vizinho.
- **Logging:** `from src.api.logger import logger`. Nunca `print()` nem `logging.getLogger()`.
- **Configuração:** variáveis de ambiente só via `get_app_settings()`, nunca `os.environ`.
- **Idioma:** chaves de resultado de tool e strings de interface em **pt-BR**; identificadores de código em inglês.
- **Tools nunca levantam exceção por dado inválido:** o erro volta como dado (`erro`, `rejeitados`, `indisponiveis`).
- **Testes de geometria e contagem são exatos** (`==`). A única tolerância admitida é `pytest.approx(..., abs=1e-9)` em coordenadas e áreas que passaram por rotação, porque `cos(90°)` não é zero em float. Assertiva frouxa (`>= 10`) esconde perda de geometria.
- **Comentários:** só para lógica não óbvia. Sem citar ids de task, testes ou pessoas.
- **Lint:** Ruff, line-length 88, regras E/F/I/B.

### 1.3 Posse de arquivo e estado da suíte entre ondas

- **Posse:** cada task lista os arquivos que pode tocar, e nenhum arquivo pertence a duas tasks da mesma onda. Essa lista é a fronteira da task.
- **Durante a onda 1, a suíte inteira fica vermelha.** A T01 troca os tipos de `src/cad/model.py`, e os módulos ainda não migrados (`documents.py`, as tools) quebram no import. É esperado. Cada task valida **os próprios testes**, listados nela.
- **Ao fim da onda 2, `make test` inteiro tem de estar verde.**

### 1.4 Comandos

| Para | Comando |
| --- | --- |
| Testes do backend (um arquivo) | `uv run pytest tests/<arquivo>.py -q` |
| Suíte do backend | `make test` |
| Lint e formatação | `make format && make lint` |
| Frontend | `npm --prefix web run typecheck && npm --prefix web test` |
| App completo | `make dev-all` (backend 8787, frontend 5173, Phoenix 6006) |

### 1.5 Dados reais

- **Onde estão:** em `data/aqg/`, com 15 arquivos em `avaliadas/<site_id>/<ruim|bom|otimo>_<solution_id>.json` e 9 em `favoritadas/`.
- **Versionamento:** os arquivos não são versionados (`.gitignore`). Num clone novo eles não existem, e o smoke test pula.
- **Tamanho:** de 92 KB a 18 MB. **Nunca leia um AQG inteiro com `cat` ou `Read`.** Para inspecionar, escreva um script curto e rode com `python -I` (ou `uv run python -I`), imprimindo só o resumo.
- **Formato:** [`data/aqg/README.md`](data/aqg/README.md).
- **Referência de interpretação:** `data/aqg/viewer.html`. É um bundle minificado de 1,2 MB; o que importa dele já está extraído na seção 2. Não o leia.

## 2. Contratos

Os contratos desta seção são fixos. Uma task que encontre um problema neles para e reporta, em vez de improvisar.

### 2.1 Tipos do índice (`src/cad/model.py`)

```python
DEFAULT_COLOR = "#d6d6d6"
MAX_WARNINGS = 20


class AqgLoadError(Exception):
    """Bytes que não são JSON, ou JSON que não é um Project AQG."""


@dataclass(slots=True)
class CadEntity:
    id: str               # ver 2.2
    type: str             # ver 2.4
    layer: str            # ver 2.4
    color: str            # "#rrggbb"
    prims: list[Prim]
    bbox: BBox | None
    closed: bool          # Polygon, MultiPolygon e LinearRing
    length: float | None  # soma de polyline_length dos PolylinePrim; None se não houver
    area: float | None    # só Polygon/MultiPolygon: Σ (externo − furos); ver 2.5
    text: str | None      # rótulo da parte; ver 2.4
    instance: str | None  # "p<i>" nas partes de família; None no resto
    family: str | None    # CadFamily.label; None fora de família


@dataclass(slots=True)
class CadLayer:           # sem mudança de campos
    name: str
    color: str            # cor da primeira entidade do layer
    count: int
    by_type: dict[str, int]
    bbox: BBox | None
    frozen: bool          # sempre False no AQG
    on: bool              # sempre True no AQG


@dataclass(slots=True)
class CadFamily:
    class_path: str
    label: str            # label normalizado; ver 2.3
    type: str             # properties.type cru: "Tower", "Vaga", "Portaria", "Lazer"…
    properties: dict[str, Any]


@dataclass(slots=True)
class CadInstance:
    id: str               # "p<i>"
    hid: str
    family: str           # CadFamily.label
    family_type: str      # CadFamily.type
    x: float
    y: float
    angle: float          # graus, anti-horário
    entity_ids: list[str] # partes desenhadas, na ordem de volume[]


@dataclass(slots=True)
class CadModel:
    filename: str
    entities: list[CadEntity]
    by_id: dict[str, CadEntity]
    layers: list[CadLayer]
    by_type: dict[str, int]              # ordenado por contagem desc, depois nome
    instances: dict[str, CadInstance]    # só PlacedFamily com família, na ordem de placed_objects
    families: list[CadFamily]            # na ordem de families[]
    indicators: dict[str, Any]           # ver abaixo
    bbox: BBox | None                    # união das bboxes das entidades
    units: str                           # sempre "metros"
    warnings: list[str]                  # deduplicados, teto MAX_WARNINGS

    # `layer_names` (property) e `layer(name)` continuam como hoje.
```

`indicators` sempre tem as quatro chaves, copiadas do arquivo sem transformação:

```python
{
    "outputs": solution.outputs,           # list, [] se ausente
    "inputs": site.inputs,                 # list, [] se ausente
    "processed_info": site.processed_info, # list, [] se ausente
    "scores": solution.scores,             # dict, {} se ausente
}
```

Funções públicas do módulo:

| Função | Contrato |
| --- | --- |
| `load_aqg(data: bytes, filename: str) -> CadModel` | Faz `json.loads` e valida: tem de ser um dict, `families` tem de ser lista e `solution.placed_objects` também. Senão levanta `AqgLoadError` com mensagem em pt-BR (ex.: `"o arquivo não parece um Project AQG: falta a lista families"`). Depois chama `build_model`. |
| `build_model(project: dict, filename: str) -> CadModel` | Constrói o índice segundo 2.2 a 2.5. Problemas de dado viram `warnings`, nunca exceção. |
| `describe_model(model: CadModel) -> str` | Resumo em pt-BR para o system prompt. Ver T01. |
| `prims_payload(model: CadModel) -> list[dict]` | **Formato inalterado** (`id`, `type`, `layer`, `color`, `bbox`, `shapes`). |

Sai do módulo: todo import de `ezdxf`, `entity_raw_props()`, `_HEADER_WHITELIST`, `_UNIT_NAMES` e os campos `doc`, `header`, `acad_version`, `block_names` e `insert_counts`.

### 2.2 Ids

| Id | O que é | Entra em |
| --- | --- | --- |
| `s<i>` | `site.elements[i]` | `by_id` (entidade) |
| `p<i>` com `PlacedFamily` | a instância `placed_objects[i]` | `instances` (**não** está em `by_id`) |
| `p<i>.<j>` | a parte `volume[j]` da família da instância `p<i>` | `by_id` (entidade) |
| `p<i>` com `PlacedElement` ou `PlacedAuxiliaryArea` | o elemento `placed_objects[i]` | `by_id` (entidade) |

- `i` e `j` são posições 0-based no arquivo, contadas **antes** de qualquer exclusão. Assim os ids ficam rastreáveis até o JSON, e uma parte excluída deixa um buraco na numeração (`p0.4` existe, `p0.5` não).
- Não há colisão: um `p<i>` é instância ou entidade, nunca as duas coisas.
- **Expansão de id de instância:** onde uma tool aceita `ids`, `p<i>` vale por todas as entidades de `instances["p<i>"].entity_ids`. O frontend aplica a mesma regra: uma entidade casa com a referência `r` se `id === r || id.startsWith(r + ".")`.

### 2.3 Instâncias e famílias

**Casamento de família.** Seja `matches(a, b) = a == b or a.startswith(b.rstrip("/") + "/")`. A família de uma `PlacedFamily` é a **primeira** de `families[]`, na ordem do arquivo, que satisfaz `matches(hid, class_path) or matches(class_path, hid)`. Sem família → aviso `"instância p<i> (<hid>) sem família — ignorada"`, e a instância não entra no índice.

**Categoria da família**, por `properties.type` em minúsculas:

| `properties.type` | Categoria |
| --- | --- |
| `tower`, `dynamictower3d` | torre |
| `vaga` | vaga |
| `portaria` | portaria |
| qualquer outro (`lazer`…) | outra |

**Label normalizado:** `label.strip()`. Se vazio, usa o último segmento do `class_path`. Se só tem dígitos, vira `f"{properties.type} {label}"` (`"0"` → `"Vaga 0"`).

**Transformação** de uma parte para o mundo, com `θ = radians(position.angle)`:

```text
x' = x + px·cos θ − py·sin θ
y' = y + px·sin θ + py·cos θ
```

A rotação é anti-horária e está **verificada**: com ela, os 3.167 `/core` de `PlacedFamily` do acervo caem dentro do `AQG_PERIMETRO`, e com a rotação horária não caem. `site.elements` e `PlacedElement` já vêm em coordenadas do terreno, sem transformação. `position.z` é ignorado.

### 2.4 Tabela de partes: o que entra, com qual layer, type, rótulo e cor

O fundo do canvas é escuro (`#0e1116`) e ele desenha só contorno. Por isso a cor de cada material é o **fill** do viewer, ou o **edge** quando não há fill. As bordas escuras do viewer sumiriam nesse fundo.

**Partes de família.** Com `segs = class_path.strip("/").split("/")`, o type padrão de uma parte é `segs[1]` se `segs[0] == "area"`, senão `segs[0]`. Isso dá `/area/shaft/privativo` → `shaft`, `/core/Casamar 8PP` → `core` e `/area/garden` → `garden`. O rótulo padrão é o label da família.

| Categoria | Partes excluídas | Parte (prefixo de `class_path`) | layer | type | text (rótulo) | cor |
| --- | --- | --- | --- | --- | --- | --- |
| torre | `/reference`, `/road_access`, `/access` | `/area/apartamento` | `pav_tipo` | `apartamento` | tipologia = `segs[2]` | `#BDD9E7` |
| torre | | `/area/varanda` | `pav_tipo` | `varanda` | tipologia = `segs[2]` | `#BDD9E7` |
| torre | | `/area/circ_vertical`, `/area/circ_horizontal` | `pav_tipo` | padrão | padrão | `#F0F0F0` |
| torre | | `/area/shaft` | `shaft` | `shaft` | padrão | `#E8E8E8` |
| torre | | `/core` e `/core/*` | `pav_tipo` | `core` | padrão | `#D0D0CF` |
| torre | | `/building_pad` | `projecao_plato` | `building_pad` | padrão | `#DEDEDC` |
| torre | | `/afastamento` | `afastamento` | `afastamento` | padrão | `#FE8484` |
| torre | | qualquer outra (ex.: `/area/garden`) | `pav_tipo` | padrão | padrão | `#C9DCCB` |
| vaga | tudo que não é `/core` **exato** | `/core` | `viario_vaga` | `vaga` | padrão | `#E1E1E1` |
| portaria | tudo que não é `/core` **exato** | `/core` | `portaria` | `portaria` | padrão | `#E6DCC8` |
| outra | `/reference`, `/road_access`, `/access`, `/road_network`, `/core/zito` | `/core` e `/core/*` | `familia:<type minúsculo>` | `core` | padrão | `#E6DCC8` |
| outra | | demais | `familia:<type minúsculo>` | padrão | padrão | `#C9DCCB` |

- "Prefixo" usa `matches()` de 2.3: `/core` casa `/core/x`, mas não `/corex`.
- Na tipologia, se `segs[2]` não existir, o rótulo cai no padrão.
- `drawing_elements[]` é ignorado.

**Terreno e viário** (`site.elements` e `PlacedElement`/`PlacedAuxiliaryArea`):

- **Exclusão:** `cad.type == "CadMesh"` (topografia) fica de fora, sem aviso.
- **Layer:** `cad.layer` normalizado, `name.upper()` com prefixo `AQG_` quando faltar (`talude` → `AQG_TALUDE`).
- **type:** `cad.type` (`CadPolygon`, `CadPolyline`, `CadMultiPolygon`, `CadMultiPolyline`, `CadBlock`).
- **text:** o `label` do `PlacedElement` (ex.: `"rua"`, `"talude"`); `None` nos `site.elements`.
- **`instance` e `family`:** `None`.

| Layer normalizado | cor |
| --- | --- |
| `AQG_PERIMETRO` | `DEFAULT_COLOR` (`#d6d6d6`) |
| `AQG_OFFSET` | `#FE8484` |
| `AQG_FRENTE`, `AQG_FUNDOS` | `#9AA5B1` |
| `AQG_ACESSO` | `#009961` |
| `AQG_RUA`, ou `hid` que começa com `/road_network` | `#7C8798` |
| qualquer outro (curvas, taludes, muros, crista, APP, área de lazer…) | `#B7C3D0` |

### 2.5 Geometria GeoJSON → primitivas

Coordenadas podem ter Z; use só `[:2]`. Todo anel passa por `normalize_closed()` (de `geometry.py`), que remove o ponto repetido de fechamento.

| `geometry.type` | Primitivas | `closed` | `area` |
| --- | --- | --- | --- |
| `Polygon` | um `PolylinePrim(closed=True)` por anel | `True` | `polygon_area(anel 0) − Σ polygon_area(furos)` |
| `MultiPolygon` | idem, para cada polígono | `True` | soma das áreas dos polígonos |
| `LinearRing` (curva de nível fechada) | um `PolylinePrim(closed=True)` | `True` | `None` |
| `LineString` | um `PolylinePrim(closed=False)` | `False` | `None` |
| `MultiLineString` | um `PolylinePrim(closed=False)` por linha | `False` | `None` |
| `Point` | um `PointPrim` | `False` | `None` |
| ausente ou outro tipo | — | — | aviso; a entidade não é criada |

- `length` é a soma de `polyline_length` de todos os `PolylinePrim`, furos incluídos. `bbox` vem de `bbox_of_prims`.
- **Não use `_area_of()` do código DXF:** ele somaria a área dos furos.

### 2.6 API HTTP

`POST /api/documents` (multipart, campo `file`) → `201`:

```json
{
  "document_id": "…", "filename": "x.json", "units": "metros",
  "bbox": [0, 0, 100, 80], "entity_count": 18, "layer_count": 9,
  "by_type": {"apartamento": 4},
  "layers": [{"name": "pav_tipo", "color": "#BDD9E7", "count": 8, "by_type": {}, "bbox": [], "frozen": false, "on": true}],
  "warnings": []
}
```

- Erros: `413` acima de `MAX_UPLOAD_MB`; `400` para `AqgLoadError` ou modelo sem nenhuma entidade (`"o arquivo não contém geometria desenhável"`).
- O nome padrão do arquivo, quando o upload não traz um, é `"projeto.json"`.
- **Saem do `DocumentResponse`:** `acad_version`, `block_count` e `insert_count`.

`GET /api/documents/{id}` devolve o mesmo corpo. `GET /api/documents/{id}/prims` não muda.

`GET /api/documents/{id}/entities/{entity_id}` só aceita ids de entidade (não de instância); id desconhecido → `404`:

```json
{
  "id": "p0.0", "type": "apartamento", "layer": "pav_tipo", "color": "#BDD9E7",
  "bbox": [20, 10, 25, 20], "closed": true, "length": 30.0, "area": 50.0,
  "text": "2 Quartos", "instance": "p0", "family": "T/4",
  "hid": "/building/torre/T/4/0i/2f/11111111",
  "properties": {"type": "Tower", "total_pavimentos": 2}
}
```

`instance`, `family` e `hid` são `null` fora de família, e `properties` é `{}`. **Saem:** `block` e `raw`.

### 2.7 Tools (11: 7 de consulta, 4 de interface)

**Chaves de `entity_brief()`:** `id`, `tipo`, `layer`, `comprimento`, `area`, `rotulo` (era `texto`), `instancia` e `familia` (era `bloco`), `bbox`. Cada uma só aparece quando tem valor.

**`split_known_ids(model, ids) -> tuple[list[str], list[str]]`** percorre os ids na ordem e sem duplicar:

- id em `model.by_id` → conhecido;
- id em `model.instances` → as `entity_ids` da instância entram como conhecidas;
- senão → rejeitado.

| Tool | Assinatura (sem o `run_context`) | Contrato |
| --- | --- | --- |
| `list_layers` | `(sort_by: Literal["count", "name"] = "count")` | inalterada |
| `count_entities` | `(group_by: Literal["type", "layer", "family"] = "type", layer: str \| None = None, entity_type: str \| None = None)` | ver abaixo da tabela |
| `query_entities` | como hoje, trocando `block_name` por `family: str \| None` (igualdade sem caixa com `entity.family`) e acrescentando `instance: str \| None` (igualdade com `entity.instance`) | `text_contains` busca no rótulo |
| `get_entity_details` | `(entity_id: str)` | ver abaixo da tabela |
| `search_text` | inalterada | busca em `entity.text`, o rótulo (tipologia ou família); docstring reescrita |
| `measure` | inalterada | `ids` aceita id de instância; `unidade` é `"metros"` |
| `get_project_indicators` | `(tipos: list[str] \| None = None)` | ver abaixo da tabela |
| `highlight_entities`, `clear_highlight`, `zoom_to`, `set_layer_visibility` | **nomes e parâmetros inalterados** | `ids` aceita id de instância; `destacadas` conta partes |

**`count_entities`:**

- `type` e `layer` contam entidades, como hoje.
- `family` conta **instâncias distintas** entre as entidades filtradas que têm `instance`.
- O payload ganha `"unidade": "entidades"` ou `"unidade": "instancias"`.

**`get_entity_details`:**

- Com id de entidade, devolve `entity_brief` + `fechada` + `cor` e, se a entidade for de família, também `instancia`, `hid`, `familia`, `tipo_familia` e `propriedades_familia`.
- Com id de instância, devolve `instancia`, `hid`, `familia`, `tipo_familia`, `propriedades_familia` e `partes` (os ids).
- Id desconhecido → erro como dado.

**`get_project_indicators`:**

- Devolve `indicadores` (`outputs`), `exigidos` (`inputs`), `terreno` (`processed_info`), `notas` (`scores`), `familias` (`[{familia, tipo, propriedades}]`) e `observacao`, fixa: `"os DescritivoTorre (01, 02…) não identificam as torres desenhadas (p<i>)"`.
- Com `tipos`, filtra `indicadores`, `exigidos` e `terreno` pelo campo `type`, sem diferenciar maiúsculas. Os tipos desconhecidos vão para `indisponiveis`, junto com `tipos_disponiveis`.

Saem: `get_block_definition` e `get_header_variables`.

### 2.8 Fixture sintética (`tests/make_aqg_sample.py`)

`build_sample_project() -> dict` devolve exatamente o projeto abaixo, com `rect(x0, y0, x1, y1)` = `[[[x0,y0],[x1,y0],[x1,y1],[x0,y1],[x0,y0]]]`. Os testes de T01, T03 e T04 dependem destes ids e números.

**`families`:**

| class_path | label | properties | volume (índice: class_path → geometria local) |
| --- | --- | --- | --- |
| `/building/torre/T/4/0i/2f` | `T/4` | `{"type": "Tower", "total_pavimentos": 2}` | 0: `/area/apartamento/2 Quartos/aaaa` → `rect(0,0,5,10)` · 1: `/area/apartamento/2 Quartos/aaaa` → `rect(5,0,10,10)` · 2: `/area/varanda/2 Quartos` → `rect(0,10,10,11)` · 3: `/area/shaft/privativo` → `rect(0,11,1,12)` · 4: `/core` → `rect(0,0,10,20)` · 5: `/reference/envelope` → `rect(0,0,10,20)` · 6: `/road_access/Endline` → LineString `[[0,0],[10,0]]` · 7: `/access/mandatory` → `rect(0,-1,10,0)` |
| `/equipment/vaga/simples/front_access/P/0` | `0` | `{"type": "Vaga", "unidades": 1}` | 0: `/core` → `rect(0,0,2.5,5)` · 1: `/core/zito` → `rect(0,0,2.5,0.5)` · 2: `/access/mandatory` → `rect(0,5,2.5,6)` |

**`site.elements`:**

| i | `cad.layer` | `cad.type` | geometria |
| --- | --- | --- | --- |
| 0 | `AQG_PERIMETRO` | `CadPolygon` | Polygon `rect(0,0,100,80)` |
| 1 | `AQG_FRENTE` | `CadPolyline` | LineString `[[0,0],[100,0]]` |
| 2 | `AQG_CURVA_DE_NIVEL_MESTRA` | `CadPolyline` | LinearRing `[[10,60],[30,60],[30,70],[10,70],[10,60]]` |
| 3 | `AQG_PORTARIA` | `CadBlock` | Point `[50,75]` |
| 4 | `topografia` | `CadMesh` | MultiPoint `[[0,0,1],[1,1,2]]` |

**`solution.placed_objects`:**

| i | type | hid / cad | position (x, y, angle) |
| --- | --- | --- | --- |
| 0 | PlacedFamily | `/building/torre/T/4/0i/2f/11111111` | 20, 10, 0 |
| 1 | PlacedFamily | `/building/torre/T/4/0i/2f/22222222` | 60, 10, 90 |
| 2 | PlacedFamily | `/equipment/vaga/simples/front_access` (prefixo invertido) | 5, 40, 0 |
| 3 | PlacedFamily | `/equipment/vaga/simples/front_access` | 8, 40, 0 |
| 4 | PlacedElement | label `talude`, hid `/talude/t1`, layer `talude`, `CadMultiPolygon`, MultiPolygon `[[ externo rect(60,50,80,64), furo [[65,55],[67,55],[67,57],[65,57],[65,55]] ]]` | — |
| 5 | PlacedElement | label `rua`, hid `/road_network/r1`, layer `AQG_RUA`, `CadPolygon`, Polygon `rect(0,70,100,75)` | — |
| 6 | PlacedFamily | `/building/inexistente/x` (sem família) | 0, 0, 0 |

**Indicadores:**

- `solution.outputs`:
  - `{"type":"TotalDeTorres","value":2}`
  - `{"type":"TotalDeUnidades","value":37}`
  - `{"type":"AreaTotalConstruida","value":1234.5}`
  - `{"type":"CAProjetado","value":1.78}`
  - `{"type":"DescritivoTorre","label":"01","order_index":0,"unidades":20}`
  - `{"type":"DescritivoTorre","label":"02","order_index":1,"unidades":17}`
- `site.inputs`: `{"type":"CAMaximoExigido","value":2.9}` e `{"type":"Municipio","value":"Florianópolis"}`.
- `site.processed_info`: `{"type":"AreaDoTerreno","value":8000}`.
- `solution.scores`: `{"total":0.65,"alignment":0.94}`.
- Demais chaves: `road_network: null`, `annotations: []`, `archprog: []`, `version: "18.0.0"`.

**Resultado esperado (exato, salvo onde indicado):**

- **18 entidades:** `s0`, `s1`, `s2`, `s3`; `p0.0` a `p0.4`; `p1.0` a `p1.4`; `p2.0`; `p3.0`; `p4`; `p5`. Não existem `s4`, `p0.5`, `p0.6`, `p0.7`, `p2.1`, `p2.2` nem nada de `p6`.
- **4 instâncias:**
  - `p0` e `p1`, família `T/4`, `family_type` `Tower`;
  - `p2` e `p3`, família `Vaga 0`.
- **Contagem por família:** `{"T/4": 2, "Vaga 0": 2}`.
- **1 aviso,** citando `p6`.
- **9 layers:**
  - `pav_tipo` 8;
  - `shaft` 2;
  - `viario_vaga` 2;
  - `AQG_PERIMETRO`, `AQG_FRENTE`, `AQG_CURVA_DE_NIVEL_MESTRA`, `AQG_PORTARIA`, `AQG_TALUDE` e `AQG_RUA`, 1 cada.
- **`by_type`:**
  - `apartamento` 4;
  - `varanda`, `shaft`, `core`, `vaga`, `CadPolygon` e `CadPolyline`, 2 cada;
  - `CadBlock` e `CadMultiPolygon`, 1 cada.
- **Áreas:**
  - `s0` = 8000;
  - `p0.0` = `p0.1` = 50;
  - `p0.2` = 10;
  - `p0.3` = 1;
  - `p0.4` = 200;
  - `p2.0` = `p3.0` = 12,5;
  - `p4` = 276;
  - `p5` = 500;
  - `p1.4` = 200 com `approx(abs=1e-9)`;
  - `s1`, `s2` e `s3` sem área.
- **Comprimentos:** `s0` = 360; `s1` = 100; `s2` = 60 (`closed=True`, sem área).
- **Bboxes:**
  - `p0.4` = (20, 10, 30, 30);
  - `p0.0` = (20, 10, 25, 20);
  - `p1.4` = (40, 10, 60, 20) com `approx(abs=1e-9)`;
  - `p1.0` = (50, 10, 60, 15) com `approx`;
  - `p2.0` = (5, 40, 7,5, 45);
  - `p3.0` = (8, 40, 10,5, 45);
  - modelo = (0, 0, 100, 80).
- **Rótulos:**
  - `p0.0`, `p0.1` e `p0.2` = `"2 Quartos"`;
  - `p0.3` e `p0.4` = `"T/4"`;
  - `p4` = `"talude"`;
  - `s0` = `None`.

## 3. Fatos dos dados (verificados nos 24 arquivos)

| Fato | Consequência | Como reverificar |
| --- | --- | --- |
| Em 6 arquivos, 1.427 vagas têm `hid` = `/equipment/vaga/simples/front_access` e a família é `.../front_access/P/0` | Casamento nos dois sentidos (2.3). Com ele, 100% das `PlacedFamily` encontram família, sem ambiguidade | Smoke test: nenhum aviso "sem família" |
| Rotação anti-horária: 3.167/3.167 `/core` dentro do `AQG_PERIMETRO` | Fórmula de 2.3 | Smoke test: a bbox do perímetro contém a bbox de toda entidade `core`, `vaga` e `portaria`. Verificado no modo estrito: 3.181 partes, folga mínima de 3 cm |
| Em todos os 24, o número de instâncias de torre é igual a `TotalDeTorres` | Invariante de contagem | Smoke test |
| A ordem dos `DescritivoTorre` difere da de `placed_objects` em 6 arquivos; nenhuma ordenação testada explica todos | Não vincular descritivo a instância (PRD) | — |
| Os polígonos de apartamento de uma torre são as unidades **por pavimento** | O agente não conta unidades na planta | Instruções do agente e eval |
| Nem `hid` nem `(hid, index)` são únicos | Id por posição (2.2) | — |
| Furos: 12 polígonos de talude (em `MultiPolygon`) e 1 `AQG_RUA` | Área = externo − furos (2.5) | Fixture: `p4` = 276 |
| Layers `talude` e `topografia` vêm em minúsculas, sem `AQG_` | Normalização (2.4) | Fixture: `p4` em `AQG_TALUDE` |
| A família da vaga tem label `"0"` em 3 arquivos | Label normalizado (2.3) | Fixture: `Vaga 0` |
| Não há texto em nenhum arquivo | `search_text` busca o rótulo | — |
| `road_network` pode vir `null`; versões de 7.0.2 a 18.0.0, com o mesmo esquema de topo | Parser tolerante, sem versão mínima | Smoke test em todos |
| Até 18 MB e 792 entidades por arquivo | Cabe no `MAX_UPLOAD_MB=64`; não precisa de otimização | — |
| As famílias `Meio` e `Ponta` nunca são instanciadas | Sem tratamento especial | — |

## 4. Ondas

```text
Onda 1 (paralelo)   T01 Motor AQG ─────────────┐      T02 Frontend
                                               │
Onda 2 (paralelo)   T03 Tools e agente ◄───────┤
                    T04 API e upload ◄─────────┤
                    T05 Harness de eval ◄──────┘
                                  │
Onda 3              T06 Limpeza do DXF e documentação
                                  │
Onda 4              Avaliação final (orquestrador + usuário)
```

| Onda | Tasks | Validação do orquestrador ao fim |
| --- | --- | --- |
| 1 | T01, T02 | `uv run pytest tests/test_model.py tests/test_geometry.py tests/test_corpus.py -q` e `npm --prefix web run typecheck && npm --prefix web test` |
| 2 | T03, T04, T05 | `make format && make lint && make test`, tudo verde |
| 3 | T06 | idem, mais o grep de resíduos de T06 vazio |
| 4 | — | seção 6 |

## 5. Tasks

### T01 — Motor AQG

**Objetivo.** Substituir o índice DXF por um índice construído direto do AQG, seguindo os contratos 2.1 a 2.5, com fixture sintética e smoke test sobre o acervo real.

**Arquivos.**

- Reescrever `src/cad/model.py` e `src/cad/__init__.py` (exporta `AqgLoadError`, `CadEntity`, `CadFamily`, `CadInstance`, `CadLayer`, `CadModel`, `build_model`, `describe_model`, `load_aqg`, `prims_payload`).
- Reescrever `tests/conftest.py`: `sample_model` = `build_model(build_sample_project(), "sample.json")`, mais a fixture `sample_project`.
- Criar `tests/make_aqg_sample.py` e `tests/test_corpus.py`.
- Reescrever `tests/test_model.py`.
- Apagar `tests/make_sample.py` e `tests/fixtures/sample.dxf`.
- `src/cad/geometry.py` só se for indispensável; o esperado é não mudar.

**O que construir.**

1. Os tipos e as funções públicas de 2.1.
2. Os helpers privados que a implementação pedir. Nomes sugeridos: `_matches`, `_find_family`, `_family_label`, `_part_spec` (categoria + class_path → layer, type, rótulo, cor, ou `None` se excluída), `_site_spec`, `_normalize_layer`, `_transform`, `_geometry` (GeoJSON → prims, closed, area).
3. A construção, numa passada só:
   - `site.elements` (`s<i>`);
   - `placed_objects` na ordem: `PlacedFamily` gera instância e partes; `PlacedElement`/`PlacedAuxiliaryArea` gera entidade `p<i>`;
   - depois `by_id`, `by_type`, os layers (contagem, `by_type`, bbox e cor da primeira entidade, ordenados por nome sem caixa), a bbox do modelo, os indicadores e os avisos deduplicados.
4. `describe_model(model)`:
   - Lista nome do arquivo, unidade (`metros`), nomes dos layers, famílias instanciadas (`label` e `type`, ex.: `T/4 (Tower)`), os tipos de indicador disponíveis (os `type` de `outputs` e `inputs`, deduplicados) e os avisos.
   - Diz que os ids são `p<i>` (instância), `p<i>.<j>` (parte) e `s<i>` (terreno).
   - **Sem contagens, medidas, extensão nem valores de indicador.** O docstring explica o motivo: a regra central.

**Reusar** (não reescrever): de `geometry.py`, `normalize_closed`, `polygon_area`, `polyline_length`, `bbox_of_prims` e `union_bbox`; do `model.py` atual, `_dedupe`, `MAX_WARNINGS`, `prims_payload` e `_round_pair`. A montagem de layers sai de `_build_layers`, sem a tabela LAYER do DXF.

**Testes.**

- `tests/test_model.py` afirma **todo** o "Resultado esperado" de 2.8, mais estes casos:
  - `load_aqg(b"nao e json", "x")` levanta `AqgLoadError`;
  - `load_aqg(b'{"a": 1}', "x")` também;
  - `load_aqg(json.dumps(build_sample_project()).encode(), "x")` equivale a `build_model`;
  - nenhum layer congelado ou oculto;
  - `prims_payload` tem 18 itens com os mesmos ids de `by_id`;
  - `describe_model` contém `T/4`, `Vaga 0`, `AQG_TALUDE`, `TotalDeUnidades` e `metros`, e **não** contém `37`, `1234`, `8000` nem `276`.
- `tests/test_corpus.py`:
  - parametrizado sobre `sorted(Path("data/aqg").rglob("*.json"))`, com `pytest.skip` se a lista vier vazia;
  - para cada arquivo: `load_aqg` não levanta; nenhum aviso contém `"sem família"`; toda instância tem pelo menos uma entidade;
  - a bbox da união do layer `AQG_PERIMETRO` contém (`bbox_contains`) a bbox de toda entidade de type `core`, `vaga` ou `portaria`;
  - o número de instâncias de categoria torre é igual ao `value` do output `TotalDeTorres`.

**Critérios de aceite.**

- `uv run pytest tests/test_model.py tests/test_geometry.py tests/test_corpus.py -q` verde, com o smoke test rodando nos 24 arquivos locais. Informe o tempo.
- `uv run ruff check src/cad tests/test_model.py tests/test_corpus.py tests/make_aqg_sample.py tests/conftest.py` sem erro.
- Nenhum `import ezdxf` em `src/cad/`.

**Checklist de revisão.**

- Ids contados antes da exclusão.
- Área de polígono com furo subtrai os furos.
- `LinearRing` sem área.
- `CadMesh` sem aviso.
- Instância sem família vira aviso, não exceção.
- `describe_model` sem números de medida ou contagem.
- Nenhum valor de `indicators` transformado.

### T02 — Frontend

**Objetivo.** Fazer o frontend aceitar AQG, remover os campos DXF da interface e aplicar a expansão de id de instância nas ações de interface do agente.

**Arquivos.** `web/src/App.tsx`, `web/src/api/types.ts`, `web/src/api/client.ts`, `web/src/components/SidePanel.tsx`, `web/src/components/ChatPanel.tsx`, `web/src/api/__tests__/client.test.ts`. Não tocar em `recorded-stream.txt`.

**O que construir.**

1. **`types.ts`:**
   - `DocumentInfo` perde `acad_version`, `block_count` e `insert_count`;
   - `EntityDetails` troca `block` e `raw` por `instance: string | null`, `family: string | null`, `hid: string | null` e `properties: Record<string, unknown>` (contrato 2.6);
   - comentários que falam de DXF passam a falar do documento.
2. **`client.ts`:** exportar `expandIds(ids: string[], entityIds: Iterable<string>): string[]`, que devolve os ids de entidade que casam com alguma referência pela regra de 2.2, na ordem de `entityIds` e sem duplicar. O despacho das tools (`applyUiTool`) não muda.
3. **`App.tsx`:**
   - `ui.highlight`, `ui.zoomToIds` e `bboxOfIds` usam `expandIds(ids, loaded.byId.keys())` antes de resolver;
   - o input aceita `.json,application/json`;
   - os textos "DXF" viram "projeto" ou "AQG" (ex.: "Abrir projeto", "Arraste um arquivo .json (AQG) aqui").
4. **`SidePanel.tsx`:**
   - saem as linhas de versão do AutoCAD e de blocos/inserções;
   - no detalhe, "Bloco" vira "Instância" e "Família";
   - "props DXF" vira "propriedades da família", mostrado só quando `properties` não está vazio.
5. **`ChatPanel.tsx`:** textos "DXF" viram genéricos ("Abra um projeto AQG para começar…").

**Testes.**

- Em `client.test.ts`, um `describe('expandIds')` cobre:
  - `expandIds(['p0'], ['p0.0', 'p0.1', 'p01.0', 's0'])` → `['p0.0', 'p0.1']` (não casa `p01.0`);
  - id de entidade passa direto;
  - referência desconhecida some;
  - sem duplicata quando `['p0', 'p0.1']`.
- Os testes existentes continuam verdes, incluindo o stream gravado.

**Critérios de aceite.**

- `npm --prefix web run typecheck && npm --prefix web test` verde.
- `grep -rni dxf web/src` sem ocorrências, exceto o próprio `recorded-stream.txt`.

**Checklist de revisão.**

- A expansão acontece no `App.tsx`, não no despacho do stream.
- Nenhum parse de AQG no browser.
- Os nomes das 4 tools de UI e o formato do evento não mudaram.

### T03 — Tools e agente

**Objetivo.** Migrar as tools para o novo índice (contrato 2.7), criar `get_project_indicators` e reescrever as instruções do agente para o domínio AQG.

**Arquivos.** `src/ai_modules/tools/cad_tools/helpers.py`, `query_tools.py`, `ui_tools.py` (só docstrings), `__init__.py` se preciso; `src/ai_modules/agents/cad_agent/instructions.md` e `cad_agent.py` (só o `description`); `src/ai_modules/runner.py` (só o docstring que diz "12 tools"); `tests/test_tools.py`.

**O que construir.**

1. **`helpers.py`:** `entity_brief` com as chaves novas; `split_known_ids` com a expansão; docstring sem "12 tools".
2. **`query_tools.py`:**
   - as tools de 2.7, removendo `get_block_definition` e `get_header_variables`;
   - `get_project_indicators` como nova tool;
   - `QUERY_TOOLS` com 7.
3. **Docstrings prescritivas,** no estilo atual (`"PREFIRA ESTA TOOL…"`):
   - `count_entities`: "para 'quantas torres/vagas' use `group_by='family'`, que conta instâncias", e "não use para unidades habitacionais nem áreas construídas".
   - `get_project_indicators`: "PREFIRA ESTA TOOL para unidades, vagas, áreas construídas, CA, TO, permeabilidade, gabarito e índices exigidos".
   - `measure`: "área em planta não é área construída".
   - `highlight_entities` e `zoom_to`: "aceitam o id da instância (`p<i>`) para destacar todas as partes".
4. **`instructions.md`, reescrito.** Mantém a estrutura atual (o que você sabe, nunca invente números, ligue ao desenho, escolha da ferramenta, limites, estilo) e o texto `Nunca invente números`. Acrescenta:
   - **Formato dos ids:** `p<i>` instância, `p<i>.<j>` parte, `s<i>` terreno.
   - **Escolha de ferramenta:**
     - quantas torres ou vagas → `count_entities(group_by="family")`;
     - unidades, áreas, índices → `get_project_indicators`;
     - tipologia → `search_text` ou `query_entities(text_contains=…)`;
     - detalhe de torre → `get_entity_details("p<i>")`;
     - destacar uma torre → `highlight_entities(["p<i>"])`.
   - **As 3 regras do PRD:** área em planta ≠ área construída; contagem em planta ≠ unidades; `DescritivoTorre` não identifica a torre desenhada.
   - **Limites:** o desenho é 2D e mostra um pavimento-tipo; topografia (mesh) e anotações não são indexadas; a unidade é sempre metros.
   - **Remover** o que é de DXF (HATCH, `$INSUNITS`, curvas amostradas).

**Testes** (`tests/test_tools.py`, reescrito contra a fixture de 2.8).

- Testes estruturais (mantidos):
  - 11 tools registradas;
  - toda tool com nome e descrição;
  - `run_context` fora do schema;
  - documento ausente volta como dado em todas;
  - todo resultado tem `resumo`.
- `count_entities(group_by="family")` → `{"T/4": 2, "Vaga 0": 2}`, `total` 4, `unidade` `"instancias"`. Com `group_by="layer"`, `pav_tipo` = 8.
- `query_entities`:
  - `instance="p1"` → `p1.0` a `p1.4`;
  - `family="t/4", entity_type="apartamento"` → 4;
  - `text_contains="2 quartos"` → 6.
- `search_text("2 Quartos")` → 6.
- `measure`:
  - `["p0.0", "p0.1"]` com `area` = 100;
  - `["p4"]` = 276;
  - `["s2"]` com `area` → `sem_area == ["s2"]`;
  - `["p0"]` com `area` = 311 (50 + 50 + 10 + 1 + 200).
- `highlight_entities`:
  - `["p0"]` → `destacadas` 5, bbox `[20, 10, 30, 30]`;
  - `["p0", "p0.1", "x"]` → `destacadas` 5, `rejeitados` `["x"]`.
- `zoom_to(ids=["p1"])` → bbox ≈ `[40, 10, 60, 20]`.
- `get_entity_details`:
  - `"p0"` → `partes` com 5 ids e `propriedades_familia == {"type": "Tower", "total_pavimentos": 2}`;
  - `"p0.0"` → `familia` `"T/4"`;
  - `"zzz"` → `erro`.
- `get_project_indicators()` contém `TotalDeUnidades` 37, `notas.total` 0,65 e a `observacao`. Com `tipos=["TotalDeTorres", "Xyz"]`, devolve só `TotalDeTorres` e `indisponiveis == ["Xyz"]`.
- Construção do agente (movida de `test_api.py`):
  - `get_cad_agent(user_id="local", model=sample_model)` → 11 tools, `tool_call_limit == 14`;
  - as instruções contêm `<documento_carregado>`, `Nunca invente números`, `T/4` e `metros`.

**Critérios de aceite.** `uv run pytest tests/test_tools.py -q` verde e `uv run ruff check src/ai_modules tests/test_tools.py` limpo.

**Checklist de revisão.**

- Nenhuma tool levanta exceção por dado inválido.
- Chaves em pt-BR.
- Docstrings imperativas.
- `UI_TOOL_NAMES` inalterado.
- `instructions.md` não promete nada que as tools não entregam.
- Nenhum número no `instructions.md`, além do exemplo "7 numa torre de 35" para explicar a armadilha.

### T04 — API e upload

**Objetivo.** Trocar o upload de DXF pelo de AQG e ajustar os modelos HTTP ao contrato 2.6.

**Arquivos.** `src/api/routers/documents.py`, `src/api/models/document.py`, `src/api/store.py` (só docstring), `tests/test_api.py`; apagar `src/cad/loader.py`.

**O que construir.**

1. **`upload_document`:**
   - lê os bytes e mantém o teto de tamanho (413);
   - chama `load_aqg(data, file.filename or "projeto.json")`; `AqgLoadError` → 400;
   - modelo sem entidades → 400 com a mensagem de 2.6;
   - `logger.info` como hoje;
   - a descrição do campo `File` passa a dizer "Arquivo AQG (.json)".
2. **`get_entity`:** monta `EntityDetailsResponse` de 2.6. `hid` e `properties` vêm de `model.instances[entity.instance]` e da `CadFamily` correspondente; fora de família, `null` e `{}`.
3. **`document.py`:** os modelos e `to_document_response` conforme 2.6.
4. **`store.py`:** o docstring fala de "documento" e não de DXF.

**Reusar.** Mantenha `_require`, os status codes e a estrutura atual das rotas; só troque o que o contrato muda.

**Testes** (`tests/test_api.py`, reescrito).

- O upload de `json.dumps(build_sample_project()).encode()` como `("sample.json", ..., "application/json")` → 201, com `entity_count` 18, `units` `"metros"` e sem as chaves `acad_version` e `block_count`.
- Rejeições com 400:
  - bytes que não são JSON;
  - `{"a": 1}`;
  - um projeto válido sem nenhuma entidade desenhável (ex.: só um `CadMesh` em `site.elements` e `placed_objects` vazio).
- `prims` tem os mesmos ids das entidades.
- Detalhe:
  - `p0.0` traz `family` `"T/4"`, o `hid` da instância e as `properties`;
  - `s0` traz `instance` `null` e `properties` `{}`;
  - `p0`, que é instância e não entidade, dá 404.
- Os testes de health, documento desconhecido e chat continuam.
- Remova `test_agent_builds_with_twelve_tools_and_the_document_summary`, que passa para T03.

**Critérios de aceite.**

- `uv run pytest tests/test_api.py -q` verde.
- `uv run ruff check src/api tests/test_api.py` limpo.
- `src/cad/loader.py` não existe.
- `grep -rn "load_dxf\|entity_raw_props" src tests` vazio.

**Checklist de revisão.**

- Nenhuma lógica de negócio no router.
- Mensagens de erro em pt-BR.
- O 404 de documento expirado continua instruindo a reenviar o arquivo.

### T05 — Harness de eval do agente

**Objetivo.** Medir, com o LLM real, se o agente responde certo às perguntas de domínio e se **todo número da resposta tem procedência numa tool**. O eval é rodado manualmente, porque precisa do gateway e de `data/aqg/`.

**Arquivos.** Criar `evals/agent_eval.py` e `tests/test_agent_eval.py`. No `Makefile`: alvo `eval` e `evals` nas listas de `lint` e `format`. No `.gitignore`: acrescentar `evals/results/` (o arquivo tem mudanças locais não commitadas; acrescente uma linha, sem mexer no resto).

**O que construir.**

1. **CLI:**
   - `uv run python -m evals.agent_eval [--all] [--files CAMINHO ...]`, e `make eval` roda a versão padrão;
   - padrão: os 5 `data/aqg/avaliadas/*/otimo_*.json`; `--all`: os 15 de `avaliadas/`.
2. **Para cada arquivo:**
   - `model = load_aqg(path.read_bytes(), path.name)`;
   - para cada caso, um agente novo (`get_cad_agent(user_id="eval", model=model)`) e uma sessão nova (`chat_id = uuid4().hex`);
   - a execução usa `run_chat(agent, ChatRequest(...), "eval", model)`, iterando os eventos.
   - **Não crie um caminho de execução paralelo.**
   - Coleta: texto de `RunContent` (`event.content`) e, de cada `ToolCallCompleted`, `event.tool.tool_name`, `tool_args` e `result`. Confirme os nomes em `agno/run/agent.py`.
3. **Casos.** O valor esperado vem de `model.indicators`; sem o valor no arquivo, o caso é pulado e marcado.

| Id | Pergunta | Esperado |
| --- | --- | --- |
| torres | "Quantas torres tem este projeto?" | `TotalDeTorres` |
| unidades | "Quantas unidades habitacionais o projeto tem no total?" | `TotalDeUnidades` |
| area | "Qual é a área total construída?" | `AreaTotalConstruida` |
| ca | "Qual o CA projetado e qual o CA máximo permitido?" | `CAProjetado` e `CAMaximoExigido` (inputs) |
| vagas | "Quantas vagas de estacionamento foram projetadas?" | `NumeroDeVagasProjetado` |
| destaque | "Destaque todas as torres no desenho." | algum `highlight_entities` cujos ids, expandidos com `split_known_ids`, cobrem todas as entidades das instâncias de categoria torre |
| vinculo | "Qual das torres desenhadas é a torre 02 dos indicadores?" | só com 2 ou mais `DescritivoTorre`; status `revisar`, com a resposta registrada para revisão humana |

**Funções puras**, testáveis sem LLM:

- `extract_numbers(text: str) -> list[tuple[float, int]]`: devolve valor e casas decimais. Aceita pt-BR (`13.166,7`, `1,78`) e ponto decimal (`13166.7`). Grupos `\d{1,3}(\.\d{3})+` sem vírgula são milhar.
- `is_sourced(value: float, decimals: int, sources: list[float]) -> bool`: verdadeiro se algum `s` satisfaz `round(s, decimals) == value`. Isso aceita o arredondamento que o modelo faz ao citar.
- `unsourced(answer: str, tool_results: list[str], allowed_text: str) -> list[str]`: lista os números da resposta sem procedência. As fontes são os números de todos os resultados de tool da run, mais os de `allowed_text`, que é a pergunta mais o `describe_model`. Labels como `T/4` e ids como `p12` vêm de lá.

**Métricas por caso:**

- `acerto`: o valor esperado aparece na resposta, via `is_sourced` com o esperado como única fonte;
- `procedencia`: `unsourced(...) == []`.

**Saída:** uma tabela por arquivo × caso no stdout (`ok`, `falha`, `revisar` ou `pulado`, com os números sem procedência) e um JSON completo em `evals/results/<AAAAMMDD-HHMMSS>.json`, com pergunta, resposta, tools chamadas e números.

**Testes** (`tests/test_agent_eval.py`, sem rede).

- `extract_numbers("13.166,7 m², CA 1,78 e 145 unidades")` → valores 13166,7, 1,78 e 145.
- `is_sourced(13166.7, 1, [13166.70000001])` é verdadeiro; `is_sourced(36.4, 1, [36.44])` também; `is_sourced(37, 0, [36.4])` é falso.
- `unsourced` acusa um número inventado e aceita um que veio da pergunta.

**Critérios de aceite.**

- `uv run pytest tests/test_agent_eval.py -q` verde e `make lint` limpo em `evals`.
- `uv run python -m evals.agent_eval --help` funciona sem o gateway configurado: o import do módulo não exige `.env`, e o agente só é criado na execução.

**Checklist de revisão.**

- Reusa `run_chat` e `get_cad_agent`.
- Uma sessão nova por pergunta.
- Execução sequencial, sem paralelismo.
- Nenhum valor esperado escrito à mão: tudo vem do arquivo.

### T06 — Limpeza do DXF e documentação

**Objetivo.** Deixar o repositório coerente com o AQG: documentação atualizada e nenhum resíduo do caminho DXF na aplicação. O notebook e `data/dxf/` ficam.

**Arquivos.**

- `CLAUDE.md`, `src/cad/CLAUDE.md`, `src/ai_modules/CLAUDE.md`, `src/ai_modules/tools/CLAUDE.md`, `README.md`, `data/aqg/README.md`.
- Qualquer resíduo de "DXF" que o grep encontrar em `src/`, `web/src` e `tests/`. As outras tasks já terminaram, então não há conflito de posse.

**O que fazer.**

1. **`CLAUDE.md` da raiz:**
   - "12 tools" → "11 tools (7 de consulta, 4 de interface)";
   - na arquitetura, sai "ezdxf (parse e índice)" e entra "parser AQG próprio em `src/cad/`";
   - mapa de arquivos sem `loader.py`, com `model.py` → `load_aqg()`;
   - em "Testes", a fixture passa a ser `tests/make_aqg_sample.py`, com os números de exemplo dela (perímetro 8000, talude 276);
   - "não parseie DXF no frontend" → "AQG";
   - em "Segurança", "o arquivo DXF é enviado" → "o AQG é enviado";
   - "Arquivos Auxiliares" lista o `PRD.md` e o `IMPLEMENTATION.md`;
   - continua abaixo de 200 linhas.
2. **`src/cad/CLAUDE.md`, reescrito:**
   - mapa;
   - as 3 primitivas (mantém);
   - as regras do AQG de 2.2 a 2.5 em forma de regra (casamento nos dois sentidos, rotação anti-horária verificada, tabela de partes, furos, ids opacos e por quê);
   - armadilhas verificadas (seção 3);
   - `describe_model` **sem contagens**;
   - avisos.
   - Sai a seção do ezdxf.
3. **`src/ai_modules/tools/CLAUDE.md`:**
   - 11 tools;
   - `get_project_indicators`;
   - chaves novas (`rotulo`, `instancia`, `familia`);
   - regra de expansão de id;
   - a regra "ao renomear uma tool de UI, atualize junto…" continua.
4. **`src/ai_modules/CLAUDE.md`:** só o que citar DXF ou o número de tools.
5. **`README.md`:** DXF → AQG; 12 → 11; instruções de uso com upload de `.json`; menção a `data/aqg/` e a `make eval`.
6. **`data/aqg/README.md`:** a regra de instanciação passa a ser nos dois sentidos (com o caso das vagas), a rotação está verificada e a ordem dos `DescritivoTorre` não segue `placed_objects`.
7. **Grep de resíduos:** `grep -rni "dxf\|ezdxf" src web/src tests --include=*.py --include=*.ts --include=*.tsx`. Corrija o que for da aplicação, como o comentário de `src/api/models/chat.py`. Deixe `experiments/` e `pyproject.toml` (o ezdxf continua como dependência).

**Critérios de aceite.**

- `make format && make lint && make test` e `npm --prefix web run typecheck && npm --prefix web test` verdes.
- O grep do passo 7 vazio (exceto `recorded-stream.txt`).
- `CLAUDE.md` com no máximo 200 linhas.

**Checklist de revisão.**

- Sub-CLAUDEs sem exemplo desatualizado.
- Nenhum "12 tools" sobrando.
- A documentação descreve o que o código faz, não o que o PRD planejava.

## 6. Avaliação final (onda 4, orquestrador + usuário)

1. **Suíte:** `make format && make lint && make test` e `npm --prefix web run typecheck && npm --prefix web test` verdes. O smoke test tem de ter rodado nos 24 arquivos, sem `skip`.
2. **Eval do agente:** `make eval` (5 arquivos × 7 casos). Antes de rodar, confirme com o usuário, porque usa o gateway e tem custo.
   - **Meta dura:** zero números sem procedência em todas as respostas. Qualquer número sem procedência é falha do requisito central.
   - **Meta de acerto:** `torres`, `unidades`, `area`, `ca` e `vagas` corretos nos 5 arquivos, e `destaque` cobrindo todas as torres.
   - Revisão humana dos casos `vinculo`: o agente tem de recusar associar o descritivo a uma torre desenhada.
   - Falha vira ajuste de docstring ou de `instructions.md` (T03), decidido com o usuário. Rode o eval de novo depois do ajuste.
3. **Teste manual no app (`make dev-all`):** abra um arquivo de `avaliadas/`, confira a planta (torres dentro do terreno, vagas, taludes e curvas visíveis) e pergunte:
   - "quantas torres?";
   - "destaque a torre `p<i>`";
   - "isole o layer pav_tipo";
   - "quantas unidades?".
   O destaque e o isolamento têm de aparecer no canvas.
4. **Revisão de código:** `/code-review` sobre o diff da branch contra `main`.
5. **Fechamento:**
   - registre o resumo do que foi feito e os desvios do plano (`CLAUDE.md`);
   - peça autorização para commit, push e PR;
   - antes do push, atualize com `main` e resolva os conflitos junto com o usuário ([`commit-rules.md`](commit-rules.md)).
