# CLAUDE.md — `src/cad/`

O motor de informação. Lê o DXF, achata a geometria e mantém o índice consultável. **Não desenha e não sabe o que é IA** — nenhum import de FastAPI, agno ou objeto HTTP entra aqui.

Este módulo é a única fonte de verdade sobre "o que existe no desenho". O payload de render do frontend e as respostas das tools do agente derivam os dois daqui, e é isso que garante que o id que a IA cita é o id que o canvas destaca.

## Mapa

| Arquivo | Papel |
| --- | --- |
| `geometry.py` | Os tipos `Prim` e as medidas: bbox, comprimento, área, hit-test |
| `loader.py` | `load_dxf(bytes)` — leitura, com fallback de recuperação |
| `model.py` | `build_model()`, `describe_model()`, `prims_payload()`, `entity_raw_props()` |

## A Abstração Central

Cerca de 15 tipos de entidade DXF colapsam em três primitivas:

```python
Prim = PolylinePrim(pts, closed) | PointPrim(p) | TextPrim(p, text, height, rotation)
```

Por causa disso, bbox, comprimento, área, hit-test e geometria de destaque derivam de um lugar só, sem `match` por tipo de entidade espalhado pelo código. **Ao adicionar suporte a um tipo DXF novo, mapeie-o para uma dessas três primitivas — não crie uma quarta.**

`PolylinePrim.pts` de uma primitiva fechada **não repete o primeiro ponto no fim**: o segmento de fechamento é implícito. `ezdxf` devolve a duplicata e `normalize_closed()` a remove — mantê-la contaria o fechamento duas vezes no comprimento e distorceria a área.

## Divisão de Trabalho com o ezdxf

Nunca reimplemente o que a biblioteca já faz:

| Precisa de | Use | Não escreva |
| --- | --- | --- |
| INSERT aninhado, arrays MINSERT, DIMENSION, LEADER, MLINE | `recursive_decompose` | transformações afins próprias |
| Arco, círculo, elipse, bulge → arco, SPLINE | `make_path(e).flattening(dist)` | amostragem ou De Boor |
| BYLAYER / BYBLOCK / true_color → `#RRGGBB` | `RenderContext.resolve_all(e)` | tabela ACI própria |
| Escapes de formatação de MTEXT | `mtext.plain_text()` | limpador de `\P`, `\f`, `{}` |
| Encoding legado (cp1252) | `ezdxf.read` / `readfile` | detecção própria |
| Ordem de vértices de SOLID (0,1,3,2) | já vem correta do decompose | reordenação manual |

## Armadilhas Verificadas

Todas falham em silêncio — nenhuma levanta erro.

1. **`insert.virtual_entities()` não expande arrays MINSERT.** Devolveu 2 de 12 num array 3×2. Use sempre `recursive_decompose`.
2. **`$EXTMIN`/`$EXTMAX` vêm com sentinelas ±1e20** em documentos novos. Calcule a bbox das primitivas; não leia do cabeçalho.
3. **Sub-entidades da decomposição têm `handle = None`.** Só o handle da entidade de topo do modelspace é id, e é o único que o LLM vê.
4. **`make_path` levanta `TypeError` para TEXT, MTEXT, ATTRIB, INSERT e POINT.** Esses cinco são tratados explicitamente em `_prims_of`.
5. **`DXFNamespace.get(key, default)` levanta `DXFAttributeError`** quando a chave não existe *no tipo* — não devolve o default. Escolha a chave pelo tipo (`char_height` em MTEXT, `height` em TEXT), não tente as duas.
6. **`import ezdxf.addons.drawing.properties` puxa `PIL`.** Por isso `pillow` é dependência do projeto.
7. **Unidades de ângulo são inconsistentes no próprio DXF:** `ARC.start/end_angle` em graus, `ELLIPSE` em parâmetro, `INSERT.rotation` e `TEXT.rotation` em graus.

## `describe_model()`

O texto que vai ao system prompt. Fora das tools, é a **única** visão que o modelo tem do desenho. Ele lista o que existe (contagens, layers, blocos, extensão) e nada mais: não afirma medida que só uma tool poderia calcular. Se você acrescentar uma medida aqui, terá criado um caminho para o modelo citar número sem tool call — exatamente o que o projeto proíbe.

## Avisos

Problema de parse vira aviso em `model.warnings`, não exceção: um DXF com um bloco faltando ainda tem 99% do desenho utilizável. Os avisos são deduplicados com teto de 20 e aparecem no resumo do modelo e no painel de Info.
