# PRD — Novas tools e funcionalidades AQG

> Status: **implementado**, exceto o spike S3. Guia de construção em [`IMPLEMENTATION-tools.md`](IMPLEMENTATION-tools.md). Base: [`CAPABILITIES.md`](CAPABILITIES.md) e os 24 AQGs locais de `data/aqg/`.

## Objetivo

Ampliar o que o assistente responde sobre terreno e torres sem quebrar a regra central: **todo número afirmado vem de uma tool**. Quando uma resposta exige conta, a conta fica na tool, e o modelo só cita o resultado.

Este PRD é um catálogo: cada ideia é um cartão independente, decidido um a um. Um cartão aprovado vira uma task própria.

## Como ler um cartão

| Campo | Conteúdo |
| --- | --- |
| Perguntas | O que o usuário pergunta |
| Fonte | De onde vem o dado no AQG, com cobertura no acervo (arquivos com o dado / 24) |
| A tool calcula | A conta que sai do modelo e passa para a tool |
| No desenho | O que destaca, isola ou enquadra |
| Risco | Onde o modelo poderia afirmar número sem tool |
| Forma mínima | Estender uma tool existente antes de criar uma nova |
| Aberto | O que falta decidir ou verificar |
| Eval | Caso novo para `CASES` em `evals/agent_eval.py` |
| Decisão | pendente / aprovado / adiado |

Toda cobertura citada foi medida por script nos 24 arquivos.

## Dado no AQG × uso hoje

| Dado | Cobertura | Uso hoje |
| --- | --- | --- |
| `solution.outputs` (CA, TO, permeabilidade, unidades, áreas, `DescritivoTorre`, `MovimentoDeTerra`…) | 24 | Lido cru por `get_project_indicators` |
| `site.inputs` (CA, TO e permeabilidade exigidos, recuos, afastamento, gabarito) | 24 | Lido cru; `compare_indicators` só lê `value` numérico |
| Propriedades da família de torre (`tipologias` por pavimento, `n_pavimentos_unidades`, alturas, elevadores) | 24 | Devolvidas cruas por `get_entity_details` |
| `archprog` (programa pedido) | 24 | Fora; só o resumo `ArchprogProcessado` (17) sai nos indicadores |
| `solution.annotations` (marcos de cota, setas de declive) | 17 | Fora |
| `site.analysis` (inclinação média e faixas) | 15 | Fora |
| Topografia em mesh (`CadMesh`: vértices x, y, z e faces triangulares) | 17 | Fora |
| Linhas do terreno: `AQG_FRENTE` (24), `AQG_FUNDOS` (10), `AQG_OFFSET` (24) | — | Desenhadas e consultáveis, sem regra associada |
| `AfastamentoProjetado` (`entre_blocos`, `lateral`) e `DescritivoTorre.afastamento` | 24 | Lidos crus, sem rota no `instructions.md` |
| `DescritivoTorreTotal` (área construída e computável somadas) | 23 | Lido cru; é um segundo total, além da linha `TOTAL` dos `DescritivoTorre` |
| `GabaritoNaoAfastado` (altura até a qual não se exige afastamento) | 9 | Lido cru |
| `InputsProcessados` (recuos e fórmula como texto: `"3,0m"`, `"(h-6)/10"`) | 19 | Lido cru |

## Pré-requisito

### F0 — Família da instância pela posição

- **Hoje:** a instância guarda só o label da família, e `get_entity_details` pega as propriedades da primeira família com esse label (`_instance_info` em `query_tools.py`).
- **Problema:** no arquivo com duas famílias `I/15` (1 de 24), elas têm 9 e 10 pavimentos com unidades. A torre da segunda família recebe as propriedades da primeira e sai com 9 pavimentos. Somar as unidades das torres pelo label dá 400, e `TotalDeUnidades` é 415. Pela família certa, a soma fecha em 24/24.
- **Forma mínima:** `CadInstance` guarda o índice da família em `families` (`build_model` já o conhece ao chamar `_place_family`), e `_instance_info` usa o índice.
- **Risco:** nenhum para a regra central. A contagem por família continua agrupando pelo label.
- **Eval:** teste de parser, sem LLM: no arquivo `I/15`, a soma das unidades das torres é igual a `TotalDeUnidades`.
- **Decisão:** aprovado e implementado (26/10/2026).

## Torres

### T1 — Ficha da torre

- **Perguntas:** "Quantas unidades tem a torre p3?", "Quantos apartamentos por andar?", "Quantos pavimentos com unidades?"
- **Fonte:** propriedades da família da instância: `tipologias` por pavimento (em `pav_tipo` na família `Tower`, 23 arquivos; no topo em `DynamicTower3d`, 1 arquivo) e `n_pavimentos_unidades`. Σ(tipologias) × `n_pavimentos_unidades`, somado nas torres desenhadas, é igual a `TotalDeUnidades` em **24/24**, com a família resolvida pela posição (F0).
- **A tool calcula:** `unidades_por_pavimento` e `unidades_da_torre`.
- **No desenho:** a instância `p<i>` inteira.
- **Risco:** baixo depois do F0, porque a conta está validada contra o indicador oficial em todo o acervo. Sem o F0, o arquivo com duas famílias `I/15` soma 400 unidades, e o oficial é 415.
- **Depende de:** F0.
- **Forma mínima:** dois campos a mais em `get_entity_details` com id de instância de torre.
- **Aberto:** altura e área construída por torre só saem do `DescritivoTorre`, o que depende de T3.
- **Eval:** "Quantas unidades tem cada torre?" → soma igual a `TotalDeUnidades`.
- **Decisão:** aprovado e implementado (26/10/2026): `unidades_por_pavimento` e `unidades_da_torre` em `get_entity_details`.

### T2 — Unidades por família

- **Perguntas:** "Quantas unidades há em cada tipo de torre?", "Qual família concentra mais unidades?"
- **Fonte:** a mesma de T1.
- **A tool calcula:** unidades por família (instâncias × unidades da torre) e o total.
- **No desenho:** as instâncias de cada família.
- **Risco:** o modelo somar os totais das famílias por conta própria. A tool devolve o total pronto.
- **Forma mínima:** campo `unidades` por grupo em `count_entities(group_by="family")`.
- **Eval:** "Quantas unidades há em cada família de torre?"
- **Depende de:** F0.
- **Decisão:** aprovado e implementado (26/10/2026): `unidades_por_familia`, `unidades_por_torre` e `total_unidades` em `count_entities(group_by="family")`.

### T3 — Vínculo descritivo ↔ grupo de torres

- **Perguntas:** "Qual é a torre 02?", "Qual a altura da torre p3?", "Qual a área construída desta torre?"
- **Fonte:** `DescritivoTorre` (24). Toda lista de descritivos tem uma linha `label: "TOTAL"`. Sem ela, o multiconjunto de `unidades` dos descritivos é igual ao das torres desenhadas (T1), e as unidades são distintas entre famílias, em **24/24**. Em 16 arquivos todas as torres são da mesma família e todos os descritivos são iguais.
- **A tool calcula:** o casamento descritivo → família de torre, pelas unidades.
- **No desenho:** todas as instâncias da família casada.
- **Risco:** o vínculo é com o **grupo** de torres idênticas, não com uma instância. A tool diz isso de forma explícita ("a torre 02 é uma das 3 torres da família X: p0, p4, p9"). Dentro do grupo, nenhum número do descritivo difere.
- **Forma mínima:** `get_entity_details` de torre devolve o descritivo casado; `get_project_indicators` marca a linha TOTAL.
- **Aberto:** **muda uma decisão vigente** ("nunca vincule descritivo a instância", em `PRD.md`, `src/cad/CLAUDE.md`, `instructions.md` e no caso `vinculo` do eval). Vale confirmar a regra com o time do exportador, mas o vínculo por grupo não depende dela.
- **Eval:** "Qual a altura da torre `p<i>`?" → `DescritivoTorre.altura` da família casada. O caso `vinculo` muda de "recusa" para "aponta o grupo".
- **Depende de:** F0, porque o casamento usa as unidades de T1.
- **Decisão:** aprovado e implementado (26/10/2026): vínculo com o grupo de torres idênticas, revogando "nunca vincule descritivo a instância" (o vínculo com uma instância só continua proibido).

## Conformidade urbanística

### C1 — Veredito por índice

- **Perguntas:** "O projeto está dentro dos índices?", "A permeabilidade atende?", "O gabarito está ok?"
- **Fonte (24/24 em todas):** CA (`CAProjetado` ≤ `CAMaximoExigido`), TO (`TOProjetada` ≤ `TOExigida`), permeabilidade (`PermeabilidadeProjetada` ≥ `PermeabilidadeExigida`) e gabarito (`GabaritoProjetado` ≤ `GabaritoMaximoExigido.altura`).
- **A tool calcula:** valor, limite, direção (máximo ou mínimo), veredito, folga e percentual de cada regra.
- **No desenho:** nada.
- **Risco:** hoje é o modelo quem escolhe os pares de `compare_indicators`, e a tool tem dois problemas:
  - trata todo limite como máximo, então na permeabilidade a folga sai com sinal invertido e o "percentual usado" engana;
  - lê só `value`, e `GabaritoMaximoExigido` traz o número em `altura` e não tem `value` em nenhum dos 24, então o gabarito nunca é comparado;
  - caso real: no `favoritadas/6abab05295f4…`, a permeabilidade projetada é 19,99 e a exigida 20. A tool devolve folga +0,01 e 99,95% "usado", o que se lê como "atende", e o projeto não atende. Os outros 23 arquivos atendem as 4 regras.
- **Forma mínima:** tool `check_zoning()` com as regras fixas no código, e `compare_indicators` passa a respeitar a direção.
- **Eval:** "O projeto atende CA, TO, permeabilidade e gabarito?" → 4 vereditos. O padrão do eval roda só os `otimo_*` de `avaliadas/`, que atendem tudo, então o caso roda também no `6abab05295f4…` com `--files`.
- **Decisão:** aprovado e implementado (26/10/2026): `check_zoning`, veredito estrito.

### C2 — Distância borda a borda

- **Perguntas:** "Qual a distância entre as torres p0 e p1?", "Quão perto da frente está a torre p3?"
- **Fonte:** geometria já indexada.
- **A tool calcula:** a menor distância entre dois conjuntos de polígonos ou linhas. Hoje `measure` só mede entre centros, o que não serve para recuo nem afastamento.
- **No desenho:** as duas entidades.
- **Risco:** o modelo citar distância entre centros como se fosse afastamento. A tool tem de dizer qual distância mediu.
- **Forma mínima:** novo modo em `measure` (pré-requisito de C3).
- **Eval:** "Qual a menor distância entre as torres `p<i>` e `p<j>`?"
- **Decisão:** aprovado e implementado (26/10/2026): `measure(metric="edge_distance")`, torre medida pelo pavimento-tipo.

### C3 — Recuos e afastamento entre torres

- **Perguntas:** "As torres respeitam os recuos?", "O afastamento entre as torres atende?", "Quais torres estão fora?"
- **Fonte:**
  - recuos: `RecuoFrontal` (20), `RecuoLateral` (17), `RecuoFundos` (14);
  - afastamento: `AfastamentoAeracao` traz número em 9 arquivos e a fórmula `(h-6)/10` em 11, mas o exportador já a aplica. `DescritivoTorre.afastamento` dá o afastamento exigido de cada torre (24; ex.: (31,8 − 6)/10 = 2,58). `AfastamentoProjetado` (24) dá `lateral`, igual a esse afastamento, e `entre_blocos`, igual ao dobro (diferença só de arredondamento). `GabaritoNaoAfastado` (9) é a altura até a qual o afastamento não se aplica;
  - linhas do terreno: `AQG_FRENTE` (24), `AQG_FUNDOS` (10), `AQG_OFFSET` (24);
  - envelope de afastamento por torre: a parte `/afastamento`, já desenhada.
- **A tool calcula:** a distância de cada torre à frente, aos fundos e ao perímetro, e a distância entre cada par de torres, contra o exigido. Devolve um veredito por torre e os ids que não atendem.
- **No desenho:** destaca as torres que não atendem.
- **Risco:** interpretar errado a regra municipal. A tool só verifica o que o arquivo declara.
- **Forma mínima:** tool `check_setbacks()` sobre C2, que compara a distância entre torres com `entre_blocos` e a distância de cada torre às linhas do terreno com os recuos. Não avalia fórmula nem depende do vínculo de T3.
- **Aberto:**
  - qual polígono é a pegada da torre (`/building_pad`, a união do `pav_tipo` ou outro);
  - se `AQG_OFFSET` já é a linha de recuo; se for, a verificação vira "a torre cabe no offset";
  - se `entre_blocos`, um valor só por arquivo, é a regra que o gerador aplica a todo par de torres, inclusive entre torres de alturas diferentes.
- **Eval:** "Alguma torre viola o recuo frontal?"
- **Decisão:** aprovado e implementado (26/10/2026): `check_setbacks`. O `AQG_OFFSET` é a linha de recuo (distância à frente = `RecuoFrontal` e ao perímetro = menor entre lateral e fundos, em todo arquivo com recuo), então o recuo vira "o pavimento-tipo cabe no offset"; `entre_blocos` vale para todo par de torres.

## Terreno e topografia

### S1 — Ficha do terreno

- **Perguntas:** "Qual a inclinação do terreno?", "Quanto de corte e aterro?", "Qual a cota de referência?", "Qual o zoneamento?"
- **Fonte:**
  - `site.analysis.avg_inclination` (15);
  - `MovimentoDeTerra`: corte, aterro, balanço e muro (17);
  - `DetalhamentoMovimentoDeTerra` (15);
  - `CotaTopografia` (15), `Zoneamento` (13), `Municipio` (15), `Datum` (9).
- **A tool calcula:** nada. Os valores já vêm prontos.
- **No desenho:** isola os layers de talude (17), muro de arrimo (9) e crista (17).
- **Risco:** baixo. Quase tudo isso já sai por `get_project_indicators`, mas o `instructions.md` não roteia essas perguntas, e `site.analysis` não é exposto.
- **Forma mínima:** a inclinação média entra no grupo `terreno` de `get_project_indicators` (sem os índices de face), mais uma rota no `instructions.md`.
- **Eval:** "Quanto de corte e aterro o projeto prevê?" → `MovimentoDeTerra`.
- **Decisão:** aprovado e implementado (26/10/2026).

### S2 — Cotas de nível

- **Perguntas:** "Qual a cota perto da torre p3?", "Onde fica o ponto mais alto marcado?"
- **Fonte:** `solution.annotations` (17): 323 marcos de cota com valor e posição, além de setas de declive.
- **A tool calcula:** o marco mais próximo de uma entidade e o maior ou menor marco.
- **No desenho:** destaca os marcos.
- **Risco:** confundir a cota do marco com a cota sob a torre (que é S3).
- **Forma mínima:** indexar os marcos como entidades num layer próprio, com a cota no rótulo e `TextPrim` (que existe e hoje não é usado). Com isso, `query_entities` por região e layer já responde.
- **Eval:** "Qual a cota marcada mais alta?"
- **Decisão:** aprovado e implementado (26/10/2026): setas só como desenho, com a classe no rótulo e o `value` fora.

### S3 — Cota do terreno sob a torre (spike)

- **Perguntas:** "Qual o desnível sob a torre p3?", "Quanto o terreno novo difere do original aqui?"
- **Fonte:** `CadMesh` (17), com vértices x, y, z e faces triangulares. Há `AQG_TOPOGRAFIA_ORIGINAL` no terreno e `AQG_TOPOGRAFIA_NOVA` no projeto.
- **A tool calcula:** a cota num ponto, por interpolação no triângulo, e o desnível de uma pegada.
- **No desenho:** a torre.
- **Risco:** o índice é 2D, e o mesh não vira `Prim` (é proibido criar uma quarta primitiva). Teria de entrar como estrutura à parte no `CadModel`.
- **Aberto:** onde o mesh vive no modelo, o custo de memória em arquivos de até 18 MB e a cobertura de cada tipo de mesh.
- **Resultado do spike (26/10/2026, nos 24 AQGs):**
  - faces são índices de vértice em base 0;
  - interpolando no triângulo, os marcos de cota batem com `AQG_TOPOGRAFIA_NOVA` (234 marcos, erro máximo 0,13 m, mediana 0) — ela é o terreno novo, mas não cobre 63 marcos (só envolve parte do terreno);
  - `AQG_TOPOGRAFIA_ORIGINAL` difere dos marcos (mediana 0,05 m, máximo 0,71 m), coerente com terreno original;
  - `AQG_TOPOGRAFIA` bate na mediana, mas tem erro de até 21,9 m em algum arquivo: o papel dela ainda não está claro;
  - custo baixo: no arquivo de 17,7 MB (31,6 mil faces) o JSON e as malhas carregam em 0,22 s com pico de 71 MB, e a varredura linear de uma consulta leva 9 ms no pior caso.
  - Recomendação: fazer, com as malhas numa estrutura à parte no `CadModel` (por layer: vértices e faces) e uma tool de cota num ponto ou sob uma pegada. Antes, entender o `AQG_TOPOGRAFIA` e o que cobre a área fora do `AQG_TOPOGRAFIA_NOVA`.
- **Decisão:** pendente.

## Programa pedido × projetado

### P1 — Comparação com o `archprog`

- **Perguntas:** "O projeto cumpre o programa pedido?", "A proporção de tipologias bate?", "Ficou dentro da faixa de pavimentos?"
- **Fonte (pedido → projetado):**

  | Pedido (`archprog`) | Projetado | Arquivos com o pedido |
  | --- | --- | --- |
  | `CAMin` | `CAProjetado` | 24 |
  | `MaxHeight` | `GabaritoProjetado` | 24 |
  | `MinPavimentos` / `MaxPavimentos` | `NumeroDePavimentos` | 16 / 11 |
  | `MinUnitsPerFloor` / `MaxUnitsPerFloor` | unidades por pavimento (T1) | 12 |
  | `MinTowersBySite` / `MaxTowersBySite` | `TotalDeTorres` | 8 / 6 |
  | `ParkingLotPerUnit` | `VagasPorUnidade` | 15 |
  | `FamilyProportion` | `UnidadesPorTipologia` | 18 |

- **A tool calcula:** um veredito por regra presente no arquivo. A regra ausente volta como "não pedido", nunca como falha.
- **No desenho:** nada, ou as torres fora da faixa de unidades por pavimento.
- **Risco:** casar a tipologia pedida (`hid` da família de apartamento) com a chave de `UnidadesPorTipologia` (`class_path` da área). Os formatos diferem, e o casamento não foi verificado.
- **Forma mínima:** tool `compare_program()`.
- **Aberto:** a regra de casamento de tipologias. `NumeroDePavimentos` vem como texto em 1 arquivo.
- **Eval:** "O número de pavimentos está dentro do pedido?"
- **Decisão:** aprovado e implementado (26/10/2026): `compare_program`. CA mínimo, proporção de tipologias e vagas por unidade são meta (só a diferença); o `CAMin` fica acima do CA projetado em 8 de 24 arquivos.

## Interação no canvas

### I1 — Perguntar sobre a seleção

- **Hoje:** o clique no canvas seleciona e mostra o detalhe no painel lateral (`App.tsx` → `SidePanel`), mas o chat não sabe o que está selecionado.
- **Proposta:** um botão "perguntar sobre isto" que leva o id selecionado para a mensagem ("o que é isto?" passa a funcionar).
- **Forma mínima:** prefixar o id na mensagem, sem mudar o contrato da API. Mandar um campo `selected_id` no `ChatRequest` é a alternativa.
- **Risco:** nenhum para a regra central, porque o modelo continua precisando de tool para qualquer número.
- **Decisão:** aprovado e implementado (26/10/2026).

### I2 — Preenchimento e cor por atributo

- **Hoje:** o canvas desenha só contorno.
- **Proposta:**
  - preencher os polígonos;
  - nova tool de interface `color_by` (tipologia, família ou veredito de C3), aplicada pelo frontend ao ler o `ToolCallStarted`, como as outras quatro.
- **Forma mínima:** primeiro o preenchimento (só canvas); a tool de interface vem depois. Ela exige atualizar junto `UI_TOOL_NAMES`, `UI_TOOLS` e `applyUiTool`.
- **Decisão:** aprovado e implementado (26/10/2026): preenchimento e `color_by` (tipologia, família, tipo). A cor por veredito de C3 saiu: `highlight_entities` com `torres_que_nao_atendem` já mostra isso.

### I3 — Cotas e setas desenhadas

- **Proposta:** desenhar os marcos de cota e as setas de declive de S2.
- **Depende de:** S2.
- **Decisão:** aprovado e implementado (26/10/2026): só as cores dos layers `AQG_COTA` e `AQG_SETA_DECLIVE`; a seta fica como linha, sem ponta, até o sentido ser confirmado.

## Ajustes pequenos

### Q1 — Famílias só sem filtro em `get_project_indicators`

- **Hoje:** a tool anexa as propriedades de todas as famílias em toda chamada, mesmo com `tipos`. São até ~11,6 mil caracteres por chamada. Na última rodada do eval, as 18 chamadas da tool vieram filtradas e todas levaram esse peso.
- **Forma mínima:** anexar `familias` só quando `tipos` vier vazio. As propriedades de uma torre continuam em `get_entity_details`.
- **Risco:** nenhum para a regra central.
- **Decisão:** aprovado e implementado (26/10/2026).

## Priorização proposta

| Ordem | Cartões | Por quê |
| --- | --- | --- |
| Primeiro | F0, C1, T1 + T2, S1, Q1 | Esforço pequeno e dado com 24/24 ou já exposto. F0 corrige um detalhe de torre errado hoje e destrava T1, T2 e T3. C1 corrige uma resposta errada real (permeabilidade 19,99 × 20) e o gabarito |
| Depois | T3, C2 + C3, P1, S2, I1, I2 | Valor alto, mas com decisão de produto (T3) ou questão aberta (C3, P1) |
| Spike | S3, I3 | Exigem estrutura nova (mesh) ou dependem de S2 |

## Decisões pedidas

- [ ] Decisão de cada cartão (pendente → aprovado/adiado).
- [ ] T3: aceitar o vínculo descritivo ↔ grupo de torres, revogando "nunca vincule".
- [ ] C3: pegada da torre e papel do `AQG_OFFSET`.
- [ ] I1: id na mensagem ou campo novo no `ChatRequest`.

## Fora do escopo

- Comparação entre soluções do mesmo terreno (ruim/bom/ótimo): muda o store e o runner para mais de um documento por chat.
- 3D, blocos externos de `families[].blocks` e escrita de AQG.
