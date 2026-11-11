"""Gera `QUERIES.md`: cada query, como a resposta é conferida e o resultado esperado
em cada AQG, a partir de `casos.json` e `casos_edicao.json`.

    uv run python -m evals.benchmark.documento
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any

OUT = Path(__file__).parent
DOC = OUT / "QUERIES.md"

# Como a resposta esperada é calculada, só com termos do AQG.
LEITURA = {
    "L1": "Instâncias de família de torre em `solution.placed_objects`; confere com "
    "`TotalDeTorres` dos `outputs`.",
    "L2": "`CAMaximoExigido` dos inputs do terreno e `CAProjetado` dos `outputs`.",
    "L3": "Instâncias de família de vaga em `solution.placed_objects`.",
    "L4": "A torre cujo pavimento-tipo desenhado fica mais perto da frente (layer "
    "`AQG_FRENTE`), borda a borda; o label da família e `total_pavimentos` das "
    "propriedades dela.",
    "L5": "`UnidadesPorTipologia` dos `outputs`.",
    "L6": "`AreaDoTerreno` e `AreaUtil` do `processed_info` do terreno.",
    "L7": "Layers dos elementos do terreno (`site.elements`).",
    "L8": "`AfastamentoProjetado.entre_blocos` dos `outputs`.",
    "A1": "piso(`AreaDoTerreno` × `CAMaximoExigido` ÷ área computável por unidade), "
    "com a área por unidade da própria solução: `AreaTotalConstruidaComputavel` ÷ "
    "`TotalDeUnidades`. A base é `AreaDeMatricula` quando `AreaBaseDeCalculo` "
    "manda.",
    "B2": "`EstacionamentoProjetado` (= `ViarioProjetado` + `VagasProjetadas`) e "
    "`ProjecaoTorres` dos `outputs`: área (m²) e percentual do terreno.",
    "B5": "O AQG não guarda a rede viária: a Arqgen a regerou para cada arquivo, e a "
    "resposta é o menor caminho nela, do acesso da portaria ao de cada torre (m). "
    "A tool `caminho` faz esse cálculo.",
    "B8": "`solution.strategy`: as etapas que geraram a solução, na ordem.",
    "B9": "Distância borda a borda entre o pavimento-tipo de cada torre e a vaga mais "
    "próxima; a torre fica sem vaga se ela passa de 50 m.",
    "B11": "A torre mais próxima da portaria (borda a borda); unidades por pavimento "
    "× min(5, pavimentos com unidades).",
}
EDICAO = {
    "D1": "A torre mais próxima da frente sobe 5 m na perpendicular à frente, para "
    "dentro do terreno; depois, vagas, viário, terraplenagem e indicadores são "
    "refeitos.",
    "D3": "Só nos arquivos com APP (layer `AQG_APP`). Unidades perdidas = "
    "`TotalDeUnidades` antes − depois.",
    "D6": "A torre mais próxima da portaria passa a ter 20 pavimentos. É inválido "
    "quando sai da faixa de pavimentos que o terreno e o programa permitem.",
    "E1": "`ParkingLotPerUnit` = 1,5 no `archprog`. Vagas necessárias = "
    "teto(unidades × 1,5); o déficit é necessárias − projetadas.",
    "E3": "Mix de 60% `2q/40_71` e 40% `1q/27_97`. Cada torre troca para a família "
    "equivalente com o programa novo; a que deixar de caber é reposicionada ou "
    "removida.",
    "E7": "Talude de aterro 1:2, de corte 1:1,5, sem muro. Só a terraplenagem e os "
    "indicadores mudam; torres e vagas ficam iguais.",
    "G4": "A mãe é o estado inicial e a filha, o resultado da D1. A resposta é a "
    "diferença: torre movida e vetor, vagas, corte, aterro e indicadores.",
    "G5": "Sequência D1 → E7 sobre o estado inicial. Desfazer as duas volta ao "
    "estado inicial.",
}
FORA = [
    ("sem portaria", "sem portaria"),
    ("sem etapa de estacionamento", "sem estacionamento"),
    ("não admitido", "arquivo fora das edições"),
    ("arquivo sem EstacionamentoProjetado", "sem vagas"),
    ("nenhuma vaga", "sem vagas"),
    ("arquivo sem solution.strategy", "versão antiga, sem `solution.strategy`"),
    ("AMBÍGUO", "empate na distância à frente"),
]


def _num(v: Any) -> str:
    if isinstance(v, float):
        return (
            f"{v:,.2f}".rstrip("0")
            .rstrip(".")
            .replace(",", "_")
            .replace(".", ",")
            .replace("_", ".")
        )
    return str(v)


def fmt(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "sim" if v else "não"
    if isinstance(v, dict):
        return "; ".join(f"{k}: {_aninhado(x)}" for k, x in v.items()) or "—"
    if isinstance(v, list):
        return ", ".join(fmt(x) for x in v) or "nenhuma"
    return _num(v)


def _aninhado(v: Any) -> str:
    return f"({fmt(v)})" if isinstance(v, dict) else fmt(v)


def _fora(obs: str) -> str:
    return next(m for prefixo, m in FORA if obs.startswith(prefixo))


def _tabela(cab: list[str], linhas: list[list[str]]) -> list[str]:
    return [
        "| " + " | ".join(cab) + " |",
        "| " + " | ".join("---" for _ in cab) + " |",
        *("| " + " | ".join(c.replace("|", "\\|") for c in li) + " |" for li in linhas),
    ]


def _edicao(caso: dict) -> list[str]:
    r = caso["resposta_esperada"]
    if caso["tarefa"] == "G4":
        movida = r["torres_movidas"][0]
        terra = r["terraplenagem"]
        return [
            f"{movida['mae']}, vetor ({fmt(movida['vetor'])}) m",
            fmt({"mãe": r["vagas"]["mae"], "filha": r["vagas"]["filha"]}),
            fmt({k: f"{fmt(v['mae'])} → {fmt(v['filha'])}" for k, v in terra.items()}),
            str(len(r["indicadores"]) + len(r["outros_indicadores_alterados"])),
        ]
    if caso["tarefa"] == "G5":
        return [Path(caso["estado_esperado"]).stem]
    detalhe = {
        k: r[k]
        for k in ("unidades_perdidas", "vagas", "pavimentos_com_unidades")
        if k in r
    }
    for k in ("reposicionadas", "removidas"):
        if r.get(k):
            detalhe[k] = len(r[k])
    regras = sorted({v["regra"] for v in r.get("violacoes", [])})
    return [
        fmt(caso["chamadas_esperadas"][0]["args"]),
        r["veredito"],
        fmt(regras) if regras else "—",
        fmt(detalhe) if detalhe else "—",
        Path(caso["estado_esperado"]).stem,
    ]


CABECALHO = {
    "G4": ["AQG", "Torre movida", "Vagas", "Terraplenagem", "Indicadores alterados"],
    "G5": ["AQG", "Estado esperado"],
}
CABECALHO_EDICAO = ["AQG", "Argumentos", "Veredito", "Violações", "Resposta", "Estado"]


def main() -> None:
    leitura = json.loads((OUT / "casos.json").read_text())
    edicao = json.loads((OUT / "casos_edicao.json").read_text())
    arquivos = sorted({c["arquivo"] for c in leitura})
    cod = {a: f"A{i:02d}" for i, a in enumerate(arquivos, 1)}
    admitidos = {c["arquivo"] for c in edicao}

    md = [
        "# Queries e resultados esperados",
        "",
        "Gerado por `evals/benchmark/documento.py` a partir de `casos.json` e "
        "`casos_edicao.json`; não edite à mão. Cada resposta esperada foi "
        "calculada por script sobre o AQG, sem LLM. Como usar as tools e medir: "
        "[`README.md`](README.md).",
        "",
        "## AQGs",
        "",
        f"{len(arquivos)} AQGs nas queries de leitura. As de edição rodam em "
        f"{len(admitidos)} deles: os arquivos em que a Arqgen reproduz a solução "
        "do AQG ao reprocessá-lo sem edição. Nesses, o estado inicial é o AQG "
        "reprocessado, que difere do original só em indicadores que o cálculo "
        "atual dá diferente.",
        "",
        *_tabela(
            ["Código", "Arquivo (`data/aqg/`)", "Edição"],
            [[cod[a], a, "sim" if a in admitidos else "—"] for a in arquivos],
        ),
        "",
        "## Leitura",
        "",
        "Status `não se aplica`: a pergunta não faz sentido no arquivo, e o caso "
        "fica fora da medição.",
    ]
    por_tarefa: dict[str, list[dict]] = {}
    for c in leitura:
        por_tarefa.setdefault(c["tarefa"], []).append(c)
    for tarefa, casos in por_tarefa.items():
        ok = sum(c["status"] == "ok" for c in casos)
        md += [
            "",
            f"### {tarefa} — {casos[0]['pergunta']}",
            "",
            f"**Conferência:** {LEITURA[tarefa]}",
            "",
            f"{ok} com resposta, {len(casos) - ok} não se aplica.",
            "",
            *_tabela(
                ["AQG", "Resposta esperada"],
                [
                    [
                        cod[c["arquivo"]],
                        fmt(c["resposta_esperada"])
                        if c["status"] == "ok"
                        else f"não se aplica: {_fora(c['observacao'])}",
                    ]
                    for c in sorted(casos, key=lambda c: cod[c["arquivo"]])
                ],
            ),
        ]

    md += [
        "",
        "## Edição e histórico",
        "",
        'O modelo resolve a referência ("a torre mais próxima da frente") e chama '
        "a tool com os argumentos da tabela; a torre é o id `p<i>`, o índice em "
        "`solution.placed_objects`. A tool devolve o veredito e passa o estado "
        "para o AQG da coluna Estado (em `data/benchmark/gravacoes/`):",
        "",
        "- **válido:** a edição passou nas regras do terreno e do programa, e o "
        "que depende dela foi refeito;",
        "- **inválido:** a edição viola uma regra (coluna Violações), e o estado é "
        "o AQG com a edição, sem refazer o resto;",
        "- **erro:** a Arqgen não conseguiu refazer a solução, e o estado não muda.",
    ]
    por_tarefa = {}
    for c in edicao:
        por_tarefa.setdefault(c["tarefa"], []).append(c)
    for tarefa, casos in por_tarefa.items():
        vereditos = Counter(
            c["resposta_esperada"]["veredito"]
            for c in casos
            if c["resposta_esperada"] and "veredito" in c["resposta_esperada"]
        )
        chamada = casos[0]["chamadas_esperadas"][0]["tool"]
        md += [
            "",
            f"### {tarefa} — {casos[0]['pergunta']}",
            "",
            f"**Chamada:** `{chamada}`. **Conferência:** {EDICAO[tarefa]}",
            "",
            f"{len(casos)} casos"
            + (f": {fmt(dict(vereditos))}." if vereditos else "."),
            "",
            *_tabela(
                CABECALHO.get(tarefa, CABECALHO_EDICAO),
                [
                    [cod[c["arquivo"]], *_edicao(c)]
                    for c in sorted(casos, key=lambda c: cod[c["arquivo"]])
                ],
            ),
        ]
    DOC.write_text("\n".join(md) + "\n")
    print(f"{DOC}: {len(leitura)} casos de leitura, {len(edicao)} de edição")


if __name__ == "__main__":
    main()
