# CLAUDE.md — `src/cad/`

O motor de informação. Lê o AQG (o JSON de *Project* da Arqgen), achata a geometria e mantém o índice consultável. **Não desenha e não sabe o que é IA** — nenhum import de FastAPI, agno ou objeto HTTP entra aqui.

Este módulo é a única fonte de verdade sobre "o que existe no projeto". O payload de render do frontend e as respostas das tools do agente derivam os dois daqui, e é isso que garante que o id que a IA cita é o id que o canvas destaca.

Formato do AQG: [`data/aqg/README.md`](../../data/aqg/README.md). Requisitos e decisões: [`PRD.md`](../../PRD.md).

## Mapa

| Arquivo | Papel |
| --- | --- |
| `geometry.py` | Os tipos `Prim` e as medidas: bbox, comprimento, área, hit-test |
| `model.py` | `load_aqg()` (bytes → `CadModel`, ou `AqgLoadError`), `build_model()`, `describe_model()`, `prims_payload()`, `tower_units()` (unidades por pavimento e da torre, das `properties` da família) e os tipos `CadEntity`, `CadInstance`, `CadFamily`, `CadLayer`, `CadModel` |

## A Abstração Central

Toda geometria colapsa em três primitivas:

```python
Prim = PolylinePrim(pts, closed) | PointPrim(p) | TextPrim(p, text, height, rotation)
```

Por causa disso, bbox, comprimento, área, hit-test e geometria de destaque derivam de um lugar só. **Ao suportar um tipo de geometria novo, mapeie-o para uma dessas três primitivas — não crie uma quarta.** Cada anel ou linha GeoJSON vira um `PolylinePrim`; `Point` vira `PointPrim`. O AQG não tem texto livre: `TextPrim` só é produzido no rótulo do marco de cota (valor com 2 casas, altura `ELEVATION_TEXT_HEIGHT`).

`PolylinePrim.pts` de uma primitiva fechada **não repete o primeiro ponto no fim**: o segmento de fechamento é implícito. Os anéis GeoJSON repetem e `normalize_closed()` remove — mantê-lo contaria o fechamento duas vezes no comprimento e distorceria a área.

## Regras do AQG

- **Ids opacos por posição:** `s<i>` para `site.elements[i]`; `p<i>` para `placed_objects[i]` (instância, se `PlacedFamily`; entidade, se `PlacedElement`/`PlacedAuxiliaryArea`); `p<i>.<j>` para a parte `volume[j]` da instância; `a<i>` para `solution.annotations[i]` (marco de cota: layer `AQG_COTA`, type `cota`, `PointPrim` + `TextPrim`; seta de declive: layer `AQG_SETA_DECLIVE`, type `seta_declive`, classe `gentle`/`steep` no rótulo e `value` fora por não ter unidade conhecida). `i` e `j` são contados **antes** de qualquer exclusão, então uma parte excluída deixa buraco na numeração. O id é opaco de propósito: um id legível como `torre-03` faria o modelo confundir a torre desenhada com a torre 03 dos indicadores.
- **Instância não é entidade.** `p<i>` de uma `PlacedFamily` vive em `model.instances`, não em `by_id`; as partes é que são entidades. As tools e o frontend expandem `p<i>` nas partes.
- **Casamento de família nos dois sentidos:** a família é a primeira de `families[]` em que `hid` e `class_path` são prefixo (por segmento) um do outro. Em 6 arquivos, 1.427 vagas têm `hid` = `/equipment/vaga/simples/front_access` e a família é `.../front_access/P/0` — a regra num sentido só as perderia. Instância sem família vira aviso e fica fora do índice.
- **Rotação anti-horária, verificada:** `x' = x + px·cos θ − py·sin θ`, `y' = y + px·sin θ + py·cos θ`. Com ela, todo `/core` do acervo cai dentro do `AQG_PERIMETRO`; com a horária, não. `site.elements` e `PlacedElement` já vêm em coordenadas do terreno.
- **Partes desenhadas** seguem o `viewer.html` de referência (tabela `_TOWER_PARTS` e `_part_spec` em `model.py`): torre sem `/reference`, `/road_access` e `/access`; vaga e portaria só `/core` exato; demais famílias sem `/reference`, `/road_access`, `/access`, `/road_network` e `/core/zito`. `drawing_elements[]` é ignorado. `CadMesh` (topografia) fica de fora sem aviso.
- **Layers do terreno normalizados:** maiúsculas com prefixo `AQG_` (`talude` → `AQG_TALUDE`).
- **Área só de `Polygon`/`MultiPolygon`:** Σ (externo − furos). `LinearRing` (curva de nível fechada) é `closed` mas sem área.
- **Label de família:** `strip()`; vazio cai no último segmento do `class_path`; só dígitos vira `"<type> <label>"` (`"0"` → `"Vaga 0"`).

## Armadilhas Verificadas

Verificadas nos 24 AQGs locais; todas falham em silêncio.

1. **Nem `hid` nem `(hid, index)` são únicos** num arquivo — só a posição em `placed_objects` identifica.
2. **A ordem dos `DescritivoTorre` não segue `placed_objects`** (difere em 6 arquivos, sem ordenação que explique). Nunca vincule descritivo a uma instância só: `descriptor_groups()` vincula cada descritivo ao **grupo** de instâncias da família de torre com as mesmas unidades (`tower_units`), e deixa de fora a linha `TOTAL` e o descritivo ambíguo.
3. **Os apartamentos desenhados são por pavimento**, não o total de unidades.
4. **Layers `talude` e `topografia` vêm em minúsculas e sem `AQG_`.**
5. **Furos existem:** 12 taludes (em `MultiPolygon`) e 1 `AQG_RUA`. `_area_of` ingênuo somaria os anéis.
6. **`road_network` pode vir `null`.** O parser é tolerante: o que não reconhece vira aviso.
7. **Label de família duplicado:** famílias diferentes podem ter o mesmo label normalizado (caso real: `I/15`, 1 de 24 arquivos). Por isso a instância guarda `family_index`, a posição em `model.families`: tudo que precisa das `properties` usa `model.families[inst.family_index]`, nunca uma busca pelo label. A contagem por família agrupa pelo label e soma as duas.

## `describe_model()`

O texto que vai ao system prompt. Fora das tools, é a **única** visão que o modelo tem do projeto. Ele lista **o que existe** — layers, famílias instanciadas, tipos de indicador disponíveis, formato dos ids, avisos — **sem contagens, medidas, extensão nem valores de indicador**. Qualquer número aqui seria um caminho para o modelo citar quantidade sem tool call, exatamente o que o projeto proíbe. Há teste garantindo isso.

## Avisos

Problema de dado vira aviso em `model.warnings`, não exceção: um AQG com uma instância sem família ainda tem o resto utilizável. Os avisos são deduplicados com teto de 20 e aparecem no resumo do modelo e no painel de Info.
