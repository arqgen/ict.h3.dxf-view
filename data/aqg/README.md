# Catálogo de AQGs de teste

Os arquivos `.json` e o `viewer.html` não são versionados (ver `.gitignore`) — ficam apenas localmente em `data/aqg/`. Um clone novo traz este catálogo, mas não os arquivos.

## O que é um AQG

JSON de um *Project* exportado pela Arqgen: um terreno (`site`) e uma solução de implantação gerada sobre ele (`solution`). Unidade: metros. Todos os arquivos têm as mesmas chaves de topo:

| chave | conteúdo |
|--|--|
| `site.elements` | geometria do terreno: perímetro, offset, frente/fundos, acesso, APP, curvas de nível, topografia (`CadMesh`). Cada item tem `cad.layer` (`AQG_*`), `cad.type` e `cad.geometry` em GeoJSON |
| `site.inputs` | parâmetros urbanísticos exigidos (CA, TO, permeabilidade, gabarito, recuos) |
| `site.processed_info` | área do terreno e área útil |
| `site.base_position` | origem do terreno em coordenadas absolutas (UTM); a geometria é local |
| `families` | definições reutilizáveis (torre, vaga, portaria, áreas de lazer), identificadas por `class_path`. A geometria está em `volume[]` (polígonos com `class_path` e `height`) e `drawing_elements[]`; `properties` traz os dados de projeto (pavimentos, tipologias, áreas) |
| `solution.placed_objects` | instâncias: `PlacedFamily` (família posicionada), `PlacedElement` (viário, taludes, muros, topografia nova) e `PlacedAuxiliaryArea` (área de lazer) |
| `solution.outputs` | indicadores calculados da solução (CA/TO projetados, unidades, vagas, áreas, descritivo de torres…) |
| `archprog` | programa arquitetônico pedido (proporção de tipologias, alturas, estratégia de torres) |

### Regras que não são óbvias

- **Instanciação:** uma `PlacedFamily` referencia a família cujo `class_path` é prefixo do seu `hid`. Posição: `mundo = R(angle) · local + (x, y)`, com `angle` em graus, anti-horário.
- **Identidade:** nem `hid` nem `(hid, index)` são únicos dentro de um arquivo — só a posição em `placed_objects` identifica uma instância.
- **`road_network`** pode vir `null`; o viário aparece como `PlacedElement` no layer `AQG_RUA`.
- **`families[].blocks`** referenciam blocos externos (ex.: `AQG_1Q`) que não vêm no arquivo.

## Coleções

| pasta | nome do arquivo | conteúdo |
|--|--|--|
| `favoritadas/` | `<site_id>_<solution_id>.json` | 9 soluções marcadas como favoritas |
| `avaliadas/<site_id>/` | `<ruim\|bom\|otimo>_<solution_id>.json` | 5 terrenos, cada um com três soluções classificadas por qualidade |

Versões do exportador presentes: 7.0.2 a 18.0.0 (maioria 18.0.0).

## `viewer.html`

Visualizador de referência (React + Three.js, bundle único). Abra no navegador e arraste um `.json`: planta e 3D, com terreno. A função que converte o AQG em cena define quais partes de cada família são desenhadas e com qual material — é a referência de como interpretar `volume[].class_path`.
