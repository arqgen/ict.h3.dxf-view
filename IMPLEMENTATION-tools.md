# IMPLEMENTATION — Novas tools AQG

> Guia de construção do [`PRD-tools.md`](PRD-tools.md). O PRD define **o quê** e decide cada cartão; este documento define **como**: em que ordem, com quais contratos, em quais arquivos e como cada peça é testada. Uma task só começa quando o cartão dela está `aprovado` no PRD e o portão dela, se houver, está resolvido.

## 0. Como usar este documento

### 0.1 Execução

- **Sequencial, uma task por vez.** Quase todo cartão mexe em `query_tools.py`, `instructions.md` e `tests/test_tools.py`, então tasks em paralelo brigariam pelos mesmos arquivos.
- **Branch:** `feat/aqg-tools`, criada a partir de `feat/aqg-support` (que ainda tem 12 commits fora da `main`). Regras em [`commit-rules.md`](commit-rules.md).
- **Ao fim de cada task:** rode as validações (1.2), confira os critérios de aceite, atualize os documentos listados na task e **pergunte sobre o commit**. A autorização de um commit não vale para o próximo.
- **Portão:** decisão que precisa do desenvolvedor antes de escrever código. Sem a decisão, a task não começa.

### 0.2 Decisões já tomadas

| Decisão | Valor |
| --- | --- |
| Escopo deste documento | todos os cartões do PRD |
| Veredito do C1 | estrito, sem tolerância: 19,99 contra 20 exigidos "não atende" |
| Unidade de `site.analysis.avg_inclination` (S1) | percentual |
| Execução | sequencial, na ordem da seção 4; entregue em lotes, com o eval por lote |
| T3 | vínculo por grupo de torres idênticas aceito; o vínculo com uma instância só continua proibido |
| C3 | `AQG_OFFSET` é a linha de recuo (caminho b); pegada = `pav_tipo` desenhado; `entre_blocos` vale para todo par de torres |
| P1 | CA mínimo, proporção de tipologias e vagas por unidade são meta; casamento de tipologia pelo trecho depois de `/apartamento/` |
| S2 | setas de declive só como desenho, com a classe no rótulo e o `value` fora |

## 1. Contexto comum

### 1.1 Regras

As regras do [`CLAUDE.md`](CLAUDE.md) e a seção 1.2 do [`IMPLEMENTATION.md`](IMPLEMENTATION.md) valem aqui sem exceção. As que mais pesam nestes cartões:

- **Todo número afirmado vem de uma tool.** Se uma resposta pede conta, a conta fica na tool, e a tool devolve o total pronto. O modelo não soma, não subtrai e não conta itens de lista.
- **Tool nunca levanta exceção por dado inválido:** dado ausente volta como `erro`, `indisponivel` ou `indisponiveis`.
- **Chaves de resultado em pt-BR**, números arredondados com `rnd()` (`helpers.py`).
- **Docstrings imperativas:** é o que o modelo lê para escolher a tool. Ver [`src/ai_modules/tools/CLAUDE.md`](src/ai_modules/tools/CLAUDE.md).
- **Testes exatos.** A única tolerância é `pytest.approx(..., abs=1e-9)` em coordenada que passou por rotação.
- **Fixture compartilhada intocada.** `tests/make_aqg_sample.py` tem contagens afirmadas em vários testes. Um caso novo monta uma variante no próprio teste (`copy.deepcopy(build_sample_project())` e muda só o que precisa).

**Tool nova** (`check_zoning`, `check_setbacks`, `compare_program`, `color_by`) muda a contagem de tools. Atualize junto:

- `assert len(CAD_TOOLS) == 12` e o dicionário `CALLS` em `tests/test_tools.py`;
- as menções a "12 tools" no `CLAUDE.md` da raiz, em `src/ai_modules/tools/CLAUDE.md` e no `CAPABILITIES.md`.

**Tool de interface nova** (`color_by`) muda também, juntos, `UI_TOOL_NAMES` (`ui_tools.py`), `UI_TOOLS` e `applyUiTool` (`web/src/api/client.ts`).

### 1.2 Validações

| Para | Comando |
| --- | --- |
| Backend | `make format && make lint && make test` |
| Frontend (tasks que tocam `web/`) | `npm --prefix web run typecheck && npm --prefix web test` |
| Eval com o LLM (custa; rodar ao fim de cada onda) | `make eval`, ou `uv run python -m evals.agent_eval --files <arquivos>` |

`tests/test_corpus.py` roda sobre os 24 AQGs de `data/aqg/` quando existem. Para inspecionar um AQG, use um script curto com `uv run python -I`, nunca `cat` ou `Read` (há arquivos de até 18 MB).

### 1.3 Harness de eval

`CASES` em `evals/agent_eval.py` hoje é `(id, pergunta, [(seção, type)])`, e `_indicator` lê só `value`. Os cartões precisam de valores fora de `value` (`GabaritoMaximoExigido.altura`, `MovimentoDeTerra.corte`) e de valores calculados (unidades por torre). A task C1 faz a mudança uma vez, e as seguintes só acrescentam casos:

- o terceiro item de cada caso vira uma função `esperado(model: CadModel) -> list[float | None]`;
- `_indicator(model, seção, type, campo="value")`;
- a pergunta pode ter `{torre}`, trocado pelo primeiro id de instância de torre em ordem de id.

Um `None` em `esperado` continua pulando o caso, como hoje.

## 2. Contratos

Os contratos desta seção são usados por mais de uma task e são fixos. Achou um problema neles? Pare e reporte.

### 2.1 Família da instância pela posição (F0)

```python
@dataclass(slots=True)
class CadInstance:
    ...
    family_index: int  # posição em model.families
```

- `build_model` já tem o índice `k` ao chamar `_place_family` e o repassa.
- Tudo que precisa das propriedades da família usa `model.families[inst.family_index]`.
- `inst.family` (o label) continua existindo: é o que `count_entities(group_by="family")` agrupa e o que o filtro `family` de `query_entities` compara.

### 2.2 Unidades da torre (T1; usado por T2, T3 e P1)

Em `src/cad/model.py`:

```python
def tower_units(properties: dict[str, Any]) -> tuple[int, int] | None:
    """(unidades por pavimento, unidades da torre), ou None sem o dado."""
```

- **Tipologias:** `properties["pav_tipo"]["tipologias"]` na família `Tower` e `properties["tipologias"]` na `DynamicTower3d`. É um dict `class_path → quantidade por pavimento`.
- **`n_pavimentos_unidades`:** no topo de `properties`, nos dois tipos.
- **Conta:** `por_pavimento = sum(tipologias.values())` e `da_torre = por_pavimento × n_pavimentos_unidades`.
- **Sem o dado** (chave ausente ou valor não inteiro): devolve `None`.

### 2.3 Comparação com limite (C1)

Em `query_tools.py`:

```python
# (indice, projetado, limite, campo do limite, sentido)
ZONING_RULES = (
    ("CA", "CAProjetado", "CAMaximoExigido", "value", "maximo"),
    ("TO", "TOProjetada", "TOExigida", "value", "maximo"),
    ("Permeabilidade", "PermeabilidadeProjetada", "PermeabilidadeExigida", "value", "minimo"),
    ("Gabarito", "GabaritoProjetado", "GabaritoMaximoExigido", "altura", "maximo"),
)
```

Resultado de uma comparação, igual em `compare_indicators` e em cada regra de `check_zoning`:

| Chave | Conteúdo |
| --- | --- |
| `projetado` / `limite` | `{"tipo": ..., "valor": ...}` |
| `sentido` | `"maximo"` ou `"minimo"` |
| `atende` | estrito: `projetado ≤ limite` no máximo, `projetado ≥ limite` no mínimo |
| `folga` | ≥ 0 quando atende, nos dois sentidos: `limite − projetado` no máximo, `projetado − limite` no mínimo |
| `percentual_do_limite` | `projetado ÷ limite × 100`, ou `None` se o limite for 0 |

- `percentual_usado` sai, porque o nome só faz sentido para um máximo.
- Um par fora da tabela usa o campo `value` e o sentido `"maximo"`, como hoje, e o `sentido` no resultado diz isso ao modelo.

### 2.4 Distância entre bordas (C2; usado por C3 e S2)

Em `src/cad/geometry.py`:

```python
def min_distance(a: list[Prim], b: list[Prim]) -> float:
    """Menor distancia entre as bordas de dois conjuntos de primitivas."""
```

- **Distância entre bordas:** uma torre dentro do perímetro dá a distância até a linha do perímetro, que é o que um recuo mede. Por isso não há teste de "ponto dentro do polígono".
- **0 quando duas bordas se cruzam ou se tocam.**
- **Por segmento:** cada `PolylinePrim` vira segmentos, com o de fechamento quando `closed`. `PointPrim` e `TextPrim` viram um ponto.
- **Conta:** menor `distance_point_segment` (já existe) entre extremos e segmentos, com um teste de cruzamento de segmentos antes.
- **Custo:** O(n·m) segmentos. Marque com `# ponytail:` e indique o índice espacial como saída se ficar lento. Nos arquivos atuais são poucas centenas de segmentos por torre.

### 2.5 Ids de anotação (S2)

`a<i>` é a entidade de `solution.annotations[i]`, por posição e contada antes de qualquer exclusão, como `s<i>` e `p<i>`. O frontend não precisa mudar: `expandIds` já trata qualquer id que não seja de instância.

## 3. Fatos dos dados

Verificados por script nos 24 AQGs locais em 26/10/2026.

| Fato | Usado em |
| --- | --- |
| Um arquivo (`bom_6ace3c8be748…`) tem duas famílias `I/15`, com 9 e 10 pavimentos com unidades. Somando as unidades das torres pelo label, dá 400; pela família da instância, dá 415 = `TotalDeUnidades`. Pela família da instância, a soma fecha em 24/24 | F0, T1 |
| Todo `DescritivoTorre`, exceto `TOTAL`, casa pelas `unidades` com exatamente uma família de torre, resolvida pela posição (24/24) | T3 |
| `Tower`: `n_pavimentos_unidades` no topo e `tipologias` em `pav_tipo` (33/33 famílias). `DynamicTower3d`: os dois no topo (1 arquivo) | T1 |
| `GabaritoMaximoExigido` tem só `altura` e `pavimentos`, sem `value` (24/24) | C1 |
| Permeabilidade de 19,99 contra 20 exigidos no `favoritadas/6abab05295f4…`. Os outros 23 atendem CA, TO, permeabilidade e gabarito | C1 |
| `DescritivoTorre.afastamento` é numérico em 24/24. `AfastamentoProjetado.lateral` é igual ao maior afastamento das torres, e `entre_blocos` ao dobro, até o arredondamento (24/24) | C3 |
| Toda torre tem `building_pad` (78/78). A caixa do pad contém a do `pav_tipo` em 70/78, e a caixa do envelope `/afastamento` contém a do pad em 75/78 | C2, C3 |
| `site.analysis` existe em 15: `avg_inclination` e as mesmas 8 faixas de 0 a 100 | S1 |
| `CotaTopografia` e `AreaDoTerreno` vêm em `site.processed_info`, cujos tipos o `describe_model` não lista | S1 |
| `MovimentoDeTerra` (17) não tem `value`: os campos são `corte`, `aterro`, `balanco`, `muro_altura`, `muro_comprimento`, `limpeza` e os fatores | S1 |
| Layers de terreno: `AQG_TALUDE_CORTE` e `AQG_TALUDE_ATERRO` (17), `AQG_CRISTA` (17), `AQG_TALUDE` (15), `AQG_MURO_DE_ARRIMO` (9) | S1 |
| Anotações: 323 marcos (`Annotation`, hid `/annotation/elevation_marker`, `position` x, y, z, com `value` = z) e 101 setas (`SlopeArrow`, `line` em `LineString` 3D, `value`, e a classe no hid: 100 `gentle`, 1 `steep`) | S2, I3 |
| `archprog.FamilyProportion` (`/building/apartamento/<x>`) e `UnidadesPorTipologia` (`/area/apartamento/<x>`) casam pelo trecho depois de `/apartamento/` em 32/35. As 3 restantes são tipologias pedidas e não projetadas, 2 delas com proporção 0 | P1 |
| A proporção projetada difere da pedida na maioria dos arquivos (ex.: 85% pedido, 58,6% projetado), e `VagasPorUnidade` fica abaixo de `ParkingLotPerUnit` em 6 dos 14 arquivos com os dois | P1 |
| `CadMesh`: vértices em `geometry` (`MultiPoint` x, y, z) e faces em `cad.faces`. Malhas: `AQG_TOPOGRAFIA_NOVA` em `placed_objects` (37), `AQG_TOPOGRAFIA` (9), `AQG_TOPOGRAFIA_ORIGINAL` (6) e `topografia` (4). Até ~43 mil vértices numa malha | S3 |

## 4. Ordem

```text
Onda 1 (sem portão)        F0 → Q1 → C1 → T1+T2 → S1
Onda 2 (sem portão)        C2 → I1 → I2a (preenchimento)
Onda 3 (com portão)        T3 · C3 · P1 · S2 → I3 · I2b (color_by)
Spike (a qualquer hora)    S3
```

| Onda | Por que nesta ordem |
| --- | --- |
| 1 | F0 corrige um dado errado hoje e é pré-requisito de T1. Q1 é uma linha. C1 introduz o harness de eval novo (1.3). S1 fecha a onda com as rotas do `instructions.md` |
| 2 | C2 é a base de C3 e S2. I1 e I2a são só frontend |
| 3 | Cada task tem uma decisão de produto antes do código. I3 depende de S2 |
| Spike | S3 entrega um relatório, não código de produção |

Ao fim de cada onda: `make eval` (custa) e o resumo da rodada no `CAPABILITIES.md`, seção "Como foi validado".

## 5. Tasks

### F0 — Família da instância pela posição

**Objetivo.** O detalhe de uma torre usa as propriedades da família dela, e não as da primeira família com o mesmo label.

**Arquivos.** `src/cad/model.py`, `src/ai_modules/tools/cad_tools/query_tools.py`, `tests/test_model.py`, `tests/test_tools.py`.

**Como fazer.**

1. `family_index` em `CadInstance` (2.1), preenchido em `build_model`.
2. `_instance_info` troca o `next(f for f in model.families if f.label == ...)` por `model.families[inst.family_index]`.

**Testes.** Uma variante da fixture com uma terceira família `T/4` (`class_path` `/building/torre/T/4/0i/3f`, `properties` `{"type": "Tower", "total_pavimentos": 3}`), com o hid de `p1` apontando para ela:

- `test_model.py`: o `family_index` de `p1` é o da família nova;
- `test_tools.py`: `get_entity_details("p1")` devolve `total_pavimentos` 3, e `count_entities(group_by="family")` continua contando 2 instâncias em `T/4`.

**Docs.** [`src/cad/CLAUDE.md`](src/cad/CLAUDE.md), armadilha 7: deixa de ser "limitação aceita", e a contagem por label continua somando as duas famílias. No `CAPABILITIES.md`, a limitação "famílias com o mesmo nome" fica só com a contagem.

**Aceite.** `make test` verde; o caso da variante passa.

### Q1 — Famílias só sem filtro em `get_project_indicators`

**Objetivo.** Chamada filtrada por `tipos` deixa de levar as propriedades de todas as famílias.

**Arquivos.** `query_tools.py`, `tests/test_tools.py`.

**Como fazer.** `payload["familias"]` só quando `tipos` vier vazio. A docstring diz que as propriedades de uma torre estão em `get_entity_details`.

**Testes.** `test_get_project_indicators_filters_by_type` afirma que `familias` não está no payload. O teste sem filtro continua igual.

**Docs.** [`src/ai_modules/tools/CLAUDE.md`](src/ai_modules/tools/CLAUDE.md), seção "Indicadores".

**Aceite.** `make test` verde.

### C1 — Veredito por índice

**Objetivo.** O assistente diz se o projeto atende CA, TO, permeabilidade e gabarito, com o sentido certo de cada limite.

**Arquivos.** `query_tools.py`, `instructions.md`, `tests/test_tools.py`, `evals/agent_eval.py`, mais os da regra de tool nova (1.1).

**Como fazer.**

1. `ZONING_RULES` e um helper privado que compara um par e devolve o resultado de 2.3.
2. `_numeric_indicator(model, name, field="value")`, para ler `altura` do gabarito.
3. `compare_indicators` usa o helper, buscando o limite em `ZONING_RULES` para saber o campo e o sentido.
4. Tool nova `check_zoning()`, sem parâmetros:
   - devolve `regras`, uma comparação por linha de `ZONING_RULES`;
   - uma regra sem dado vira `{"indice": ..., "indisponivel": [tipos ausentes]}`;
   - devolve os totais prontos: `nao_atende` (lista de índices) e `atende_todas` (`None` se alguma regra ficou indisponível).
5. Docstring de `check_zoning`: "USE ESTA TOOL para 'o projeto está dentro dos índices?' e para qualquer índice isolado". `compare_indicators` fica para pares fora da tabela.
6. `instructions.md`, em "Escolha da ferramenta":
   - "atende os índices / está dentro do limite" → `check_zoning`;
   - a regra "Não faça contas" passa a citar as duas tools.
7. Harness de eval (1.3).

**Testes.**

- `compare_indicators` com o CA da fixture: `folga` = `round(2.9 - 1.78, 3)`, `atende` verdadeiro, `sentido` `"maximo"`.
- Variante com `PermeabilidadeProjetada` 19,99 e `PermeabilidadeExigida` 20: `atende` falso, `folga` −0,01.
- Variante com `GabaritoProjetado` e `GabaritoMaximoExigido` só com `altura`: o gabarito é comparado.
- `check_zoning` na fixture: CA comparado e as outras três regras indisponíveis.

**Eval.** Caso `zoneamento`: "O projeto atende CA, TO, permeabilidade e gabarito?"

- `esperado`: os 8 valores (projetado e limite das 4 regras);
- acerto também exige uma chamada a `check_zoning`;
- rodar também com `--files data/aqg/favoritadas/6abab05295f499e81abeca64_6abd57caa4c6bcd7c7e56699.json` e conferir à mão que a resposta diz que a permeabilidade não atende.

**Docs.** `CAPABILITIES.md`: sai a limitação de `compare_indicators` e entra `check_zoning` na tabela de indicadores. [`src/ai_modules/tools/CLAUDE.md`](src/ai_modules/tools/CLAUDE.md): seção "Indicadores".

**Aceite.** `make test` verde; o eval do `6abab05295f4…` diz que não atende.

### T1 + T2 — Unidades por torre e por família

**Objetivo.** "Quantas unidades tem a torre p3?" e "quantas unidades há em cada família?" respondidos pela tool, com a conta pronta.

**Depende de.** F0.

**Arquivos.** `src/cad/model.py`, `query_tools.py`, `instructions.md`, `tests/test_model.py`, `tests/test_tools.py`, `tests/test_corpus.py`, `evals/agent_eval.py`.

**Como fazer.**

1. `tower_units()` (2.2).
2. `_instance_info`: com `tower_units` não nulo, acrescenta `unidades_por_pavimento` e `unidades_da_torre`. Vale para id de instância e de parte de torre.
3. `count_entities(group_by="family")`, quando há torre na seleção, acrescenta:
   - `unidades_por_familia`: soma, por label, das `unidades_da_torre` de cada instância, pela família da própria instância, o que dá certo no caso `I/15`;
   - `total_unidades`.
4. Docstrings:
   - os campos vêm das propriedades da família (tipologias × pavimentos), não da contagem de polígonos;
   - o total do projeto continua sendo `TotalDeUnidades`.
5. `instructions.md`:
   - a armadilha "Contagem em planta não é contagem de unidades" ganha a rota "unidades de uma torre → `get_entity_details`; por família → `count_entities(group_by="family")`";
   - o total do projeto continua em `get_project_indicators`.

**Testes.**

- `test_model.py`: `tower_units` para `Tower` (em `pav_tipo`), `DynamicTower3d` (no topo), sem `tipologias` (`None`) e com `n_pavimentos_unidades` não inteiro (`None`).
- `test_tools.py`: uma variante com `tipologias` `{"/area/apartamento/2 Quartos/aaaa": 2}` e `n_pavimentos_unidades` 2 na família `T/4` dá `unidades_da_torre` 4, `unidades_por_familia` `{"T/4": 8}` e `total_unidades` 8.
- `test_corpus.py`: a soma de `unidades_da_torre` das torres é igual a `TotalDeUnidades` em cada arquivo.

**Eval.**

- "Quantas unidades tem cada torre?" → `esperado` = as `unidades_da_torre` distintas;
- "Quantas unidades há em cada família de torre?" → os valores de `unidades_por_familia`.

**Docs.**

- `CAPABILITIES.md`: as unidades por torre e por família saem de "ainda não faz" e entram nas tabelas das tools;
- [`src/cad/CLAUDE.md`](src/cad/CLAUDE.md): `tower_units` no mapa.

**Aceite.** `make test` verde, com o corpus em 24/24.

### S1 — Ficha do terreno

**Objetivo.** Corte, aterro, muro, cota de referência, inclinação, zoneamento e município respondidos e roteados.

**Arquivos.** `src/cad/model.py`, `query_tools.py`, `instructions.md`, `tests/test_model.py`, `tests/test_tools.py`, `evals/agent_eval.py`.

**Como fazer.**

1. `build_model` guarda `indicators["inclinacao_media"]` com `site.analysis.avg_inclination`, ou `None`. Os índices de face de `inclination_groups` ficam fora.
2. `get_project_indicators` acrescenta ao grupo `terreno`, antes do filtro por `tipos`, o item `{"type": "InclinacaoMedia", "value": rnd(x), "unidade": "%"}` quando houver.
3. `describe_model` lista também os tipos de `processed_info` e `InclinacaoMedia`, só os nomes. Hoje `CotaTopografia` fica invisível ao modelo.
4. `instructions.md`, em "Escolha da ferramenta":
   - corte, aterro, muro, movimento de terra → `get_project_indicators(tipos=["MovimentoDeTerra", "DetalhamentoMovimentoDeTerra"])`;
   - cota, inclinação, zoneamento, município → `tipos=["CotaTopografia", "InclinacaoMedia", "Zoneamento", "Municipio"]`;
   - projeção das torres, alturas, descritivos de tipologia e de vaga → os tipos correspondentes (hoje expostos e sem rota);
   - para mostrar o movimento de terra, `set_layer_visibility` isolando os layers de talude, crista e muro que existirem (3).
5. Em "Limites que você deve declarar": a inclinação passa a existir; o mesh continua fora.

**Testes.**

- `test_model.py`: variante com `site.analysis` guarda a inclinação; sem `analysis`, o valor é `None`.
- `test_tools.py`: `get_project_indicators(tipos=["InclinacaoMedia"])` na variante devolve o item com `"unidade": "%"`.
- O teste de `describe_model` afirma que `AreaDoTerreno` aparece e que `8000` continua fora.

**Eval.**

- "Quanto de corte e aterro o projeto prevê?" → `esperado` = `MovimentoDeTerra.corte` e `.aterro`;
- "Qual a inclinação média do terreno?" → `esperado` = `avg_inclination`.

Os dois pulam nos arquivos sem o dado.

**Docs.** `CAPABILITIES.md`: sai a linha de `site.analysis` de "Fica fora do índice", e a lista "dados que o `instructions.md` ainda não roteia" fica vazia.

**Aberto.** O arquivo não traz a unidade de corte e aterro. A tool não acrescenta unidade; se o modelo disser m³, isso é uma leitura do domínio, não um número sem tool.

**Aceite.** `make test` verde.

### C2 — Distância entre bordas

**Objetivo.** `measure` mede a menor distância entre as bordas de duas entidades, o que serve para recuo e afastamento.

**Arquivos.** `src/cad/geometry.py`, `query_tools.py`, `tests/test_geometry.py`, `tests/test_tools.py`.

**Como fazer.**

1. `min_distance()` (2.4) e um helper de cruzamento de segmentos em `geometry.py`.
2. Novo valor `"edge_distance"` em `metric` de `measure`, com exatamente 2 referências:
   - um id de parte vale pela parte;
   - um id de instância de torre vale pelas partes do layer `pav_tipo`, o pavimento desenhado, sem o envelope `/afastamento` nem o `building_pad`;
   - um id de outra instância vale por todas as partes.
3. O resultado diz o que mediu, em `referencia`: "menor distância entre as bordas" e, para torre, "pavimento-tipo desenhado".
4. A docstring de `measure` diferencia `distance` (entre centros, não serve para recuo) de `edge_distance`.

**Testes.**

- `test_geometry.py`, exatos: dois retângulos a 10 m dão 10; retângulos que se tocam ou se cruzam dão 0; linha e polígono; um retângulo dentro de outro dá a distância até a borda de fora.
- `test_tools.py`: `edge_distance` entre `p0` e `p1` da fixture é 10. O core de `p0` vai de x 20 a 30, e o de `p1`, girado 90°, de x 40 a 60, então o valor sai com `pytest.approx(10, abs=1e-9)`.

**Eval.** "Qual a menor distância entre as torres `{torre}` e a vizinha?" fica de fora: depende de saber qual é a vizinha. O caso entra com C3.

**Docs.** `CAPABILITIES.md`, tabela de `measure`.

**Aceite.** `make test` verde.

### I1 — Perguntar sobre a seleção

**Objetivo.** Com uma entidade selecionada no canvas, um botão leva o id dela para o chat.

**Arquivos.** `web/src/App.tsx`, `web/src/components/SidePanel.tsx`, `web/src/components/ChatPanel.tsx`.

**Como fazer.**

1. `App.tsx` ganha o estado `chatDraft: string | null`.
2. `SidePanel`, no bloco da seleção, ganha o botão "Perguntar sobre isto", que chama `onAskAbout(selected.id)`. O `App` faz `setChatDraft("Sobre <id>: ")`.
3. `ChatPanel` recebe `draft`. Um `useEffect` copia o texto para o `input` e dá foco ao campo.

O contrato da API não muda: o id viaja no texto, e o modelo continua precisando de `get_entity_details` para qualquer número.

**Testes.** `npm --prefix web run typecheck`. É lógica de estado trivial, sem teste novo. Conferir no app (`make dev-all`): selecionar uma vaga, clicar, enviar "o que é isto?".

**Docs.** `CAPABILITIES.md`, seção "Ações na planta".

**Aceite.** typecheck e testes do frontend verdes; o fluxo funciona no app.

### I2a — Preenchimento dos polígonos

**Objetivo.** O canvas preenche os polígonos com área, em vez de desenhar só o contorno.

**Arquivos.** `src/cad/model.py` (`prims_payload`), `web/src/api/types.ts`, `web/src/viewer/CadCanvas.tsx`, `tests/test_model.py`.

**Como fazer.**

1. `prims_payload` acrescenta `"filled": entity.area is not None` a cada entidade. Curva de nível fechada (`LinearRing`) tem `closed` mas não tem área, e não deve ser preenchida.
2. `PrimEntity` em `types.ts` ganha `filled: boolean`.
3. No desenho, entidade com `filled` faz `ctx.fill()` na cor dela, com transparência, antes do contorno. A ordem do payload (terreno antes das torres) já põe o perímetro por baixo.

**Testes.** `test_model.py`: no payload, o talude (`p4`) tem `filled` verdadeiro, e a curva de nível, falso. Conferir no app.

**Aceite.** `make test`, typecheck e testes do frontend verdes.

### T3 — Vínculo descritivo ↔ grupo de torres

**Portão.** Aceitar o vínculo por grupo, revogando "nunca vincule descritivo a instância" (`PRD.md`, [`src/cad/CLAUDE.md`](src/cad/CLAUDE.md), `instructions.md` e o caso `vinculo` do eval).

**Depende de.** F0, T1.

**Objetivo.** "Qual é a torre 02?" e "qual a altura da torre p3?" respondidos pelo grupo de torres idênticas a que o descritivo corresponde.

**Arquivos.** `src/cad/model.py`, `query_tools.py`, `instructions.md`, `tests/test_model.py`, `tests/test_tools.py`, `tests/test_corpus.py`, `evals/agent_eval.py`.

**Como fazer.**

1. Em `model.py`, `descriptor_groups(model) -> dict[str, list[str]]`: rótulo do `DescritivoTorre` → ids das instâncias da família casada.
   - Ignora a linha `TOTAL`.
   - Casa pelas `unidades` do descritivo com `tower_units(...)[1]` de cada família, agrupando as instâncias por `family_index`.
   - Descritivo que casa com nenhuma família, ou com mais de uma, fica fora.
2. `get_entity_details` de uma torre acrescenta:
   - `descritivos`: os rótulos casados com a família dela;
   - `descritivo`: os campos do primeiro deles;
   - `grupo`: as instâncias da família;
   - `observacao`: "o vínculo é com o grupo de torres idênticas, não com uma instância".
3. `get_project_indicators`, quando devolve `DescritivoTorre`:
   - acrescenta `vinculo_descritivos` (rótulo → instâncias);
   - a `observacao` passa a dizer que a linha `TOTAL` é a soma, não uma torre.
4. `instructions.md`: a terceira armadilha vira "o descritivo aponta um grupo de torres idênticas; destaque o grupo inteiro e diga que dentro dele não há como distinguir".

**Testes.**

- `test_model.py`: uma variante com duas famílias de unidades diferentes casa cada descritivo com a sua; uma com duas famílias de unidades iguais deixa o descritivo fora.
- `test_corpus.py`: todo descritivo, exceto `TOTAL`, casa com exatamente uma família, em 24/24.

**Eval.**

- O caso `vinculo` deixa de ser `revisar`: acerto = `highlight_entities` cobre as instâncias do grupo de `02`.
- Caso novo: "Qual a altura da torre `{torre}`?" → `esperado` = `altura` do descritivo casado.

**Docs.**

- `PRD.md`: registrar a revogação;
- [`src/cad/CLAUDE.md`](src/cad/CLAUDE.md): armadilha 2;
- `CAPABILITIES.md`: "Recusa de propósito", "Decisão em aberto" e a linha TOTAL.

**Aceite.** `make test` verde, com o corpus em 24/24.

### C3 — Recuos e afastamento entre torres

**Portão.** Três decisões, nesta ordem:

1. **Papel do `AQG_OFFSET`.** Medir por script a distância do `AQG_OFFSET` ao `AQG_PERIMETRO` e ao `AQG_FRENTE` e comparar com os recuos. Se for a linha de recuo, a verificação vira "a pegada da torre cabe no offset", e o caminho 2a abaixo cai.
2. **Pegada da torre.** O `pav_tipo` (padrão do C2), o `building_pad` ou outra parte (fatos em 3).
3. **`entre_blocos`.** Confirmar que esse valor único vale para todo par de torres, inclusive entre torres de alturas diferentes.

**Depende de.** C2.

**Objetivo.** "As torres respeitam os recuos e o afastamento?", com um veredito por torre e os ids que não atendem.

**Arquivos.** `query_tools.py`, `instructions.md`, `tests/test_tools.py`, `evals/agent_eval.py`, mais os da regra de tool nova (1.1).

**Como fazer.** Tool nova `check_setbacks()`, sem parâmetros:

1. A pegada de cada torre, conforme o portão.
2. Recuos, por um destes caminhos:
   - a. sem offset: `min_distance` da pegada ao `AQG_FRENTE` contra `RecuoFrontal`, ao `AQG_FUNDOS` contra `RecuoFundos` e ao `AQG_PERIMETRO` contra `RecuoLateral`;
   - b. com offset: se a pegada cabe no polígono do offset.

   Um recuo sem o indicador ou sem a linha volta como `indisponivel`.
3. Afastamento: `min_distance` entre as pegadas de cada par de torres contra `AfastamentoProjetado.entre_blocos`.
4. Totais prontos:
   - `torres_que_nao_atendem` (ids);
   - `pares_que_nao_atendem`;
   - a `distancia` medida e o `exigido` de cada verificação.
5. Docstring: a tool verifica só o que o arquivo declara, não interpreta a regra municipal. Para mostrar, chame `highlight_entities` com `torres_que_nao_atendem`.

**Testes.** Variante da fixture com `RecuoFrontal` e `AfastamentoProjetado`. As torres a 10 m uma da outra atendem com `entre_blocos` 8 e não atendem com 12; mesmo esquema para o recuo frontal contra o `AQG_FRENTE` (y = 0).

**Eval.**

- "As torres respeitam o afastamento entre blocos?" → `esperado` = `entre_blocos`;
- acerto também exige uma chamada a `check_setbacks`.

**Docs.** `CAPABILITIES.md`; o caso de C2 fica coberto aqui.

**Aceite.** `make test` verde, e a tool roda nos 24 arquivos sem erro (script ou corpus).

### P1 — Programa pedido × projetado

**Portão.**

1. **Proporção de tipologias e vagas por unidade:** são requisito (veredito) ou meta (só a diferença)? Os fatos de 3 indicam meta. O padrão proposto é meta.
2. **Casamento de tipologia** pelo trecho depois de `/apartamento/` (32/35, e as 3 restantes são tipologias não projetadas).

**Depende de.** T1, para as unidades por pavimento de cada torre.

**Objetivo.** "O projeto cumpre o programa pedido?", com o resultado de cada regra presente no arquivo.

**Arquivos.** `src/cad/model.py`, `query_tools.py`, `instructions.md`, `tests/test_model.py`, `tests/test_tools.py`, `evals/agent_eval.py`, mais os da regra de tool nova (1.1).

**Como fazer.**

1. `build_model` guarda `indicators["archprog"]` (lista crua, `[]` se ausente). O `archprog` deixa de ficar fora do índice.
2. Tool nova `compare_program()`, sem parâmetros. Uma linha por regra presente no `archprog`, e regra ausente volta como `"nao_pedido"`, nunca como falha:

   | Pedido | Projetado | Resultado |
   | --- | --- | --- |
   | `CAMin` | `CAProjetado` | veredito (mínimo) |
   | `MaxHeight` | `GabaritoProjetado` | veredito (máximo) |
   | `MinPavimentos` / `MaxPavimentos` | `NumeroDePavimentos` | veredito de faixa; texto não numérico vira `indisponivel` |
   | `MinTowersBySite` / `MaxTowersBySite` | `TotalDeTorres` | veredito de faixa |
   | `MinUnitsPerFloor` / `MaxUnitsPerFloor` | `tower_units(...)[0]` de cada torre | veredito por torre e os ids fora da faixa |
   | `ParkingLotPerUnit` | `VagasPorUnidade` | pedido, projetado e diferença (meta, conforme o portão) |
   | `FamilyProportion` | `UnidadesPorTipologia` | por tipologia: % pedido, % projetado (calculado pela tool) e diferença em pontos percentuais (meta) |

3. Totais prontos: `regras_que_nao_atendem` e `torres_fora_da_faixa`.

**Testes.** Variante da fixture com `archprog` cobrindo uma regra de cada forma, mais uma tipologia pedida e não projetada (% projetado 0).

**Eval.** "O número de pavimentos está dentro do pedido?" → `esperado` = `NumeroDePavimentos` e os limites presentes.

**Docs.** `CAPABILITIES.md`: sai a linha do `archprog` de "Fica fora do índice". [`src/cad/CLAUDE.md`](src/cad/CLAUDE.md): `archprog` no índice.

**Aceite.** `make test` verde, e a tool roda nos 24 arquivos sem erro.

### S2 — Cotas de nível

**Portão.** Confirmar que as setas de declive entram só como desenho, com a classe (`gentle`, `steep`) no rótulo. O `value` delas não tem unidade conhecida e fica fora.

**Depende de.** C2, para ordenar pela proximidade.

**Objetivo.** "Qual a cota perto da torre p3?" e "qual a maior cota marcada?" respondidos pela tool.

**Arquivos.** `src/cad/model.py`, `query_tools.py`, `instructions.md`, `tests/test_model.py`, `tests/test_tools.py`, `evals/agent_eval.py`.

**Como fazer.**

1. `build_model` lê `solution.annotations` com o id `a<i>` (2.5):
   - **marco** (`Annotation`, `/annotation/elevation_marker`): layer `AQG_COTA`, type `cota`, um `PointPrim` e um `TextPrim` em (x, y), com o rótulo `f"{value:.2f}"`. A altura do texto é uma constante de módulo;
   - **seta** (`SlopeArrow`): layer `AQG_SETA_DECLIVE`, type `seta_declive`, um `PolylinePrim` com o x, y de `line`, e o rótulo com a classe tirada do hid;
   - **outro tipo:** vira aviso.
2. `query_entities` ganha:
   - `sort_by="cota_desc"` e `"cota_asc"`, que ordenam as entidades `cota` pelo valor do rótulo;
   - `near: str | None`, que ordena por `min_distance` até a referência e acrescenta `distancia` a cada item devolvido.
3. `instructions.md`:
   - rota "cota perto de X → `query_entities(entity_type="cota", near="X", limit=1)`";
   - rota "maior ou menor cota → `sort_by="cota_desc"` ou `"cota_asc"`";
   - em "Limites", as anotações passam a ser indexadas.
4. A docstring de `search_text`, que diz que anotações não existem, é corrigida.
5. Os ids `a<i>` entram em `describe_model`, no `instructions.md` e na tabela de ids do `CAPABILITIES.md`.

**Testes.** Variante da fixture com 2 marcos e 1 seta:

- `test_model.py`: as entidades `a0`, `a1` e `a2`, com layer, type, rótulo e um `TextPrim` no marco;
- `test_tools.py`: `cota_desc` devolve o marco maior primeiro, e `near="p0"` devolve o marco mais perto de `p0` primeiro, com a `distancia` exata.

**Eval.** "Qual a maior cota marcada no terreno?" → `esperado` = o maior `value` dos marcos.

**Docs.** `CAPABILITIES.md`: sai a linha de anotações de "Fica fora do índice". [`src/cad/CLAUDE.md`](src/cad/CLAUDE.md): os ids `a<i>`, e o `TextPrim` passa a ser produzido.

**Aceite.** `make test` verde, com o corpus sem aviso novo.

### I3 — Cotas e setas desenhadas

**Depende de.** S2.

**Objetivo.** Os marcos e as setas de S2 aparecem no canvas.

**Arquivos.** `src/cad/model.py` (cores), `web/src/viewer/CadCanvas.tsx`.

**Como fazer.**

1. Verificar no app: o canvas já desenha `TextPrim` (`drawTexts`) e polilinhas, então os marcos e as setas devem aparecer sem código novo.
2. Cores próprias para `AQG_COTA` e `AQG_SETA_DECLIVE` em `_SITE_COLORS`.
3. **Ponta de seta:** só depois de confirmar o sentido da linha. No exemplo inspecionado, o z cresce do primeiro ao último ponto. Se o sentido não for confirmado, a seta fica como linha.

**Testes.** Conferir no app; sem teste novo se não houver código de desenho novo.

**Aceite.** typecheck e testes do frontend verdes; marcos legíveis no zoom de uma torre.

### I2b — Cor por atributo (`color_by`)

**Depende de.** I2a.

**Objetivo.** "Pinte os apartamentos por tipologia" colore o canvas por grupo.

**Arquivos.** `ui_tools.py`, `src/cad/model.py` (`prims_payload`), `web/src/api/client.ts`, `web/src/api/types.ts`, `web/src/App.tsx`, `web/src/viewer/CadCanvas.tsx`, os testes de tools, os do frontend e a gravação do stream, mais os da regra de tool nova (1.1).

**Como fazer.**

1. `prims_payload` acrescenta `label` (o rótulo) e `family` a cada entidade, para o frontend agrupar sem nova chamada.
2. Tool de interface `color_by(attribute: Literal["tipologia", "familia", "tipo", "nenhum"])`:
   - no servidor, valida e devolve quantos grupos há;
   - no frontend, `applyUiTool` agrupa pelo campo, atribui cores de uma paleta fixa na ordem alfabética dos grupos e desenha uma legenda no canto;
   - `"nenhum"` volta às cores originais.
3. **Desvio do cartão:** a cor por veredito de C3 sai, porque `highlight_entities` com `torres_que_nao_atendem` já mostra isso.

**Testes.**

- `test_tools.py`: `color_by` valida o atributo.
- `client.test.ts`: o despacho de `color_by` a partir de um `ToolCallStarted`.

**Aceite.** backend e frontend verdes; o efeito aparece no app durante a resposta.

### S3 — Cota do terreno sob a torre (spike)

**Objetivo.** Decidir se e como o mesh entra no `CadModel`. O resultado é um relatório, sem código de produção.

**Perguntas a responder (script em `uv run python -I`):**

1. **Malha:** qual delas responde "terreno original" e qual responde "terreno novo"? Há `AQG_TOPOGRAFIA_NOVA` em várias peças por arquivo, `AQG_TOPOGRAFIA_ORIGINAL`, `AQG_TOPOGRAFIA` e `topografia`.
2. **Faces:** qual o formato de `cad.faces` (índices de vértice, base 0 ou 1)?
3. **Interpolação:** cota num ponto por coordenadas baricêntricas no triângulo que contém o ponto.
   - Validar contra os marcos de S2: o z de cada marco deve bater com a malha nova no mesmo ponto.
   - Reportar o maior erro.
4. **Custo:** memória e tempo de carga no arquivo de 18 MB, e o tempo de uma consulta por varredura linear das faces.
5. **Lugar no modelo:** uma estrutura à parte em `CadModel` (por exemplo, uma lista de malhas com vértices e faces), nunca uma quarta primitiva.

**Entrega.** Relatório curto com os números e uma recomendação (fazer, adiar ou descartar). Se for fazer, vira um cartão novo no PRD com a forma mínima.

## 6. Avaliação final

Ao fim da onda 3:

1. `make eval` e o `--files` do `6abab05295f4…`.
2. A tabela de rodadas e os casos cobertos atualizados no `CAPABILITIES.md`.
3. Repassar com o desenvolvedor os casos `revisar` e qualquer número sem procedência.
4. Conferir que todos os cartões implementados estão `aprovado` no PRD e que o `CAPABILITIES.md` descreve o que o assistente faz depois deles.
