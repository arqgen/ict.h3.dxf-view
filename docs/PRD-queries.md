# PRD — Queries sobre o AQG e tools caixa-preta

> Status: **proposta fechada com o time do viabiliza-terrenos** (09/11/2026), para levar à RECOD. Base: estudo de `hub-ai.*`, `prototype.solucao.backend.eros` e `.frontend.eros`, `viabiliza-terrenos.backend`, `buildings`, dos motores (teodora, teseu, ibitira, minotauro, veredas, trama) e dos 24 AQGs locais.

## Objetivo

A RECOD vai medir a estrutura intermediária do AQG pelo que o modelo vê: o modelo lê e edita a estrutura, e compara-se o AQG cru com cada proposta. Este PRD entrega o que fica fixo entre os lados:

1. as tools: motores como caixa-preta, operações de edição e cálculo;
2. as tarefas (queries), cada uma com resposta verificável.

| Fixo entre os lados | Varia |
| --- | --- |
| Tarefa, estado inicial, resposta esperada e tools | A estrutura que o modelo lê e edita |

Métricas por tarefa: tokens de entrada (a estrutura e o que as tools devolvem), tokens de saída, chamadas de tool, acerto e dano colateral (uma edição que muda o que não devia).

## O que o estudo encontrou

### Onde o AQG nasce

```
site + PU + PA ─ seed ─▶ Tower ─▶ ParkingLot ─▶ Entrance ─▶ Leisure ─▶ Earthmoving ─▶ indicadores + anotações ─▶ Project
                       teodora   teseu        teodora     teodora     trama
                                 ou veredas                           + ibitira
                                 + minotauro
                                 ou subsolo
```

- Uma rodada sorteia 300 seeds. Cada seed escolhe um pipeline, uma configuração e uma meta de `CAMin` × `MaxHeight`, e grava a escolha em `solution.strategy`.
- A geração é assíncrona: Step Function → Lambdas, em minutos.
- Cada etapa é uma função Python em `viabiliza-terrenos.backend/packages/py/lib/problem/**` e `buildings`. Nenhuma tem endpoint síncrono.
- **Editar a etapa *k* invalida as etapas *k+1…n*.** Essa dependência decide o que "rodar de novo só uma parte" significa.

### Quem edita hoje

| Sistema | Lê o Project | Altera o Project | Histórico |
| --- | --- | --- | --- |
| Hub (`hub-ai.agente` + `hub-ai.mcp`) | Não. Vê só o retrato da tela (`<ui_data>`, top 5 soluções) | Não. Escreve só o PA, o PU e o disparo da rodada. O time vem tirando ações do agente (ARQ-9178) | Não. O documento `parameters` é sobrescrito |
| Eros | Sim | Sim: torres, pavimentos, cota do platô, viário, terraplenagem, regenerar. Só o frontend usa | Não há undo. "Salvar" cria uma solução filha (`parentSolutionId`) |
| Viabiliza-terrenos | Gera | Só uma rodada nova inteira | Run record por rodada (`runs/<requestId>/report.json`) |
| Este repo | Sim, com 16 tools | Não | — |

### Achados que pesam na pesquisa

1. **O Project não basta para regerar tudo.** As famílias não usadas são podadas (`remove_unused_families`). `client_specs` e `familyKey` não vão no arquivo. O problema do teodora fica no S3 por 90 dias. Para validar as torres e refazer o estacionamento o AQG basta (seção O que já foi verificado); para trocar uma torre por outra família ou regerar com as specs do cliente, não.
2. **A topologia do viário se perde, mas pode ser regerada.** `road_network` é persistido como `null`, e o viário vira polígono em `AQG_RUA`. O Eros recupera a rede do S3 (`app/teseu/archived.py`). Rodar o teseu de novo a partir das torres também a recupera: nos arquivos recentes, reproduz as mesmas vagas e devolve a rede com nós (seção O que já foi verificado).
3. **Os indicadores têm duas implementações**: `compute_outputs` do `buildings` e a reimplementação do Eros em `app/outputs`. O Eros registra que o ibitira não alimenta `MovimentoDeTerra`.
4. **A validação devolve só a primeira violação** (`app/teodora/validate.py:63`). Responder "por quê" e "o que corrigir" exige todas.
5. **Nenhum sistema tem histórico de edições.** A estrutura de histórico é frente da RECOD.
6. **O Eros não troca a família de uma torre nem muda o PA**: o problema chega congelado do S3, e o `archprog` é copiado sem mudança.

## Tools

### Tools finas

Se a tool responde a pergunta, a estrutura some da medição: a saída de `check_zoning` tem o mesmo tamanho sobre o AQG cru e sobre qualquer proposta. Por isso as tools do benchmark recebem ids e parâmetros que o modelo leu na estrutura e devolvem o mínimo. Depois de uma edição, o modelo lê o novo estado na própria estrutura; a tool devolve só o veredito, as violações (com ids) e as etapas que rodaram.

| Tipo | Por que existe | O que mede da estrutura |
| --- | --- | --- |
| Motores | Uma edição real reroda viário, terraplenagem e indicadores; sem isso o AQG editado fica incoerente | Quanto pesa o resultado que volta para a estrutura (ex.: mil vagas regeradas) e se dá para saber o que ficou desatualizado |
| Operações de edição | O modelo escolhe a operação; a tool aplica | Quantos tokens custa endereçar e expressar a edição, e o dano colateral |
| Cálculo | O modelo não faz conta nem geometria | Nada: separa erro de leitura de erro de conta (D4) |

As tools que hoje respondem perguntas inteiras neste repo (`check_zoning`, `compare_program`, `count_entities`…) ficam fora da comparação entre representações. Decidido em 09/11/2026: elas rodam num terceiro braço, só nas tarefas de leitura (L, A, B, C), como linha de base ("vale ter uma representação melhor ou basta dar tools prontas ao modelo?"). São código sem binário e podem ir para a RECOD junto com as de cálculo.

### Ciclo de uma edição

O modelo não move a torre: a função move. O modelo trabalha antes e depois dela.

1. Lê a estrutura e resolve as referências do pedido ("a torre mais próxima da APP" → um id).
2. Chama a operação com esses ids.
3. A função aplica no AQG e roda os motores da cascata.
4. O modelo recebe uma visão do resultado: o documento inteiro, uma diferença ou outra forma. Essa forma é decisão da estrutura.
5. O modelo julga o resultado (válido? o que mudou?) e responde ou parte para a próxima operação.

Os passos 1, 4 e 5 custam tokens conforme a estrutura. O custo de um ciclo inteiro é a medição de edição mais reveladora: com o AQG cru, a visão do resultado tende a ser o documento de novo, com as vagas regeradas junto.

### Motores (caixa-preta)

| Tool | Motor | Lê da estrutura | Devolve à estrutura | Latência medida | Existe em |
| --- | --- | --- | --- | --- | --- |
| `resolver_torres(fixadas, seed, modo)` | teodora positioning ou filling | Perímetro, recuo, famílias, torres fixadas, PA | Torres posicionadas e scores | 0,07–4,2 s no Eros; até 260 s no pipeline | `lib/problem/towers/`; Eros `_solve_once` |
| `resolver_estacionamento(params)` | teseu `optimize`, ou veredas + minotauro, ou subsolo | Torres, portaria, perímetro, acessos | Vagas (até ~3 mil instâncias), viário e sua rede | 0,04–3,5 s (8,6 s com topografia); p95 de 57 s em produção | `lib/problem/parking_lot/`; Eros `_solve_viary` |
| `posicionar_portaria()` | teodora | Perímetro, acessos, torres | Portaria | — | `lib/problem/entrance.py` |
| `resolver_lazer()` | teodora | Áreas livres, PA de lazer | Áreas de lazer | — | `buildings/lazer/solver.py` |
| `resolver_terraplenagem(talude, cotas)` | trama + ibitira | Malha do terreno, platôs, viário 3D, vagas | Malhas novas, taludes, muros, cotas | ~0,9 s | `lib/problem/earth_movement.py`; Eros `_solve_ibitira` |
| `recalcular_indicadores()` | `compute_outputs` + `compute_annotations` | O projeto todo | Cerca de 50 tipos de indicador e as anotações | — | `buildings.metrics`; Eros `app/outputs` (achado 3) |
| `validar()` | teodora com tudo fixado, por partes: cada torre sozinha (regras de terreno), cada par (afastamento) e o conjunto (agregados de CA, TO, permeabilidade e vagas). Decidido em 09/11/2026; um subcomando `validate` no teodora fica como sugestão ao time dele | Torres e restrições | Nada; devolve todas as violações, com a torre e a regra | 6–67 ms por chamada; ~1 s para 12 torres | Eros `app/teodora/validate.py`, que hoje devolve só a primeira |
| `potencial_terreno()` | `gen_solving_parameters` + `validate_solve_request` | Terreno, PU, PA, famílias | Nada; devolve as faixas viáveis de CA e altura | — | `buildings` |

### Operações de edição

Toda operação aceita `preview` (roda sem gravar) e pode ir num lote atômico. Referências como "aos fundos" ou "paralela à frente" são resolvidas pela tool, não pelo modelo.

| Operação | Parâmetros | Cascata depois | Tarefas |
| --- | --- | --- | --- |
| `mover_torre` | Torre; deslocamento ou referência a uma linha do terreno | validar → estacionamento refeito (regra geral; preservar a rede, como o Eros, fica para depois) → terraplenagem → indicadores | D1, D10, E8 |
| `girar_torre` | Torre; ângulo ou "paralela a" uma linha | Idem | D2 |
| `adicionar_torre` | Família; posição ou "onde couber" (teodora com as demais fixadas) | Idem | B1, D4, F2 |
| `remover_torre` | Torre | Idem | D3 |
| `fixar_torre` / `liberar_torre` | Torre | Vale para o próximo `resolver_torres` | D5, F6 |
| `definir_pavimentos` | Torre; total | Novo tipo irmão e novo afastamento → validar → cascata | D6, E4 |
| `definir_cota_plato` | Torre; cota | Terraplenagem → indicadores | D7 |
| `trocar_familia` | Torres; família ou programa novo | Validar → cascata; se ficar inválido, reposiciona só a torre inválida | E2, E3, E4 |
| `editar_rua` | Adicionar, editar, mover ou remover; nó da rede | teseu `interact` → terraplenagem → indicadores | D8 |
| `alterar_programa` | Chave do PA ou do PU; valor | Reroda a partir da etapa da tabela abaixo | A5, E1, E3–E8, F1, F5 |

**Família equivalente** (decidido com o time do VT em 09/11/2026): numa troca, a nova família sai do conjunto que `build_families` gera para o novo programa, escolhida nesta ordem: (1) o formato que o pedido nomeia ("torres em H"); (2) senão, o formato da torre original (I, L, U, H); (3) o número de pavimentos permitido mais próximo do original; (4) as unidades por pavimento mais próximas; (5) no empate, a de pegada menor. Sem família no formato exigido, a tool responde que a troca não é possível com aquele programa.

O Eros já faz mover, girar, adicionar (com coordenada), remover, fixar, pavimentos, cota do platô e editar rua. `trocar_familia` e `alterar_programa` não existem em nenhum sistema.

**Regra geral de edição** (decidida com o time do VT em 09/11/2026): o que o usuário já tem é preservado. Roda-se de novo a etapa diretamente afetada e as seguintes; as anteriores só são revalidadas, e regeradas apenas se ficarem inválidas ou se o usuário pedir. Quando a mudança deixar a solução claramente pior do que poderia ser (ex.: espaço perdido entre as torres depois de mudar a largura da via), o modelo avisa e oferece regerar.

**Mudança → etapa** (aplicação da regra geral):

| Mudança | O que acontece |
| --- | --- |
| `RoadNetworkWidth`, `SidewalkWidth` | Torres revalidadas (a largura entra na circulação das torres); estacionamento em diante refeito |
| `ParkingLotPerUnit`, `AdditionalParkingRatio` | Famílias recalculam `vagas_necessarias`; torres revalidadas pelo agregado de vagas; estacionamento em diante refeito. Verificado no spike do teseu |
| PU: permeabilidade | Torres revalidadas (agregados); estacionamento em diante refeito (o teseu respeita a permeabilidade mínima) |
| PU: recuos e afastamento | Recuo do terreno recalculado; torres revalidadas; o resto só se alguma torre se mover |
| PU: CA e TO | Torres revalidadas e indicadores recalculados |
| `AuxiliaryArea*`, `DistributedLeisure` | Torres revalidadas (lazer impermeável entra nos agregados); lazer e terraplenagem refeitos |
| `VGVPorUnidade` | Só indicadores |
| `FamilyProportion`, `FamilySelection`, `AlturaDoPavimento`, `MaxHeight`, `Min/MaxPavimentos`, `Min/MaxUnitsPerFloor`, `Min/MaxTowersBySite`, `TypicalFloorFormat` | Alteram as próprias torres. Mantém-se a posição e a quantidade e troca-se a família de cada torre pela equivalente no novo programa; uma torre que fique inválida com a nova pegada é reposicionada sozinha (teodora com as demais fixas); se o programa mudar a quantidade de torres (`Min/MaxTowersBySite`), as torres são regeradas. Depois, estacionamento em diante refeito (a demanda de vagas muda com as unidades) |

### Cálculo

| Tool | Faz |
| --- | --- |
| `calcular(expressao)` | Soma, razão e diferença sobre valores que o modelo leu na estrutura |
| `medir(ids, metrica)` | Comprimento, área, distância borda a borda, volume entre malhas |
| `relacao_espacial(ids, tipo)` | Dentro, sobrepõe, mais próximo, dentro de um raio |
| `cota_terreno(ponto ou pegada)` | Cota interpolada na malha |
| `caminho(origem, destino)` | Distância pela rede viária; a rede sai de rodar o teseu de novo (achado 2) |

### Rodadas e versões

| Tool | Faz | Tarefas |
| --- | --- | --- |
| `consultar_rodada(request_id)` | Lê o run record: estratégia, falhas por etapa e indicadores por seed | A4, F3, G1, G2 |
| `resolver_seed(seed)` | Uma seed, síncrona (até 260 s) | C3, F3 |
| `diff_versoes(a, b)`, `desfazer(n)`, `restaurar(versao, manter)`, `historico()` | Contrato que a estrutura de histórico da RECOD precisa atender; como o histórico aparece para o modelo também entra na medição | G4–G7 |

## Tarefas

Cada tarefa diz o que força na estrutura. As tarefas citam elementos por descrição ("a torre mais próxima da portaria"), nunca por id: resolver a referência é trabalho do modelo sobre a estrutura. Ao instanciar o caso, a descrição precisa apontar um elemento só.

| Força | O que a estrutura precisa facilitar |
| --- | --- |
| Localizar | Achar um campo ou um elemento |
| Agregar | Contar ou somar sobre muitas instâncias (até ~3 mil vagas) |
| Relacionar | Seguir referências: instância → família → propriedades; descritivo ↔ grupo de torres |
| Espacial | Relação geométrica entre elementos |
| Topologia | O grafo do viário |
| Derivado | Separar dado guardado de calculado e saber o que ficou velho |
| Editar | Endereçar e expressar uma operação sem estragar o resto |
| Cascata | Absorver o resultado de um motor |
| Histórico | Diferença e reversão entre versões |

Nível: **S** simples · **M** mediana · **C** complexa.

### L — Leitura direta

| Id | Tarefa | Nível | Força | Tools |
| --- | --- | --- | --- | --- |
| L1 | "Quantas torres tem a solução?" | S | Agregar | — |
| L2 | "Qual o CA máximo exigido e o projetado?" | S | Localizar | — |
| L3 | "Quantas vagas foram desenhadas?" | S | Agregar | — |
| L4 | "Qual a família da torre mais próxima da frente e quantos pavimentos ela tem?" | S | Espacial, Relacionar | `relacao_espacial` |
| L5 | "Quantas unidades há de cada tipologia?" | S | Relacionar, Agregar | `calcular` |
| L6 | "Qual a área do terreno e a área útil?" | S | Localizar | — |
| L7 | "Que elementos o terreno tem (frente, fundos, APP, curvas de nível)?" | S | Localizar | — |
| L8 | "Qual o afastamento exigido entre as torres?" | S | Localizar | — |

### A — Terreno e potencial

| Id | Tarefa | Nível | Força | Tools | Nota |
| --- | --- | --- | --- | --- | --- |
| A1 | "Quantas unidades este terreno comporta pelo CA, mantido o mix desta solução?" | M | Relacionar | `calcular` | Junta PU e indicadores: base de cálculo × CA máximo ÷ (área computável ÷ unidades) |
| A2 | "Quanto do terreno é inviável para torre por declividade?" | M | Relacionar, Espacial | `medir` | `inclination_groups` aponta faces da malha |
| A3 | "O programa pedido cabe neste terreno? Que faixas de CA e altura são viáveis?" | M | Localizar | `potencial_terreno` | — |
| A4 | "Qual é o gargalo deste terreno: CA, TO, permeabilidade, vagas, gabarito ou geometria?" | C | Agregar | `consultar_rodada` | Sobre a rodada, não sobre uma solução |
| A5 | "Se o recuo frontal fosse 8 m, quanta área útil eu perderia?" | M | Derivado | `alterar_programa(preview)`, `medir` | O offset é derivado do PU |

### B — Inferência sobre uma solução

| Id | Tarefa | Nível | Força | Tools | Nota |
| --- | --- | --- | --- | --- | --- |
| B1 | "Por que esta solução tem 2 torres se o CA permitia mais?" | C | Derivado, Relacionar | `adicionar_torre(preview)`, `validar`, `calcular` | A resposta nomeia a restrição que barrou a tentativa |
| B2 | "Quanto do terreno vai para o carro?" | M | Localizar, Agregar | `calcular` | Viário, estacionamento e projeção das torres |
| B3 | "Qual torre exige mais terraplenagem?" | M | Espacial | `cota_terreno`, `medir` | O indicador separa só platô × viário |
| B4 | "Quais torres estão sobre aterro, e com que altura máxima?" | C | Espacial | `relacao_espacial`, `cota_terreno` | Cruza a região de aterro com a pegada |
| B5 | "Qual a distância de carro da portaria a cada torre?" | M | Topologia | `caminho` | O AQG cru não guarda a rede; ela sai de rodar o teseu de novo (achado 2) |
| B6 | "O viário respeita a rampa máxima? Onde fica o trecho mais íngreme?" | M | Topologia, Espacial | `cota_terreno` | — |
| B7 | "Por que o score `biggest-buildings` é baixo?" | M | Derivado | — | O score é saída do gerador; a semântica está fora do AQG |
| B8 | "Que estratégia gerou esta solução?" | S | Localizar | — | `solution.strategy` |
| B9 | "Alguma torre fica sem vaga num raio de 50 m?" | M | Espacial, Agregar | `relacao_espacial` | Até ~3 mil vagas |
| B10 | "Para onde estão voltadas as fachadas maiores?" | M | Relacionar | `calcular` | Ângulo local + georreferência |
| B11 | "Quantas unidades eu perderia se a torre mais próxima da portaria tivesse 5 pavimentos a menos?" | M | Espacial, Relacionar | `relacao_espacial`, `calcular` | — |

### C — Auditoria e coerência

| Id | Tarefa | Nível | Força | Tools | Nota |
| --- | --- | --- | --- | --- | --- |
| C1 | "Os indicadores batem com o desenho?" | M | Derivado | `recalcular_indicadores(preview)` | Guardado × recalculado |
| C2 | "O `MovimentoDeTerra` é coerente com as malhas original e nova?" | C | Derivado, Espacial | `medir` (volume entre malhas) | — |
| C3 | "As famílias deste arquivo bastam para regerá-lo?" | M | Relacionar | `resolver_seed` | Famílias podadas e specs fora do arquivo (achado 1) |

### D — Edição geométrica

| Id | Tarefa | Nível | Força | Tools | Nota |
| --- | --- | --- | --- | --- | --- |
| D1 | "Mova a torre mais próxima da frente 5 m em direção aos fundos" | M | Espacial, Editar, Cascata | `relacao_espacial`, `mover_torre` | O modelo resolve "mais próxima" e "fundos"; as vagas regeradas voltam à estrutura |
| D2 | "Deixe todas as torres paralelas à frente" | M | Editar | `girar_torre` (lote) | Uma edição, várias torres |
| D3 | "Remova a torre mais próxima da APP e diga quantas unidades perdi" | M | Espacial, Editar, Cascata | `relacao_espacial`, `remover_torre` | — |
| D4 | "Coloque mais uma torre igual à mais alta onde couber" | C | Relacionar, Editar, Cascata | `adicionar_torre` | A posição vem do teodora |
| D5 | "Mantenha as duas torres mais próximas da portaria e regenere o resto" | M | Espacial, Cascata | `relacao_espacial`, `fixar_torre`, `resolver_torres` | — |
| D6 | "Suba a torre mais próxima da portaria para 20 pavimentos" | M | Espacial, Editar, Derivado | `relacao_espacial`, `definir_pavimentos` | Cria um tipo irmão; o afastamento muda |
| D7 | "Baixe em 2 m o platô da torre mais distante da frente" | M | Espacial, Editar, Cascata | `relacao_espacial`, `definir_cota_plato` | Só a terraplenagem reroda |
| D8 | "Remova a rua que passa mais perto da torre mais distante da frente" / "Ligue à frente o fim da rua mais longa" | M | Topologia, Espacial, Editar | `relacao_espacial`, `editar_rua` | Exige a rede |
| D9 | "Refaça o viário com via de 6 m" | S | Cascata | `resolver_estacionamento` | — |
| D10 | "Afaste as torres até o afastamento entre blocos ter 1 m de folga" | C | Editar, Espacial | `mover_torre(preview)`, `validar`, `medir` | Laço até o critério |

### E — Programa e regeneração parcial

| Id | Tarefa | Nível | Força | Tools | Nota |
| --- | --- | --- | --- | --- | --- |
| E1 | "Aumente para 1,5 vaga por unidade e refaça só o estacionamento" | M | Cascata | `alterar_programa` | A demanda vem de `vagas_necessarias` das famílias, que precisa ser recalculada antes; no spike, 2 de 11 terrenos perderam vagas com a demanda × 1,5 |
| E2 | "Troque as torres em I por torres em H, mantendo as posições" | C | Relacionar, Editar, Cascata | `trocar_familia` | Usa o catálogo de famílias congelado em `data/families/` (D6) |
| E3 | "Mude o mix para 60% 2Q / 40% 1Q mantendo a implantação" | C | Relacionar, Cascata | `alterar_programa`, `trocar_familia` | — |
| E4 | "Com pé-direito de 2,9 m, cabe mais um pavimento?" | M | Derivado, Editar | `alterar_programa(preview)`, `definir_pavimentos` | — |
| E5 | "Troque o estacionamento descoberto por subsolo" | C | Cascata | `alterar_programa` | Muda permeabilidade e terraplenagem |
| E6 | "Inclua lazer distribuído" | M | Cascata | `alterar_programa` | — |
| E7 | "Refaça só a terraplenagem com talude mais suave e sem muro" | M | Cascata | `resolver_terraplenagem` | Fora do produto hoje (o talude vem do `SlopeSpec` das specs do cliente); mantida por decisão do time do VT. Parâmetros canônicos: aterro 1:2 (26,6°), corte 1:1,5 (33,7°), altura de muro sem limite |
| E8 | "O recuo frontal virou 8 m: quais torres ficam irregulares? Corrija com o menor deslocamento" | C | Derivado, Editar, Espacial | `alterar_programa`, `validar`, `mover_torre` | — |

### F — Contrafactual e otimização dirigida

| Id | Tarefa | Nível | Força | Tools | Nota |
| --- | --- | --- | --- | --- | --- |
| F1 | "Qual a menor mudança que faz a permeabilidade passar?" | C | Derivado, Cascata | `alterar_programa(preview)`, `resolver_estacionamento(preview)`, `calcular` | Caso real `6abab05295f4…` (19,99 × 20) |
| F2 | "Se eu abrir mão de 20 vagas, cabe mais uma torre?" | C | Cascata | `resolver_estacionamento`, `adicionar_torre(preview)` | — |
| F3 | "Maximize unidades com corte + aterro abaixo de 1.000 m³" | C | Agregar | `resolver_seed`, `consultar_rodada` | — |
| F4 | "Sem mexer nas torres, quantas vagas a mais cabem?" | M | Cascata | `resolver_estacionamento(preview)` | — |
| F5 | "Qual o VGV se eu trocar 1Q por 2Q?" | M | Derivado | `alterar_programa(preview)` | — |
| F6 | "Proponha 3 variações que mantenham as duas torres mais próximas da portaria e explorem o fundo do terreno" | C | Espacial, Cascata, Histórico | `relacao_espacial`, `fixar_torre`, `resolver_torres` | As variações são ramos de versão |

### G — Rodada, comparação e histórico

| Id | Tarefa | Nível | Força | Tools | Nota |
| --- | --- | --- | --- | --- | --- |
| G1 | "Por que nenhuma das 300 soluções tem 4 torres?" | C | Agregar | `consultar_rodada` | — |
| G2 | "Qual estratégia rendeu mais unidades nesta rodada?" | M | Agregar | `consultar_rodada` | — |
| G3 | "O que a solução ótima tem que a ruim não tem?" | C | Relacionar | `calcular` | Duas estruturas no contexto |
| G4 | "O que mudou entre a solução mãe e a filha 3.A?" | M | Histórico | `diff_versoes` | — |
| G5 | "Desfaça as duas últimas mudanças" | S | Histórico | `desfazer` | — |
| G6 | "Volte para antes de eu mexer no viário, mas mantenha a torre que movi" | C | Histórico, Cascata | `restaurar` | A rede depende da posição da torre |
| G7 | "Quais indicadores ficaram desatualizados depois desta edição?" | M | Derivado, Histórico | `historico` | — |
| G8 | "Qual solução da rodada mais se parece com esta?" | C | Relacionar | — | Compara estruturas inteiras |

## Uso como benchmark

Cada tarefa vira um caso fixo:

| Campo | Conteúdo |
| --- | --- |
| Estado inicial | Leitura: o arquivo do acervo. Edição: a base, o arquivo normalizado pela cascata sem edição (difere só em indicadores que o `buildings` atual calcula diferente, no UUID do viário e nos scores). Nas tarefas G, também a sequência de edições anteriores |
| Referências | Elementos citados por descrição; resolver a referência faz parte da tarefa, e a resposta esperada usa o elemento do AQG cru |
| Resposta esperada | Número, veredito, ids ou o estado resultante, calculado por script sobre o AQG cru, sem LLM |
| Métricas | Tokens de entrada e saída, chamadas de tool, acerto e dano colateral |

Numa edição, o estado resultante é o AQG gravado (D1, D5): a RECOD só precisa da conversão AQG → estrutura e do mapa de ids. Tarefas de edição só rodam nos arquivos admitidos (D7).

## O que já foi verificado

### Spikes dos motores

Teodora, teseu e ibitira remontam o problema a partir do próprio AQG, com o código do viabiliza-terrenos já instalado no venv dele (binários e `buildings` 19.3.0), sem S3 e sem AWS. Scripts e resultados em `experiments/spikes/`.

| Motor | Arquivos | Resultado | Tempo |
| --- | --- | --- | --- |
| teodora (`validar`) | 21 de 24 remontados | Solução original válida em 21/21; torre deslocada 500 m inválida em 21/21; torre sobreposta a outra inválida em 15/15 (pega por torre × torre, recuo, encosta íngreme ou distância às linhas) | Montar: 31–324 ms; binário: 6–67 ms |
| teseu (`resolver_estacionamento`) | 11 de 11 com teseu | Mesmo número de vagas do arquivo em 10/11; mesmas posições (até 1 cm) em 3/3 conferidos (versões 17.7 e 18.0); o único 16.4 diverge | teseu: 0,01–1,35 s; greide: até 0,85 s |
| ibitira (`resolver_terraplenagem`) | 15 de 15 com terraplenagem | Cadeia só torres → teseu → ibitira: corte, aterro, muro e cota das torres idênticos em 13/15 (17.7 e 18.0); os 2 da 17.1 divergem. Exige o adaptador da D8 | 0,18–2,7 s |

Limites:

- Os arquivos anteriores à 16.4 não remontam o teodora (falta `strategy` ou `site.analysis`).
- As specs do cliente foram as padrão em todos (D6).
- Não testado: o `interact` do teseu (edição de rua).

### Teste de admissão

`evals/benchmark/admissao.py` junta os três spikes num critério: um arquivo entra nas tarefas de edição só se o teodora aceita as torres e recusa o controle, o teseu refaz as mesmas vagas nas mesmas posições e o ibitira refaz o mesmo corte, aterro, muro e cota. Também aponta o catálogo de `data/families/` que cobre o programa.

**29 de 37 admitidos**: os 16 arquivos 17.7 e 18.0 do acervo original e os 13 de `solucoes-18x/` (18.0 e 18.1), todos com catálogo. Fora: 4 antigos sem `strategy`, o 16.4 (vagas divergem), o 16.8 (estacionamento por quarteirões, fora da cadeia gravável) e os 2 da 17.1 (terraplenagem diverge).

### Gabarito das tarefas de leitura

481 casos (37 arquivos × 13 tarefas), calculados por `evals/benchmark/gabarito.py` com o parser de `src/cad` e gravados em `evals/benchmark/casos.json`: 449 com resposta e 32 fora.

| Tarefa | Com resposta | Fora | Motivo |
| --- | --- | --- | --- |
| L1 | 37 | — | Bate com `TotalDeTorres` |
| L2 | 37 | — | — |
| L3 | 37 | — | 10 arquivos sem vaga desenhada respondem 0 |
| L4 | 34 | 3 | Empate de distância (< 0,01 m) |
| L5 | 37 | — | Bate com a soma por família |
| L6 | 37 | — | — |
| L7 | 37 | — | — |
| L8 | 37 | — | — |
| A1 | 37 | — | — |
| B2 | 27 | 10 | Sem vagas desenhadas |
| B8 | 33 | 4 | Versões antigas sem `solution.strategy` |
| B9 | 27 | 10 | Sem vagas desenhadas |
| B11 | 32 | 5 | Arquivo sem portaria |

Definições adotadas, com a evidência:

- **A1:** base de cálculo (`AreaDeMatricula` quando ela é a base declarada, senão `AreaDoTerreno`) × `CAMaximoExigido` ÷ (`AreaTotalConstruidaComputavel` ÷ `TotalDeUnidades`), arredondado para baixo, pelo mix da própria solução (decidido com o time do VT). A mesma base reproduz o `CAProjetado` em todos os arquivos.
- **B2:** `EstacionamentoProjetado` já inclui o viário (definição em `buildings/metrics` e soma conferida em 14/14). A resposta é ele, com viário e vagas só como decomposição.
- **L8:** `AfastamentoProjetado.entre_blocos`, que é a regra aplicada (2 × o afastamento da família, conferido em 24/24), não uma distância medida.

## Decisões

Todas fechadas com o time do viabiliza-terrenos em 09/11/2026.

1. **D1 — Onde os motores rodam: função gravada.**
   - Os motores rodam só do lado da Arqgen, com os binários locais e o código do VT; os binários não são compartilhados com a RECOD.
   - Para cada tarefa de edição, a Arqgen roda a chamada canônica uma vez e grava o AQG resultante. A tool entregue à RECOD só devolve o resultado gravado; uma chamada fora do roteiro responde "fora do roteiro", e isso entra nas métricas.
   - Depois, se a RECOD precisar explorar alternativas: serviço de tools ao vivo, como sub-servidor do `llm.h3.mcp-server` (falta empacotar o `lib` do VT e expor o endpoint). Meio-termo: gravar uma grade de transições (mover em passos de 1 m, girar em 5°, pavimentos de 1 em 1).
   - Descartadas por ora: API no backend do VT (mexe em produção para um grupo externo) e rodar o benchmark inteiro do nosso lado (cada iteração deles dependeria de nós).
2. **D2 — Primeira fatia.**
   - Leitura: L1–L8, A1, B2, B8, B9, B11 (gabarito pronto) e B5 (falta gravar a rede viária regerada pelo teseu).
   - Edição gravada, nos arquivos admitidos: D1, D3, D6, E1, E3, E7.
   - Histórico: G4 e G5 (do nosso lado, só o estado inicial e o esperado).
   - Tools: as de cálculo, `validar`, `mover_torre`, `remover_torre`, `definir_pavimentos`, `alterar_programa`, `trocar_familia`, `resolver_estacionamento`, `resolver_terraplenagem` (com talude) e `recalcular_indicadores`.
     - Ajuste de 10/11/2026: das de cálculo, entram `calcular`, `caminho`, `medir` (comprimento, área e distância) e `relacao_espacial` (mais próximo e dentro de um raio), as que as tarefas desta fatia usam. `cota_terreno`, o volume entre malhas da `medir` e os tipos "dentro" e "sobrepõe" da `relacao_espacial` entram com B3, B4, B6 e C2: exigem ler a malha do terreno, que o parser hoje ignora.
   - Para depois: as exploratórias (B1, D10, E8, F1–F3, F6), as que dependem de cota na malha ou de georreferência (A2, B3, B4, B6, B10, C2) e as demais.
3. **D3 — Regra de edição.** Regra geral e tabela "mudança → etapa" na seção Operações de edição; troca de família pela regra de família equivalente.
4. **D4 — Cálculo no benchmark: tools nos dois lados** (`calcular`, `medir`, `relacao_espacial`, `cota_terreno`, `caminho`). São código de geometria sem motor e podem ser entregues à RECOD; a rede viária do `caminho` vai como dado pré-calculado pelo teseu. Separa erro de leitura da estrutura de erro de conta.
5. **D5 — Fonte da verdade: o AQG cru.** As tools e os resultados gravados são sempre AQGs. Cada proposta da RECOD fornece só a conversão AQG → estrutura (a visão que o modelo lê) e o mapa de ids (id da estrutura ↔ elemento do AQG), sem caminho de volta.
6. **D6 — Famílias e configurações do cliente.**
   - O AQG só traz as famílias usadas e não grava `familyKey` nem `client_specs`. Os catálogos do ohana ficam congelados em `data/families/`: `comercial-vba` (programas novos, como o da E3) e os catálogos de origem (`cury-vba`, `emccamp-vba`, `rottas-vba`, `sc7-vba`), cada AQG com o do seu terreno.
   - `build_families` monta as torres com todos eles (0,5–5,7 s). A família original só reaparece no conjunto regerado em 2 de 6 terrenos, com as specs padrão ou as do cliente.
   - Specs do cliente: as padrão em todo o benchmark (reproduziram o acervo e não mudam as famílias).
   - Os catálogos têm famílias de teste; ficam como exportados, porque `build_families` só usa as que o programa cita.
7. **D7 — Arquivos do benchmark.** Tarefas de leitura em todos os arquivos (hoje 37); tarefas de edição só nos admitidos pelo teste de admissão (hoje 29). Num arquivo não admitido, uma edição gravada mudaria o que o usuário não pediu e contaria como dano colateral. O acervo cresce aos poucos: arquivos 18.x variados (terreno grande, 10+ torres, lazer, subsolo, mais de uma tipologia, terreno íngreme), uma solução por terreno, e alguns terrenos com 2 ou 3 soluções para as tarefas de comparação e para o eixo de versionamento. Ainda não há arquivo com subsolo.
8. **D8 — Versões dos motores nas gravações:** o conjunto que reproduziu o acervo, registrado em cada resultado gravado. Binários: teodora 17.1.0, teseu 0.5.2, ibitira 5.2.0 (com o adaptador que converte o `road_graph` do protocolo 6 para o 5), minotauro 2.0.0. Pacotes: buildings 19.3.0, maga-teodora 17.3.3, maga-teseu 0.6.0, maga-ibitira 6.0.0, trama 7.4.0.
9. **D9 — `validar` por partes:** cada torre sozinha, cada par e o conjunto, para devolver todas as violações sem mudar o teodora. Um subcomando `validate` no binário fica como sugestão ao time do teodora.
10. **D10 — Linha de base:** as 16 tools deste repo, que devolvem a resposta pronta, rodam num terceiro braço nas tarefas de leitura.

## Fora do escopo

- A estrutura intermediária e a de histórico: são frentes da RECOD. Este PRD só fornece as tarefas e os contratos.
- Medir os motores: são os mesmos nos dois lados.
- As tarefas e tools fora da primeira fatia (D2).
- Mudar o hub. O catálogo serve de insumo, e a integração é decisão do time do hub.
- Edição vaga a vaga e mais de um tipo de vaga (limites do teseu hoje).
