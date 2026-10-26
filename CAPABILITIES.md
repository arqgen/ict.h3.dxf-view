# Assistente AQG — o que faz e o que ainda não faz

26/10/2026 · Gustavo Sarti · versão viva: [Claude Docs](https://claude.ai/artifact/L2xHEQd5obuogY2PyBVprq)

## Visão geral

O assistente responde perguntas sobre um projeto AQG com 13 tools, e todo número que ele afirma vem de uma delas. Ele nunca vê o arquivo: vê um resumo que lista o que existe (layers, famílias, tipos de indicador), sem nenhuma contagem ou medida.

As tools se dividem em 9 de consulta e 4 de ação na planta. As de ação destacam, enquadram e isolam layers no desenho, e o efeito aparece no canvas enquanto o agente responde.

| Id | O que identifica | Exemplo |
| --- | --- | --- |
| `p<i>` | uma instância posicionada (torre, vaga, portaria) ou um elemento posicionado (rua, talude) | `p12` |
| `p<i>.<j>` | uma parte da instância (apartamento, varanda, core, shaft) | `p12.3` |
| `s<i>` | um elemento do terreno (perímetro, frente, curva de nível) | `s0` |

Os ids são opacos de propósito: `p3` não é a "torre 3" dos indicadores.

## O que ainda não faz

Hoje o assistente lê a planta 2D e os indicadores que o exportador gravou. Não analisa o projeto além disso, e recusa o que exigiria inventar um vínculo ou um número.

### Recusa de propósito

| Pedido | Por que recusa | O que destravaria |
| --- | --- | --- |
| "Qual torre desenhada é a torre 02 dos indicadores?" | A ordem dos `DescritivoTorre` não segue a das instâncias desenhadas (difere em 6 de 24 arquivos), e nenhuma ordenação testada explica isso. Associar seria inventar. | O time do exportador informar a regra que liga `order_index` à instância, ou o vínculo por grupo de torres (cartão T3 de [`PRD-tools.md`](PRD-tools.md)) |
| Contar unidades pela planta | Os apartamentos desenhados são os de um pavimento-tipo (por exemplo, 7 numa torre de 35 unidades). | — (unidades vêm dos indicadores) |

O modelo também não faz contas (somas, percentuais, diferenças, contar itens de uma lista). Elas saem prontas de `check_zoning`, `compare_indicators` e dos totais das tools, e qualquer outra conta pede uma tool nova.

### Fica fora do índice

| O que | Efeito para o usuário |
| --- | --- |
| Topografia em mesh (`CadMesh`) | Sem cotas do terreno, sem relevo na planta |
| Anotações (`solution.annotations`: cotas de nível, setas de declive) | Não aparecem nem podem ser consultadas |
| Programa arquitetônico pedido (`archprog`) | Não compara o programa pedido com o projetado. Só o resumo `ArchprogProcessado` (faixas de unidades por pavimento, pavimentos e torres) sai nos indicadores |
| Inclinação do terreno (`site.analysis`) | Sem inclinação média nem faixas de declividade |
| Altura das partes (`volume[].height`) | Altura da torre só pelos indicadores e pelas propriedades da família |
| Georreferência (`site.base_position`, `Datum`) | Sem coordenadas absolutas (UTM) |
| Estratégias do gerador (`solution.strategy`) | Não explica como a solução foi gerada |
| Blocos externos de `families[].blocks` (ex.: `AQG_1Q`) | O interior das unidades não é desenhado |
| 3D e pavimentos além do tipo | Só planta 2D de um pavimento |
| Preenchimento de polígonos no canvas | Desenho só em contorno |
| Comparação entre soluções de um mesmo terreno | Um projeto por vez |
| Escrita de AQG | O assistente só lê |

### Tools de domínio ainda não criadas

O catálogo de candidatas está em [`PRD-tools.md`](PRD-tools.md), em cartões para decidir um a um. Os temas são:

- ficha e unidades por torre;
- vínculo descritivo ↔ torre;
- veredito por índice urbanístico, recuos e afastamento;
- terreno e cotas;
- programa pedido × projetado;
- interação no canvas.

### Limitações conhecidas

- **Famílias com o mesmo nome:** famílias diferentes com o mesmo label (caso real: `I/15`, 1 de 24 arquivos) são somadas na contagem por família. O detalhe de cada torre já usa as propriedades da família dela.
- **Vagas:** nos 15 arquivos com `NumeroDeVagasProjetado`, as vagas desenhadas batem 1:1 com o indicador. Os 9 sem o indicador não têm nenhuma vaga desenhada. Diferente dos apartamentos, vaga pode ser contada na planta (`count_entities(group_by="family")`). 2 dos 5 projetos do eval estão no segundo grupo, e o eval não confere vagas neles.
- **Linha TOTAL nos `DescritivoTorre`:** todo arquivo tem um descritivo `TOTAL`, com a soma das torres, ao lado dos `01`, `02`… O modelo pode tratá-lo como uma torre. Há ainda um indicador à parte, `DescritivoTorreTotal` (23 de 24), com a área construída e a computável somadas.
- **Nota citada como percentual:** se o modelo citar `0,94` como "94%", o eval acusa número sem procedência. Não apareceu na última rodada.
- **Memória e acesso:** o projeto vive em memória, e reiniciar o servidor exige reenviar o arquivo. Não há autenticação nem multiusuário.
- **Envio do arquivo:** o AQG é enviado ao servidor. Se o conteúdo dos projetos for sensível, isso pede revisão antes de expor a aplicação.

### Decisão em aberto

- [ ] Regra que liga `DescritivoTorre.order_index` à instância em `placed_objects` — depende do time do exportador.
  - Achado: pelas unidades da torre, cada descritivo casa com uma família de torre em 24 de 24 arquivos. Sem regra fica só qual instância de um grupo de torres idênticas é a "02", e nenhum número difere entre elas. A proposta está no cartão T3 de [`PRD-tools.md`](PRD-tools.md).

## Indicadores: unidades, áreas e índices

Unidades, áreas construídas e índices saem só destas três tools, porque a planta mostra um pavimento só. Vagas são exceção: as desenhadas batem com o indicador.

| Tool | O que faz | Perguntas que responde |
| --- | --- | --- |
| `get_project_indicators` | Lê os indicadores do exportador sem transformar: projetados (`solution.outputs`), exigidos (`site.inputs`), dados do terreno (`site.processed_info`), notas da solução (`solution.scores`) e as propriedades de cada família. Filtra por tipo de indicador. | "Quantas unidades?", "Qual a área construída?", "Quantas vagas foram projetadas?", "Qual o CA máximo permitido?", "Qual a área do terreno?", "Qual a nota da solução?" |
| `check_zoning` | Compara CA, TO, permeabilidade e gabarito com os limites, cada um no seu sentido (permeabilidade é mínimo; o gabarito usa a `altura` exigida). Devolve por índice se atende, a folga e o percentual do limite, mais os totais `nao_atende` e `atende_todas`. O veredito é estrito: 19,99 contra 20 exigidos não atende. | "O projeto está dentro dos índices?", "A permeabilidade atende?", "Qual a folga da TO?" |
| `compare_indicators` | Compara um par de indicadores fora desses quatro, com a mesma saída. Recebe só os nomes; os valores vêm do arquivo, então não há conta sobre número inventado. | "Quanto de X foi usado em relação a Y?" |

`get_project_indicators` também devolve dados que o `instructions.md` ainda não roteia:

- movimento de terra: corte, aterro, balanço e muro (17 de 24 arquivos);
- projeção das torres;
- descritivos de tipologia e de vaga;
- alturas de pavimento;
- cota de referência do terreno.

## Contagem, busca e medida no desenho

Estas tools respondem sobre o que está desenhado. Elas devolvem totais prontos para o modelo não somar nem contar listas à mão.

| Tool | O que faz | Perguntas que responde |
| --- | --- | --- |
| `count_entities` | Conta por tipo, layer ou família. Por família, conta **instâncias** e devolve o total por tipo (`por_tipo_familia`: Tower, Vaga, Portaria), quantas famílias há de cada tipo e o tipo de cada família. | "Quantas torres?", "Quantas famílias de torre existem?", "Quantos elementos há no layer pav_tipo?" |
| `query_entities` | Busca com filtros combinados: tipo, layer, família, instância, rótulo, região, comprimento, só polígonos. Ordena por área ou comprimento e pagina; devolve também todas as instâncias encontradas e o total delas. | "Qual o maior apartamento?", "Quais são as partes da torre p3?", "O que existe nesta região?", "Liste as torres da família U/30" |
| `search_text` | Procura no rótulo das partes: a tipologia do apartamento ou da varanda, ou o nome da família. Aceita expressão regular. | "Onde estão os apartamentos de 2 quartos?", "Onde aparece a tipologia UH Ponta?" |
| `list_layers` | Lista os layers com contagem, cor e tipos de elemento. | "Quais layers existem?" |
| `get_entity_details` | Com id de instância: família, tipo, propriedades da família e lista de partes. Com id de parte: medidas, instância e família. | "Detalhe a torre p12", "Qual a família desta vaga?", "Quantos pavimentos tem esta torre?" (das propriedades da família) |
| `measure` | Comprimento, área (já sem os furos), caixa envolvente ou distância entre centros. Aceita id de instância. | "Qual a área do talude?", "Qual o perímetro do terreno?", "Qual a distância entre as torres p0 e p1?" |

A área de `measure` é em planta, de um pavimento, e não é área construída.

## Ações na planta

O assistente aponta de volta para o desenho com estas quatro tools. O frontend lê a chamada no stream do chat e aplica o efeito no canvas antes de o texto da resposta chegar.

| Tool | O que faz | Exemplo |
| --- | --- | --- |
| `highlight_entities` | Destaca entidades e pode reenquadrar a vista. Um id de instância acende a torre ou a vaga inteira. | "Destaque todas as torres" |
| `zoom_to` | Reenquadra em ids, num layer, numa região ou no desenho todo. | "Mostre a área da portaria" |
| `set_layer_visibility` | Mostra, oculta ou isola layers. | "Isole o layer pav_tipo" |
| `clear_highlight` | Remove o destaque atual. | "Limpe o destaque" |

## Como foi validado

Na última rodada do eval com o LLM real, nenhuma das 35 perguntas falhou:

- 28 passaram na checagem automática: valor certo e nenhum número sem procedência;
- 5 são recusas do vínculo descritivo ↔ torre, conferidas à mão, porque o eval não aprova esse caso sozinho;
- 2 foram puladas: os projetos não têm o indicador de vagas.

O eval roda 7 perguntas em cada um dos 5 projetos `otimo_*` de `data/aqg/avaliadas/` e confere se cada número da resposta saiu de uma tool.

| Rodada | Falhas | O que mudou antes dela |
| --- | --- | --- |
| 4ª | 0 | Totais prontos (`total_instancias`, `familias_por_tipo`) e regra de não contar listas |
| 3ª | 2 | Lista completa de instâncias em `query_entities` e número de grupos em `count_entities` |
| 2ª | 2 | `compare_indicators`, regra de não fazer contas e total por tipo de família |
| 1ª | 13 | — |

Casos cobertos: torres, unidades, área construída, CA projetado × máximo, vagas, destaque de todas as torres e o vínculo descritivo ↔ torre (o assistente tem de recusar). Permeabilidade e gabarito não são cobertos, e por isso o erro de `compare_indicators` não apareceu. Para rodar de novo: `make eval` (usa o gateway e tem custo).

O parser também roda em teste sobre os 24 AQGs locais: todas as instâncias encontram família, todo core cai dentro do perímetro e o número de torres desenhadas bate com `TotalDeTorres`.
