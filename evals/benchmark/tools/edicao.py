"""Tools de edição entregues à RECOD (D1): devolvem a gravação, sem rodar motor.

Cada tool procura, no índice das gravações, a chamada feita a partir de `estado`
(a base ou o resultado de uma edição anterior) com os mesmos argumentos. Devolve
`{"resposta", "estado"}`: a `resposta` vai ao modelo (veredito, violações, etapas);
o `estado` é o AQG seguinte, que o harness passa a usar e a estrutura mostra. Sem
gravação, a resposta é "fora do roteiro" e o estado não muda (`None`).
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
INDICE = ROOT / "evals" / "benchmark" / "gravacoes.json"
OCULTOS = {"arquivo", "tool", "args", "versoes", "segundos", "aqg"}


@lru_cache(maxsize=1)
def _indice() -> dict[str, dict]:
    return json.loads(INDICE.read_text())


def _norm(valor: Any) -> Any:
    """Formas equivalentes do mesmo argumento: 5 e 5.0, "1:1,5" e "1:1.5"."""
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, int | float):
        return float(valor)
    if isinstance(valor, str):
        return valor.strip().lower().replace(",", ".")
    if isinstance(valor, dict):
        return sorted((_norm(k), _norm(v)) for k, v in valor.items())
    if isinstance(valor, list):
        return [_norm(v) for v in valor]
    return valor


def _gravado(estado: str, tool: str, args: dict[str, Any]) -> dict:
    path = Path(estado).resolve()
    rel = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else estado
    indice = _indice()
    origem = next(((k, v) for k, v in indice.items() if v.get("aqg") == rel), None)
    if origem is None:
        return {"resposta": {"erro": f"estado desconhecido: {estado}"}, "estado": None}
    key, entry = origem
    pedido = {k: v for k, v in args.items() if v is not None}
    if entry["tool"] != "base":
        pedido["apos"] = key
    alvo = _norm(pedido)
    gravado = next(
        (
            v
            for v in indice.values()
            if v["arquivo"] == entry["arquivo"]
            and v["tool"] == tool
            and _norm(v["args"]) == alvo
        ),
        None,
    )
    if gravado is None:
        return {"resposta": {"erro": "fora do roteiro"}, "estado": None}
    resposta = {k: v for k, v in gravado.items() if k not in OCULTOS}
    return {"resposta": resposta, "estado": gravado.get("aqg")}


def mover_torre(estado: str, torre: str, distancia: float, sentido: str) -> dict:
    """Move uma torre e refaz estacionamento, terraplenagem e indicadores.

    A tool resolve a direção; o modelo não calcula vetor.

    Args:
        torre: id da torre (`p<i>`).
        distancia: deslocamento em metros.
        sentido: "fundos" afasta a torre da linha de frente mais próxima, para
            dentro do terreno.
    """
    args = {"torre": torre, "distancia": distancia, "sentido": sentido}
    return _gravado(estado, "mover_torre", args)


def remover_torre(estado: str, torre: str) -> dict:
    """Remove uma torre e refaz estacionamento, terraplenagem e indicadores.

    Args:
        torre: id da torre (`p<i>`).
    """
    return _gravado(estado, "remover_torre", {"torre": torre})


def definir_pavimentos(estado: str, torre: str, total: int) -> dict:
    """Muda o número de pavimentos de uma torre (a família ganha um tipo irmão).

    Args:
        torre: id da torre (`p<i>`).
        total: número total de pavimentos.
    """
    return _gravado(estado, "definir_pavimentos", {"torre": torre, "total": total})


def alterar_programa(
    estado: str,
    mix: dict[str, float] | None = None,
    chave: str | None = None,
    valor: float | None = None,
) -> dict:
    """Altera o programa: o mix de tipologias ou um parâmetro do programa.

    Mantém a implantação; torres que ficarem inválidas com a família nova são
    reposicionadas, e estacionamento em diante é refeito.

    Args:
        mix: percentual por tipologia, pelo class_path do apartamento (ex.:
            {"/building/apartamento/2q/40_71": 60}).
        chave: nome do parâmetro do programa (ex.: "ParkingLotPerUnit").
        valor: novo valor do parâmetro `chave`.
    """
    args = {"mix": mix, "chave": chave, "valor": valor}
    return _gravado(estado, "alterar_programa", args)


def resolver_terraplenagem(estado: str, aterro: str, corte: str, muro: str) -> dict:
    """Refaz só a terraplenagem e os indicadores com outro talude.

    Args:
        aterro: inclinação do talude de aterro, como "1:2".
        corte: inclinação do talude de corte, como "1:1,5".
        muro: altura máxima do talude antes de virar muro, ou "sem limite".
    """
    args = {"aterro": aterro, "corte": corte, "muro": muro}
    return _gravado(estado, "resolver_terraplenagem", args)


def trocar_familia(estado: str, torre: str, familia: str) -> dict:
    """Troca a família de uma torre pela indicada.

    Args:
        torre: id da torre (`p<i>`).
        familia: class_path da família nova.
    """
    return _gravado(estado, "trocar_familia", {"torre": torre, "familia": familia})


def resolver_estacionamento(estado: str) -> dict:
    """Refaz estacionamento, terraplenagem e indicadores a partir das torres."""
    return _gravado(estado, "resolver_estacionamento", {})


def recalcular_indicadores(estado: str) -> dict:
    """Recalcula os indicadores e as anotações do projeto."""
    return _gravado(estado, "recalcular_indicadores", {})


def validar(estado: str) -> dict:
    """Valida as torres: cada uma sozinha, cada par e o conjunto (agregados)."""
    return _gravado(estado, "validar", {})
