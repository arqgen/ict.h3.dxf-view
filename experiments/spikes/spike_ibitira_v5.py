"""spike_ibitira com um adaptador de protocolo: maga_ibitira 6 -> binário ibitira 5.2.0.

Na v6 `road_graph` é lista de pares (largura, linhas); a v5 espera um par só.
"""

import json
import subprocess
import sys

import lib.problem.earth_movement as em
from errata.result import Err, Ok
from maga.ibitira.protocol import FeasibilitySolution

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import spike_ibitira as s  # noqa: E402


def invoke_v5(problem, executable):
    payload = problem.serialize()
    graphs = payload["road_graph"]
    if len(graphs) > 1:
        return Err(f"adaptador: {len(graphs)} larguras de via, v5 aceita uma")
    payload["road_graph"] = graphs[0] if graphs else [0.0, []]
    proc = subprocess.run(
        [executable, "feasibility"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=600,
    )
    if proc.returncode:
        return Err(f"ibitira v5: {proc.stderr[:200]}")
    return Ok(FeasibilitySolution.create(json.loads(proc.stdout)))


em.invoke_ibitira = invoke_v5
s.compute_earthmoving = em.compute_earthmoving

if __name__ == "__main__":
    rows = [r for r in (s.spike(f) for f in (sys.argv[1:] or s.FILES)) if r]
    json.dump(rows, open(__file__.replace(".py", "_resultado.json"), "w"), indent=1)
    for r in rows:
        a, n = r.get("arquivo_mov") or {}, r.get("novo_mov") or {}
        print(r["arquivo"][:28], r["terraplenagem"].split("/")[2], r["etapa"][:80])
        if r["etapa"] == "ok":
            print(
                "  corte",
                a.get("corte"),
                n.get("corte"),
                "| aterro",
                a.get("aterro"),
                n.get("aterro"),
                "| muro",
                a.get("muro_comprimento"),
                n.get("muro_comprimento"),
                "| z",
                r["arquivo_z"][:4],
                r["novo_z"][:4],
                "| t",
                r.get("terraplenagem_s"),
            )
