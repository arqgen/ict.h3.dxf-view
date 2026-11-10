# IMPLEMENTATION — Benchmark de queries sobre o AQG (primeira fatia)

> Guia de construção da primeira fatia do [`PRD-queries.md`](PRD-queries.md) (D2). O PRD define **o quê** e registra as decisões D1–D10; este documento define **como**: ordem, contratos, arquivos e critério de aceite de cada task.

## 0. Como usar este documento

### 0.1 Execução

- **Sequencial, uma task por vez**, na ordem da seção 4. A gravação de cada tarefa depende do núcleo (G0).
- **Branch:** `feat/aqg-benchmark`. Regras em [`commit-rules.md`](commit-rules.md): ao fim de cada task, rode as validações (1.3) e **pergunte sobre o commit**.
- **Dois ambientes**, que nunca se misturam:

  | Ambiente | Roda | Como |
  | --- | --- | --- |
  | Gravação (lado Arqgen) | Motores, `buildings` e `lib` do VT | venv do viabiliza-terrenos, com cwd em `data/benchmark/bin`, onde ficam os binários da D8 (não versionados; baixar com `AWS_PROFILE=arqgen` e `maga.core.install.install_binary(<nome>, <tag>)` nessa pasta) |
  | Entrega (lado RECOD) | Tools de cálculo, tools de edição gravada, linha de base, casos | venv deste repo (`uv run`) |

  Nenhum import do VT, do `buildings` ou da `maga` entra no código de entrega: é o que garante a D1 (binários e código de motor ficam na Arqgen).

### 0.2 Decisões já tomadas

| Decisão | Valor |
| --- | --- |
| Motores (D1) | Função gravada: a Arqgen grava o AQG resultante de cada chamada canônica; a tool entregue só devolve o gravado |
| Fonte da verdade (D5) | AQG cru; a RECOD fornece conversão AQG → estrutura e o mapa de ids |
| Edição (D3) | Etapa afetada e seguintes refeitas; anteriores só revalidadas. Mexer em torre refaz estacionamento, terraplenagem e indicadores (o viário é refeito pelo teseu; preservar a rede, como o Eros, fica para depois) |
| Troca de família (D3) | Regra de família equivalente do PRD |
| Famílias e specs (D6) | Catálogos de `data/families/`; specs padrão |
| Arquivos (D7) | Edição só nos admitidos por `admissao.py` (hoje 29) |
| Versões (D8) | teodora 17.1.0, teseu 0.5.2, ibitira 5.2.0 + adaptador, buildings 19.3.0; registradas em cada gravação |
| `validar` (D9) | Por partes: torre a torre, par a par e o conjunto |
| Linha de base (D10) | As 16 tools deste repo, só nas tarefas de leitura |

### 0.3 Portões

| Portão | Pergunta | Default proposto | Trava |
| --- | --- | --- | --- |
| P1 | B5: de onde a onde vai a "distância de carro"? | **Resolvido (10/11/2026):** menor caminho na rede, do ponto das ruas mais próximo do `/road_access` da portaria ao ponto mais próximo do `/road_access` de cada torre (projeção na aresta, não no nó). Pontos empatados a menos de 1 cm: fica o de menor caminho | G5 |
| P2 | "Em direção aos fundos" (D1) | **Resolvido (09/11/2026):** perpendicular à linha de frente mais próxima da torre, para dentro do terreno, em todos os arquivos (com ou sem `AQG_FUNDOS`) | G1 |
| P3 | Como a RECOD recebe as tools, os casos e as gravações | Pacote das tools e casos por acesso de leitura ao repo; gravações (centenas de MB) por um bucket ou um zip | E0 |

## 1. Contexto comum

### 1.1 Onde cada peça mora

| Peça | Caminho | Versionado |
| --- | --- | --- |
| Núcleo de gravação (cascata, validar, índice) | `evals/benchmark/gravacao.py` | Sim |
| AQGs gravados | `data/benchmark/gravacoes/<arquivo>/<chave>.json` | Não (pesado; padrão do `data/aqg/`) |
| Índice das gravações | `evals/benchmark/gravacoes.json` (chave → resultado, versões, tempos) | Sim |
| Rede viária regerada (B5) | `data/benchmark/redes/<arquivo>.json` | Não |
| Tools entregues | `evals/benchmark/tools/` | Sim |
| Casos | `evals/benchmark/casos.json` (leitura) e `evals/benchmark/casos_edicao.json` | Sim |

### 1.2 Regras

- **Ids das tools** são os do parser deste repo (`p<i>`, `s<i>`, `p<i>.<j>`): estáveis por posição no AQG. O mapa de ids da RECOD aponta para eles.
- **Tool não levanta exceção por dado inválido** (regra do repo): devolve o erro como dado. Uma chamada sem gravação devolve `{"erro": "fora do roteiro"}`.
- **Chaves em pt-BR** nos resultados (`veredito`, `violacoes`, `etapas`), como as tools atuais.
- **Determinismo:** toda gravação registra as versões da D8 e o arquivo de origem; regravar com as mesmas versões tem de dar o mesmo AQG.

### 1.3 Validações

- `make lint` e `make test` (o teste de corpus roda nos 37 AQGs).
- Gravação: a cascata sem edição (G0) tem de reproduzir o arquivo, como na admissão.
- `evals/benchmark/gabarito.py` e `admissao.py` rodados de novo quando a task mexer no que eles leem.

## 2. Contratos

### 2.1 Chave de gravação

```python
# chave canônica: o mesmo pedido, escrito de formas equivalentes, cai na mesma chave
Chave = tuple[str, str, tuple[tuple[str, object], ...]]  # (arquivo, tool, args ordenados)
```

Os argumentos são os semânticos, não coordenadas: `mover_torre(torre="p12", distancia=5.0, sentido="fundos")`. A tool resolve a geometria (P2); o modelo nunca calcula vetor.

### 2.2 Resposta de uma tool de edição

```json
{
  "veredito": "valido",
  "violacoes": [],
  "etapas": ["validar", "estacionamento", "terraplenagem", "indicadores"],
  "aqg": "data/benchmark/gravacoes/<arquivo>/<chave>.json"
}
```

`violacoes` traz `{"regra", "torres"}` por violação (D9). Com veredito `invalido`, a cascata para e `aqg` é o estado depois da edição, sem as etapas seguintes; o modelo julga e decide.

### 2.3 Cascata

Uma função só, usada por todas as gravações:

```
aplicar(project, edicao) ->
    edição sobre o Project
    → validar (por partes)                        ; inválido: para
    → reposicionar torres inválidas               ; só em troca de família (D3)
    → estacionamento: solve_parking_lot (teseu)   ; se a etapa afetada vem antes
    → terraplenagem: compute_earthmoving (ibitira 5.2.0 + adaptador)
    → indicadores: outputs zerados, earthmoving reaplicado, compute_outputs, compute_annotations
```

`compute_outputs` **acrescenta** em `solution.outputs`: o recálculo zera os outputs antes, ou os indicadores saem duplicados.

### 2.4 `validar` por partes (D9)

1. Monta o problema do teodora como `admissao.check_teodora` (pré-Tower, specs padrão).
2. Cada torre sozinha: violação de terreno (recuo, perímetro, encosta, distância às linhas) → `{"regra", "torres": [p]}`.
3. Cada par: violação entre torres (afastamento) → `{"regra", "torres": [p, q]}`.
4. O conjunto: agregados (CA, TO, permeabilidade, vagas necessárias) → `{"regra", "torres": todas}`.

O nome da regra sai da mensagem do binário (`parse_formulation_error` do Eros é a referência).

### 2.5 Família equivalente (D3)

Entrada: torre original, programa novo, formato pedido (opcional). Conjunto candidato = `build_families(specs padrão, catálogo do terreno, 10)` com o programa novo. Ordem: formato pedido → formato original → pavimentos mais próximos → unidades por pavimento mais próximas → menor pegada. Sem candidata no formato: `{"erro": "troca impossível com este programa"}`.

### 2.6 Rede viária (B5)

`data/benchmark/redes/<arquivo>.json`: `ruas`, os eixos que o teseu refaz (`ParkingLot.axis`, segmentos 3D de dois pontos, que se encontram nas pontas), e `acessos`, o `/road_access` posicionado de cada portaria e torre pelo id do parser (`p<i>` → linhas 2D). A tool `caminho(arquivo, origem, destino)` faz menor caminho nesse grafo, com origem e destino pela regra do P1, e devolve a distância e o afastamento de cada acesso à rede.

## 3. Fatos dos dados

Verificados nos spikes e na admissão (09/11/2026):

1. O problema do teodora sai de `_gen_problem` com `solution.placed_objects` vazio (estado pré-Tower); as torres do arquivo validam e o controle de 500 m não.
2. O teseu não usa sorteio e para por iteração nos admitidos: refaz as mesmas vagas, nas mesmas posições.
3. O ibitira 5.2.0 só aceita o `road_graph` como um par (largura, linhas); o adaptador está em `admissao.py`.
4. `vagas_necessarias` de cada pavimento sai de `_calc_expected_parking_spots(tipologias, archprog)` em `buildings/family/variations/height.py`.
5. Variações de altura de uma torre (pavimentos) saem de `_gen_height_variation` no mesmo módulo: a candidata natural para `definir_pavimentos`, a confirmar em G2.
6. `build_families` monta as torres com qualquer catálogo de `data/families/` (0,5–5,7 s); a família original só reaparece no conjunto em 2 de 6 terrenos.
7. As famílias de torre têm a parte `/road_access`, que o parser deste repo não desenha mas lê do arquivo.
8. 4 arquivos de `solucoes-18x/` não têm portaria: B5 e B11 ficam fora neles.
9. Rodar de novo a etapa de portaria não a reproduz; as demais etapas depois das torres (estacionamento, lazer, terraplenagem, indicadores, anotações) se reproduzem chamando `_solve_step` do pipeline.
10. `compute_annotations` e `remove_unused_families` devolvem o Project direto (não `Result`); `compute_outputs` devolve `Result`.

## 4. Ordem

| # | Task | Depende de | Entrega |
| --- | --- | --- | --- |
| 1 | G0 — Núcleo de gravação | — | Cascata, `validar` por partes, índice |
| 2 | G1 — Mover e remover torre (D1, D3) | G0, P2 | Gravações e casos |
| 3 | G2 — Pavimentos e mix (D6, E3) | G0 | Variação de altura, família equivalente, gravações |
| 4 | G3 — Vagas por unidade (E1) | G0 | Recálculo de `vagas_necessarias`, gravações |
| 5 | G4 — Talude (E7) | G0 | Gravações |
| 6 | G5 — Rede viária (B5) | P1 | Redes, `caminho`, gabarito da B5 |
| 7 | G6 — Histórico (G4, G5) | G1 | Sequências gravadas e respostas esperadas |
| 8 | T0 — Tools entregues | G0–G6 | `evals/benchmark/tools/` |
| 9 | T1 — Casos de edição e controles | T0 | `casos_edicao.json`, cliente-gabarito e cliente-vândalo |
| 10 | E0 — Entrega à RECOD | T1, P3 | Pacote e instruções |

## 5. Tasks

### G0 — Núcleo de gravação

- **Arquivos:** `evals/benchmark/gravacao.py` (cascata, `validar`, chave, índice); o que `admissao.py` já tem (adaptador do ibitira, problema do teodora) passa para lá, e `admissao.py` importa dele.
- **Passos:** cascata da 2.3; `validar` da 2.4; gravação em `data/benchmark/gravacoes/`; índice com versões da D8 e tempo de cada etapa.
- **Aceite:** a cascata sem edição, nos 29 admitidos, devolve um AQG com as mesmas vagas, o mesmo corte, aterro, muro e cota do arquivo, e os mesmos indicadores; `validar` nos arquivos originais devolve zero violações, e no controle de 500 m devolve a violação de terreno da torre deslocada.
- **Resultado (09/11/2026): concluída.** As 29 bases reproduzem todos os elementos do arquivo (torres, vagas, portaria, lazer e terraplenagem), são determinísticas (duas execuções, mesmo JSON) e `validar` devolve zero violações nelas. Nos controles, `validar` acusa `InsideGeometry` na torre deslocada 500 m e `NoOverlapping` no par sobreposto; 12 torres levam 0,7 s. Duas decisões de implementação:
  - a portaria não se reproduz ao rodar a etapa de novo (muda de lugar num arquivo; falha onde a família foi podada), então é preservada do arquivo, como no Eros;
  - o estado inicial das tarefas de edição é a **base**: o AQG normalizado pela cascata sem edição, gravado no índice com a tool `base`. Ela difere do arquivo só em indicadores que o `buildings` atual calcula diferente do exportador original (`AreaPrivativaTotalComputavel` e `AreaPrivativaTotalNaoComputavel` em 16 arquivos, `DescritivoTipologia` ausente em 17), no UUID do viário (fixado) e nos scores (mantidos do arquivo). Assim, a diferença entre a base e uma gravação mostra só a edição.

### G1 — Mover e remover torre

- **Tarefas:** D1 ("mova a torre mais próxima da frente 5 m em direção aos fundos") e D3 ("remova a torre mais próxima da APP e diga quantas unidades perdi").
- **Passos:** resolver a referência por descrição sobre o AQG cru (parser deste repo); aplicar a edição; cascata; gravar. A D3 só existe nos arquivos com APP.
- **Aceite:** gravação por arquivo admitido em que a descrição aponta um elemento só; a resposta esperada da D3 é a diferença de `TotalDeUnidades` entre o arquivo e o gravado.
- **Resultado (10/11/2026): concluída.** `evals/benchmark/edicoes.py` resolve a referência com o parser deste repo (torre pelo pavimento-tipo desenhado, como `relacao_espacial`) e passa a edição por `gravacao.aplicar`.
  - D1 em 27 dos 29: 15 válidas (cascata completa), 11 inválidas (`NoOverlapping`, `DistanceFromLinesGreaterThanThreshold`, `InsideGeometry`) e 1 erro do teseu (estacionamento inviável, gravado como `erro`). Duas ficam fora por empate abaixo de 1 cm na distância à frente. Em todas, a torre se afasta da frente 5 m (4,93 m e 4,96 m onde outra aresta passa a ser a mais próxima).
  - D3 nos 2 arquivos com `AQG_APP`: 60 e 72 unidades perdidas.
  - Dois ajustes no núcleo: a cascata devolve como `Err` a exceção que o teseu levanta por dentro (`unwrap` de `infeasible`); e `gravacao.py` se re-executa com `PYTHONHASHSEED=0`, porque a ordem de `families` saía de sets e mudava entre processos. A conferência da G0 rodava as duas vezes no mesmo processo e não pegava. As bases foram regravadas com a semente fixa.

### G2 — Pavimentos e mix

- **Tarefas:** D6 ("suba a torre mais próxima da portaria para 20 pavimentos") e E3 ("mude o mix para 60% 2Q / 40% 1Q mantendo a implantação").
- **Passos:** D6 pela variação de altura (fato 5; se não servir, pela família equivalente com 20 pavimentos); E3 com o catálogo comercial e a família equivalente para cada torre; reposicionar só as inválidas (teodora com as demais fixas); cascata.
- **Aceite:** famílias novas dentro do gabarito (`MaxHeight`) ou veredito `invalido` com a regra; nenhuma torre muda de lugar sem estar inválida.
- **Resultado (10/11/2026): concluída.** As duas tarefas estão em `edicoes.py`. Nas famílias novas e nas D6 válidas, a altura fica dentro do `MaxHeight`, e nenhuma torre fora de `reposicionadas`/`removidas` sai do lugar.
  - **D6** (`definir_pavimentos(torre, total=20)`) em 24 arquivos (5 sem portaria): 3 válidas e 21 `invalido`. A variação de altura (fato 5) é aplicada à própria família `Tower`: o volume de afastamento sai e é regerado por `_gen_family_variation`, e `total_pavimentos`, `pav_tipo.n` e `n_pavimentos_unidades` são refeitos como em `_compute_tower_property`. Com o próprio número de pavimentos, isso reproduz as 40 famílias de torre do acervo, exceto no terreno `6ace63aa`: lá o exportador gravou afastamento 3,0 e o `buildings` 19.3.0 calcula 2,13 pela fórmula do terreno (`(h-6)/10`), e a D6 usa o valor do motor. A faixa permitida sai de `gen_min_floors_with_units`/`gen_max_floors_with_units` (`MaxHeight`, `MaxPavimentos`, gabarito do terreno, `MaxTotalUnits`); fora dela, o veredito é `invalido` com `MaxPavimentos` ou `MinPavimentos` e a faixa na resposta. Na maioria dos arquivos as torres já estão no gabarito máximo, por isso tantas inválidas.
  - **E3** (`alterar_programa(mix=...)`) nos 29: 23 válidas e 6 erros (5 do teseu, porque o estacionamento não comporta a demanda nova, e 1 em que o tetris não acha planta para o programa). Programa canônico: `2q/40_71` 60% e `1q/27_97` 40%, as variantes simples do catálogo comercial; saem as proporções e a `FamilySelection` anteriores. As candidatas são todas do tetris. Família equivalente pela 2.5: o formato da original vem do `class_path` (tetris) ou do campo `formato` do catálogo de origem (estáticas). Em 8 arquivos as torres trocadas já validam; nos outros 20, 21 torres foram reposicionadas e 30 removidas, porque o teodora não achou lugar para elas.
  - **Reposicionar** (`gravacao.reposicionar`, só com `repor=True`): na ordem do arquivo, fica fixa a torre válida sozinha e compatível com as já fixadas, e as demais viram moldes livres. O problema usa só as famílias em uso, `SmallestCardinality` no lugar do `KeepProportion` da strategy (que cita as famílias trocadas) e, como meta, o número de torres de cada família, porque a meta de CA do arquivo já pode estar atendida pelas fixas. Teodora com `--seed 0`.
  - **Determinismo:** o tetris dá `_id` e datas novos a cada execução (fixados na E3), e a ordem de `families` depende de hash por identidade das geometrias, então `gravar` passa a escrever as famílias ordenadas por `class_path`. Bases e G1 foram regravadas; duas passadas completas dão os mesmos 104 AQGs, com os mesmos vereditos de antes.

### G3 — Vagas por unidade

- **Tarefa:** E1 ("aumente para 1,5 vaga por unidade e refaça só o estacionamento").
- **Passos:** `ParkingLotPerUnit` × 1,5 no archprog; `vagas_necessarias` recalculado por `_calc_expected_parking_spots` em cada pavimento das famílias de torre; validar (agregado de vagas); cascata a partir do estacionamento.
- **Aceite:** demanda nova = demanda do arquivo × 1,5 (arredondada como o `buildings` arredonda); resposta esperada com vagas atendidas e déficit, que pode ser negativo em relação às vagas do arquivo (spike: 2 de 11 perderam vagas).
- **Resultado (10/11/2026): concluída, com um desvio do passo.** A pergunta diz "aumente **para** 1,5" e a tool é `alterar_programa(chave, valor)`, então a gravação **define** `ParkingLotPerUnit = 1,5`, em vez de multiplicar por 1,5 como no spike. Os arquivos têm de 0,25 a 1,08, e por isso a demanda sobe de ×1,4 a ×6. Aceite conferido nessa leitura: em todas as gravações, demanda = `ceil(unidades × 1,5)`, como `calc_parking_spots_amount`.
  - E1 em 23 arquivos (6 sem etapa de estacionamento ficam fora): 8 válidas, 13 `invalido` e 2 erros do teseu (`infeasible`). Nas válidas, as vagas projetadas sobem e o déficit vai de 0 a 92. Das inválidas, 11 estouram a permeabilidade já no `validar` (o peso de cada torre inclui a área impermeável das vagas) e 2 caem no estacionamento: o teseu acha menos de 80% da demanda (85 de 120, 563 de 756).
  - **Recusa do teseu vira veredito:** quando a cascata cai em "didn't reach expected parking lots amount", `aplicar` grava `invalido` com `ParkingNetworkInsufficientRatio` e `vagas: {necessarias, encontradas}`, e não `erro`. Com isso, a E3 de `6ace7adc/otimo` passou de `erro` para `invalido`.
  - **Agregados com nome no `validar`:** o teodora só diz "broken broad constraint". `agregados_estourados` refaz as somas dos `MaximumSum` e nomeia o teto pelos mesmos que o gerador usa (`PermeabilidadeExigida` por `gen_tx_available_area_to_towers`, `CAMaximoExigido`); os outros saem como `MaximumSum`. As outras 110 entradas do índice não mudaram, e duas passadas dão os mesmos 126 AQGs.

### G4 — Talude

- **Tarefa:** E7, com os parâmetros canônicos do PRD (aterro 1:2, corte 1:1,5, muro sem limite).
- **Passos:** `SlopeSpec` sobreposto só nesta chamada; só terraplenagem e indicadores rodam.
- **Aceite:** torres e vagas idênticas ao arquivo; muro zero; corte, aterro e malhas novos gravados.
- **Resultado (10/11/2026): concluída.** `resolver_terraplenagem` em `edicoes.py`, nos 26 arquivos com terraplenagem (3 sem ela ficam fora): 26 válidas, de 1,2 s a 15,6 s. Contra a base, torres, portaria e vagas são idênticas, nenhuma gravação tem muro e as malhas do talude são novas; corte e aterro mudam em 25 (em `6ace4f3f/bom` o talude muda de forma sem mudar os volumes de platô). Duas passadas dão os mesmos 26 AQGs.
  - **Specs só na terraplenagem:** a `cascata` ganhou `por_etapa`, porque o viário também lê o `SlopeSpec` e não pode mudar.
  - **"Muro sem limite" = `slope_max_distance` de 1000 m:** com 1e6 a ibitira não termina (timeout de 600 s), e com 100 m ainda sobra um muro de 3,95 m em `6ac7a6d2`.

### G5 — Rede viária

- **Tarefa:** B5 ("qual a distância de carro da portaria a cada torre?").
- **Passos:** gravar a rede da 2.6 nos admitidos; tool `caminho`; gabarito da B5 em `casos.json`.
- **Aceite:** em todo arquivo admitido com portaria, toda torre alcançável ou marcada como inalcançável com o motivo.
- **Resultado (10/11/2026): concluída.** `evals/benchmark/redes.py` grava a rede em 23 dos 29 admitidos (6 sem etapa de estacionamento). A tool `caminho` está em `evals/benchmark/tools/calculo.py`, primeira das tools de cálculo da T0, em stdlib (Dijkstra) sobre a geometria deste repo, com teste em `tests/test_benchmark_caminho.py`. A B5 entrou no `gabarito.py`: 18 casos `ok` e 19 `fora` (6 sem estacionamento, 5 sem portaria, 8 não admitidos); os outros casos de `casos.json` não mudaram. Em `6ace84f4/otimo` uma torre fica inalcançável (rede em pedaços desconexos). As redes são determinísticas (duas passadas, mesmos arquivos).
  - **P1 pela aresta:** com o nó mais próximo, portaria e torres caíam no mesmo nó (7 torres a 0 m, distâncias repetidas), porque a rede tem poucos nós. O acesso passou a ser projetado na aresta, e os pontos escolhidos viram nós.
  - **0 m legítimo em 4 torres:** a rede entra no terreno por uma ponta de rua junto à portaria, e o acesso da torre passa nesse mesmo ponto (ou os dois projetam na mesma ponta de um trecho sem saída). O resto do trajeto está nos afastamentos, que vão na observação do caso: o acesso da portaria fica de 4,9 m a 19,5 m da rede.
  - **Núcleo:** a `cascata` não anula mais `road_network`; quem anula é o `gravar`, e os AQGs gravados não mudam (conferido nas 26 gravações da E7).

### G6 — Histórico

- **Tarefas:** G4 ("o que mudou entre a solução mãe e a filha?") e G5 ("desfaça as duas últimas mudanças").
- **Passos:** G4 usa a gravação da D1 como filha; a resposta esperada é a diferença calculada por script (torre movida e vetor, vagas que mudaram, deltas de corte, aterro e indicadores). G5 grava a sequência D1 → D3; a resposta esperada é o arquivo original.
- **Aceite:** resposta esperada gerada sem LLM e conferida contra as duas gravações.
- **Resultado (10/11/2026): concluída.** `evals/benchmark/historico.py` (lado do repo, sem motor) escreve os casos em `casos_edicao.json`.
  - **Edições a partir da base:** o estado inicial que a RECOD lê é a base (G0), mas as edições eram resolvidas sobre o arquivo cru, e a cascata reordena os `placed_objects`. Em 3 arquivos (`6ace7b93`, `6ace7f0d`, `6ace84f4`) a torre tinha outro id na base, e a chamada certa cairia em "fora do roteiro". `edicoes.py` passou a ler a base, e todas as edições foram regravadas: vereditos e violações iguais, só os ids mudam nesses 3. As válidas saem com os mesmos AQGs, exceto uma E3 com torres reposicionadas (`6ace3c16/ruim`, mesmas torres, determinística); as inválidas, que gravam o estado sem cascata, mudam porque partem da base.
  - **G4** (mãe = base, filha = D1) nos 15 arquivos com D1 válida: torre movida com ids e vetor, vagas (mantidas, removidas, novas), corte, aterro e muro, e indicadores alterados. Conferido: a única torre movida é a da D1, a 5 m.
  - **G5 = D1 → E7**, não D1 → D3: a D3 só existe nos 2 arquivos com APP, e neles a D1 é inválida. A E7 parte do estado gravado da D1 (`edicoes.py g5`), com `apos` (a chave da D1) nos argumentos para não colidir com a E7 sobre a base; a resposta esperada é a base.
  - **G5** em 13 arquivos (das 15 D1 válidas, 2 sem terraplenagem): todas as E7 válidas, sem mexer nas torres da D1; duas passadas dão os mesmos AQGs.
  - **Binários da D8 fora do checkout do VT:** às 15:30 de 10/11/2026 o checkout do VT passou para teodora 17.3.3, teseu 0.6.0 e ibitira 6.0.0, e a E7 parou de rodar. Todas as gravações anteriores são de antes da troca. Os binários da D8 agora ficam em `data/benchmark/bin` (seção 0.1), e o `lib` continua vindo do checkout pelo `lib.pth` do venv. Um worktree do VT não isolaria nada, porque o `lib.pth` aponta para o checkout. Nesse ambiente, D1, E1, E3 e E7 de um arquivo reproduzem as gravações byte a byte.

### T0 — Tools entregues

- **Arquivos:** `evals/benchmark/tools/` com três módulos: `calculo.py` (as 5 da D4, sobre o parser deste repo), `edicao.py` (cada tool de edição resolve a chave canônica e devolve o gravado ou "fora do roteiro") e `linha_de_base.py` (as 16 tools atuais, sem o `RunContext` do agno).
- **Contrato:** funções Python puras com descrição em JSON Schema, para a RECOD plugar no framework de agente que quiser.
- **Aceite:** nenhum import do VT, `buildings` ou `maga` (teste que falha se aparecer); toda chamada canônica dos casos devolve a gravação; chamada não gravada devolve "fora do roteiro".
- **Resultado (10/11/2026): concluída.** `evals/benchmark/tools/` com os três módulos e um registro (`GRUPOS`, nome → função, e `esquemas(grupos)`, o JSON Schema de cada tool, gerado pelo mesmo `Function.from_callable` do agno que monta as tools do agente).
  - **Estado:** toda tool, exceto `calcular`, recebe `estado`, o caminho do AQG atual, como primeiro argumento. Quem passa é o harness da RECOD, e o schema que vai ao modelo não o inclui (o papel do `RunContext` no agente deste repo).
  - **Edição:** a tool acha, no índice, de onde o estado veio (a base ou uma gravação, que vira o `apos`) e a gravação com os mesmos argumentos, comparados depois de normalizar (`5` = `5.0`, `"1:1,5"` = `"1:1.5"`, maiúsculas, ordem do mix). Devolve `{"resposta", "estado"}`: a resposta vai ao modelo (veredito, violações, etapas e, quando há, vagas, reposicionadas, removidas ou erro); o estado é o AQG seguinte. Sem gravação: `{"erro": "fora do roteiro"}` e estado `None`. `trocar_familia`, `resolver_estacionamento`, `recalcular_indicadores` e `validar` existem, mas nenhuma tarefa da fatia as grava.
  - **Cálculo:** 4 tools, pelo ajuste da D2 no PRD. `relacao_espacial` mede como o gabarito (torre pelo pavimento-tipo, borda a borda) e confere com a B9 e a B11 de `checks.json` nos 37 arquivos; `calcular` só aceita aritmética (`ast`, sem nomes nem chamadas).
  - **Linha de base:** as 16 tools com a mesma função, descrição e schema do agente; o documento vem de um `RunContext` montado com o AQG do estado.
  - **Aceite** em `tests/test_benchmark_tools.py`: importar as tools não carrega `buildings`, `maga`, `errata`, `persistente` nem `lib`; todas as entradas do índice, chamadas pela tool a partir do estado de origem, devolvem a gravação e o veredito; formas equivalentes caem na mesma gravação; o que não foi gravado devolve "fora do roteiro".

### T1 — Casos de edição e controles

- **Arquivo:** `evals/benchmark/casos_edicao.json`: tarefa, arquivo, pergunta com a referência por descrição, chamada canônica esperada, gravação esperada e resposta esperada.
- **Controles do instrumento:** um cliente-gabarito (chama exatamente as chamadas canônicas) tem de acertar 100%; um cliente-vândalo (acerta e faz uma edição a mais) tem de ser acusado de dano colateral em 100%. Sem os dois, nenhum número do benchmark vale.

### E0 — Entrega à RECOD

- Depende do P3. Pacote das tools e dos casos, gravações, e um README curto: como plugar as tools, o que a estrutura deles precisa fornecer (conversão AQG → estrutura, mapa de ids) e como medir (métricas do PRD).

## 6. Avaliação final

- Os dois controles da T1 passam.
- A linha de base (D10) responde as tarefas de leitura com as 16 tools e o gabarito confere.
- Uma rodada curta com um modelo real no AQG cru, para medir tokens de referência antes de a RECOD trazer a estrutura dela.
