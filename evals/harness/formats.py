"""What the model reads besides the view: the answer protocol and each task's format.

The benchmark's answer key compares exact data, so the model ends by calling
`responder` with the value in the task's format. The format names the keys the
answer key uses and is the same for every variant: only the view changes between
them. The text here is in pt-BR, like the benchmark's questions and tools.
"""

import json

PROTOCOL = """## Rodada de avaliação

Não há usuário para tirar dúvidas nem para confirmar nada: resolva a tarefa sozinho.

- Use só o documento e as tools. Não invente valor.
- Termine chamando `responder` uma única vez, com `valor_json` no formato pedido na \
tarefa. A rodada acaba nessa chamada.
- Edite só o que a tarefa pede."""

EDIT_ANSWER = (
    "o objeto `resposta` devolvido pela tool de edição que atendeu ao pedido, "
    "sem mudar nada."
)

FORMATS = {
    "L1": "número inteiro.",
    "L2": '{"CAMaximoExigido": número, "CAProjetado": número}',
    "L3": "número inteiro.",
    "L4": '{"familia": nome da família da torre, "total_pavimentos": número inteiro}',
    "L5": "{<tipologia>: número de unidades}, com a tipologia identificada como no "
    "projeto.",
    "L6": '{"AreaDoTerreno": número, "AreaUtil": número}, em m².',
    "L7": "lista com o layer de cada tipo de elemento do terreno, sem repetição, em "
    "ordem alfabética.",
    "L8": "número, em metros.",
    "A1": "número inteiro, arredondado para baixo.",
    "B2": '{"EstacionamentoProjetado": X, "ViarioProjetado": X, "VagasProjetadas": X, '
    '"ProjecaoTorres": X}, com X = {"area": número em m², "percentual": número}, ou '
    "null quando o projeto não traz o valor.",
    "B5": "{<id da torre>: distância em metros ou 'inalcançável'}, uma por torre.",
    "B8": "lista das estratégias, na ordem em que aparecem no projeto.",
    "B9": '{"torres_sem_vaga_em_50m": [ids das torres, em ordem alfabética], '
    '"existe": true ou false}',
    "B11": "número inteiro.",
    "D1": EDIT_ANSWER,
    "D3": EDIT_ANSWER + ' Se o veredito for "valido", acrescente "unidades_perdidas": '
    "número inteiro de unidades a menos no projeto.",
    "D6": EDIT_ANSWER,
    "E1": EDIT_ANSWER + ' Se o veredito for "valido", acrescente "vagas": '
    '{"necessarias": TotalDeUnidades depois da edição x vagas por unidade, '
    'arredondado para cima, "projetadas": vagas desenhadas depois da edição, '
    '"deficit": necessarias - projetadas, "na_base": vagas desenhadas antes da '
    "edição}.",
    "E3": EDIT_ANSWER,
    "E7": EDIT_ANSWER,
    "G4": "o objeto devolvido por `diff_versoes`, sem mudar nada.",
    "G5": "null.",
}


def task_message(case: dict) -> str:
    """The user message: the question, the versions (in edits) and the format."""
    parts = [case["pergunta"]]
    if "historico" in case:
        lines = ["0: a base"]
        for i, edit in enumerate(case.get("edicoes", []), start=1):
            # `apos` is the key of the previous recording: internal index data.
            args = {k: v for k, v in edit["args"].items() if k != "apos"}
            lines.append(f"{i}: após {edit['tool']}({json.dumps(args)})")
        parts.append(
            "Versões do projeto (a última é a atual, a do documento):\n"
            + "\n".join(lines)
        )
    parts.append(f"Formato de `valor_json`: {FORMATS[case['tarefa']]}")
    return "\n\n".join(parts)
