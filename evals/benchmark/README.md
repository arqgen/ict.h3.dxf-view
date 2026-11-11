# Benchmark de queries sobre o AQG

Tarefas de leitura e de edição sobre projetos AQG, com as tools que respondem a elas e o gabarito de cada caso. Requisitos e decisões em [`PRD-queries.md`](../../PRD-queries.md); construção em [`IMPLEMENTATION-queries.md`](../../IMPLEMENTATION-queries.md).

## Instalação

1. Clone este repo e rode `uv sync`.
2. Descompacte `entrega.zip` na raiz do repo. Ele cria `data/aqg/` (os AQGs originais), `data/benchmark/gravacoes/` (os AQGs gravados das edições) e `data/benchmark/redes/` (as redes viárias).
3. Confira: `uv run python -m evals.benchmark.controles` tem de terminar com os dois controles `ok`.

## Casos

| Arquivo | Tarefas | Estado inicial |
| --- | --- | --- |
| `casos.json` | Leitura (L, A, B): pergunta e `resposta_esperada`; `status: fora` quando a tarefa não se aplica ao arquivo | `data/aqg/<arquivo>` |
| `casos_edicao.json` | Edição (D, E) e histórico (G): `chamadas_esperadas`, `estado_esperado` e `resposta_esperada` | O último item de `historico` |

## Tools

```python
from evals.benchmark.tools import GRUPOS, esquemas

tools = GRUPOS["calculo"] | GRUPOS["edicao"]  # nome -> função Python
schemas = esquemas(["calculo", "edicao"])  # JSON Schema que vai ao modelo
```

- **`estado`:** toda tool, exceto `calcular`, recebe como primeiro argumento o caminho do AQG atual. Quem passa é o seu harness, e o schema que vai ao modelo não inclui esse argumento.
- **Edição:** as tools devolvem `{"resposta", "estado"}`. A `resposta` vai ao modelo; o `estado` é o AQG seguinte, que a sua estrutura passa a mostrar. As tools não rodam motor nenhum: devolvem o AQG que a Arqgen gravou para aquela chamada. Uma chamada que não foi gravada devolve `{"erro": "fora do roteiro"}`, o estado não muda, e isso conta nas métricas.
- **Linha de base** (`GRUPOS["linha_de_base"]`): as 16 tools do assistente deste repo, só para as tarefas de leitura.
- **Histórico:** `desfazer` e `diff_versoes` não são tools entregues, porque o histórico é da estrutura de vocês. `controles.executar` traz uma versão de referência, com índices nas versões.

## O que a estrutura de vocês fornece

- **Conversão AQG → estrutura:** o que o modelo lê no lugar do arquivo cru.
- **Mapa de ids:** as tools endereçam elementos pelo id deste repo, `p<i>`, que é o índice em `solution.placed_objects`. Após cada edição, o mapa tem de ser refeito sobre o `estado` novo.

## Como medir

Por tarefa: tokens de entrada (a estrutura mais o que as tools devolvem), tokens de saída, chamadas de tool, acerto e dano colateral.

- **Acerto (edição):** o cliente fez as `chamadas_esperadas` (argumentos normalizados, `5` = `5.0`) e a resposta confere com a `resposta_esperada`.
- **Dano colateral:** o cliente fez alguma chamada que muda o estado sem estar entre as esperadas, inclusive uma que caiu "fora do roteiro".

`controles.avaliar(caso, chamadas, resposta)` calcula as duas. A resposta é comparada por igualdade exata dos dados; a resposta de um modelo real, que vem em texto, precisa antes ser extraída para esse formato.

**Controles:** um cliente que faz exatamente as chamadas esperadas tem de acertar 100% sem dano; um que acerta e faz uma edição a mais tem de ser acusado de dano em 100%. Rode os dois (passo 3 da instalação) antes de publicar qualquer número.
