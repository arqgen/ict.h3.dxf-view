"""Zip dos dados do benchmark para a RECOD (P3): o que os casos e as tools leem e o
Git não versiona. Os binários dos motores (`data/benchmark/bin`) ficam de fora (D1).

    uv run python -m evals.benchmark.entrega   # -> data/benchmark/entrega.zip

Os caminhos no zip são relativos à raiz do repo: descompacte na raiz.
"""

import json
import zipfile
from pathlib import Path

from evals.benchmark.historico import ROOT

BENCH = ROOT / "evals" / "benchmark"
SAIDA = ROOT / "data" / "benchmark" / "entrega.zip"


def arquivos() -> list[Path]:
    casos = json.loads((BENCH / "casos.json").read_text())
    casos += json.loads((BENCH / "casos_edicao.json").read_text())
    indice = json.loads((BENCH / "gravacoes.json").read_text())
    aqgs = {ROOT / "data" / "aqg" / c["arquivo"] for c in casos}
    gravacoes = {ROOT / v["aqg"] for v in indice.values() if "aqg" in v}
    redes = set((ROOT / "data" / "benchmark" / "redes").glob("*.json"))
    return sorted(aqgs | gravacoes | redes)


def main() -> None:
    paths = arquivos()
    with zipfile.ZipFile(SAIDA, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in paths:
            zf.write(path, path.relative_to(ROOT))
    print(f"{len(paths)} arquivos, {SAIDA.stat().st_size / 1e6:.0f} MB em {SAIDA}")


if __name__ == "__main__":
    main()
