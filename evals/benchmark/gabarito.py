"""Gabarito (resposta esperada, sem LLM) das tarefas de leitura sobre AQGs.

Roda de dentro do repo, reusando o parser e as medidas das tools:

    PYTHONPATH=. uv run python evals/benchmark/gabarito.py

Escreve casos.json e checks.json ao lado deste arquivo.
"""

import glob
import json
from decimal import ROUND_FLOOR, Decimal
from pathlib import Path
from typing import Any

from evals.benchmark.tools.calculo import REDES, caminho
from src.ai_modules.tools.cad_tools.query_tools import _edge_prims
from src.cad.geometry import Prim, min_distance
from src.cad.model import CadModel, _category, load_aqg, tower_units

OUT = Path(__file__).parent
AQG = Path(__file__).resolve().parents[2] / "data" / "aqg"
FILES = (
    sorted(glob.glob(str(AQG / "favoritadas" / "*.json")))
    + sorted(glob.glob(str(AQG / "avaliadas" / "*" / "*.json")))
    + sorted(glob.glob(str(AQG / "solucoes-18x" / "*.json")))
)
TIE = 0.01
RAIO_VAGA = 50.0
ADMISSAO = {r["arquivo"]: r for r in json.loads((OUT / "admissao.json").read_text())}

PERGUNTAS = {
    "L1": "Quantas torres tem a solução?",
    "L2": "Qual o CA máximo exigido e o projetado?",
    "L3": "Quantas vagas foram desenhadas?",
    "L4": "Qual a família da torre mais próxima da frente e quantos pavimentos "
    "ela tem?",
    "L5": "Quantas unidades há de cada tipologia?",
    "L6": "Qual a área do terreno e a área útil?",
    "L7": "Que elementos o terreno tem?",
    "L8": "Qual o afastamento exigido entre as torres?",
    "A1": "Quantas unidades este terreno comporta pelo CA, mantido o mix desta "
    "solução?",
    "B2": "Quanto do terreno vai para o carro?",
    "B5": "Qual a distância de carro da portaria a cada torre?",
    "B8": "Que estratégia gerou esta solução?",
    "B9": "Alguma torre fica sem vaga num raio de 50 m?",
    "B11": "Quantas unidades eu perderia se a torre mais próxima da portaria "
    "tivesse 5 pavimentos a menos?",
}


def dec(x: float) -> Decimal:
    return Decimal(str(x))


def trunc2(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_FLOOR)


def r3(x: float) -> float:
    return round(x, 3)


def units_by_typology(props: dict[str, Any]) -> dict[str, int]:
    """Unidades por tipologia de UMA torre, como `calc_unidades_by_tipologia`.

    `Tower` soma pav_tipo x n e terreo x n; `DynamicTower3d` multiplica as
    tipologias por `n_pavimentos_unidades`.
    """
    result: dict[str, int] = {}
    if props.get("type") == "Tower":
        for key in ("pav_tipo", "terreo"):
            group = props.get(key) or {}
            for hid, n in (group.get("tipologias") or {}).items():
                result[hid] = result.get(hid, 0) + n * group.get("n", 0)
        return result
    for hid, n in (props.get("tipologias") or {}).items():
        result[hid] = n * props.get("n_pavimentos_unidades", 0)
    return result


def ranking(model: CadModel, towers: list[str], target: list[Prim]):
    return sorted(
        ((min_distance(_edge_prims(model, t), target), t) for t in towers),
        key=lambda item: item[0],
    )


def caso(tarefa, arquivo, resposta, fonte, obs="", status="ok") -> dict:
    return {
        "tarefa": tarefa,
        "arquivo": arquivo,
        "pergunta": PERGUNTAS[tarefa],
        "status": status,
        "resposta_esperada": resposta,
        "fonte": fonte,
        "observacao": obs,
    }


def run_file(path: str) -> tuple[list[dict], dict]:
    raw = json.loads(Path(path).read_bytes())
    model = load_aqg(Path(path).read_bytes(), path)
    arq = str(Path(path).relative_to(AQG))
    outputs: dict[str, list[dict]] = {}
    for o in model.indicators["outputs"]:
        outputs.setdefault(o.get("type"), []).append(o)
    inputs = {o.get("type"): o for o in model.indicators["inputs"]}
    pinfo = {o.get("type"): o for o in model.indicators["processed_info"]}

    def out(t: str) -> dict | None:
        return outputs[t][0] if t in outputs else None

    towers = [
        i.id for i in model.instances.values() if _category(i.family_type) == "torre"
    ]
    vagas = [
        i.id for i in model.instances.values() if _category(i.family_type) == "vaga"
    ]
    portarias = [
        i.id for i in model.instances.values() if _category(i.family_type) == "portaria"
    ]
    props = {
        t: model.families[model.instances[t].family_index].properties for t in towers
    }
    casos: list[dict] = []
    chk: dict[str, Any] = {"arquivo": arq, "versao": raw.get("version")}

    # L1
    total = (out("TotalDeTorres") or {}).get("value")
    blocos = sorted({p.get("blocos") for p in props.values()})
    obs = "" if total == len(towers) else f"DIVERGE: TotalDeTorres={total}"
    casos.append(
        caso(
            "L1",
            arq,
            len(towers),
            f"instâncias PlacedFamily de família Tower/DynamicTower3d ({len(towers)}); "
            f"solution.outputs TotalDeTorres={total}",
            obs or f"confere com TotalDeTorres={total}; blocos por família={blocos}",
        )
    )
    chk["L1"] = {"desenhadas": len(towers), "TotalDeTorres": total, "blocos": blocos}

    # L2
    camax = inputs["CAMaximoExigido"]["value"]
    caproj = out("CAProjetado")["value"]
    casos.append(
        caso(
            "L2",
            arq,
            {"CAMaximoExigido": camax, "CAProjetado": caproj},
            "site.inputs CAMaximoExigido.value; solution.outputs CAProjetado.value",
            f"CABasico={inputs.get('CABasico', {}).get('value')} (não perguntado)",
        )
    )

    # L3
    nvp = (out("NumeroDeVagasProjetado") or {}).get("value")
    obs = []
    if not vagas:
        obs.append("nenhuma vaga desenhada no arquivo")
    if nvp is None:
        obs.append("arquivo sem NumeroDeVagasProjetado")
    elif nvp != len(vagas):
        obs.append(f"DIVERGE: NumeroDeVagasProjetado={nvp}")
    else:
        obs.append(f"confere com NumeroDeVagasProjetado={nvp}")
    casos.append(
        caso(
            "L3",
            arq,
            len(vagas),
            "instâncias PlacedFamily de família Vaga (parte /core desenhada)",
            "; ".join(obs),
        )
    )
    chk["L3"] = {"desenhadas": len(vagas), "NumeroDeVagasProjetado": nvp}

    # L4
    frente = [
        prim for e in model.entities if e.layer == "AQG_FRENTE" for prim in e.prims
    ]
    n_frente = sum(1 for e in model.entities if e.layer == "AQG_FRENTE")
    rank = ranking(model, towers, frente) if frente and towers else []
    chk["L4"] = [(t, r3(d)) for d, t in rank[:3]]
    if not rank:
        casos.append(caso("L4", arq, None, "AQG_FRENTE", "sem frente ou torre", "fora"))
    else:
        d0, t0 = rank[0]
        inst = model.instances[t0]
        fam = model.families[inst.family_index]
        ans = {
            "familia": fam.label,
            "total_pavimentos": fam.properties.get("total_pavimentos"),
        }
        fonte = (
            f"min_distance(pavimento-tipo desenhado, {n_frente} elemento(s) "
            f"AQG_FRENTE); families[{inst.family_index}].properties.total_pavimentos"
        )
        if len(rank) > 1 and rank[1][0] - d0 < TIE:
            tied = [t for d, t in rank if d - d0 < TIE]
            same = {
                (
                    model.families[model.instances[t].family_index].label,
                    model.families[model.instances[t].family_index].properties.get(
                        "total_pavimentos"
                    ),
                )
                for t in tied
            }
            casos.append(
                caso(
                    "L4",
                    arq,
                    None,
                    fonte,
                    f"AMBÍGUO: empate < {TIE} m entre {tied} a {r3(d0)} m; "
                    + (
                        f"todas com a mesma família/pavimentos {sorted(same)} "
                        "(resposta seria a mesma)"
                        if len(same) == 1
                        else f"famílias/pavimentos diferentes {sorted(same)}"
                    ),
                    "fora",
                )
            )
        else:
            nxt = f"; 2ª: {rank[1][1]} a {r3(rank[1][0])} m" if len(rank) > 1 else ""
            casos.append(
                caso(
                    "L4",
                    arq,
                    ans,
                    fonte,
                    f"torre {t0} a {r3(d0)} m da frente{nxt}; tipo {fam.type}, "
                    f"n_pavimentos_unidades={fam.properties.get('n_pavimentos_unidades')}",
                )
            )

    # L5
    upt = (out("UnidadesPorTipologia") or {}).get("value")
    tu = (out("TotalDeUnidades") or {}).get("value")
    soma: dict[str, int] = {}
    for t in towers:
        for hid, n in units_by_typology(props[t]).items():
            soma[hid] = soma.get(hid, 0) + n
    tu_helper = [tower_units(props[t]) for t in towers]
    tu_helper_total = (
        sum(u[1] for u in tu_helper) if all(u is not None for u in tu_helper) else None
    )
    obs = []
    if soma == upt:
        obs.append("confere com a soma por família (tipologias x pavimentos)")
    else:
        obs.append(f"DIVERGE da soma por família: {soma}")
    if tu is not None and sum(upt.values()) != tu:
        obs.append(f"DIVERGE: soma != TotalDeUnidades={tu}")
    if tu_helper_total != tu:
        obs.append(
            f"tower_units() do repo soma {tu_helper_total} != TotalDeUnidades={tu}"
        )
    casos.append(
        caso(
            "L5",
            arq,
            upt,
            "solution.outputs UnidadesPorTipologia.value",
            "; ".join(obs),
        )
    )
    chk["L5"] = {
        "UnidadesPorTipologia": upt,
        "soma_familias": soma,
        "TotalDeUnidades": tu,
        "tower_units_total": tu_helper_total,
    }

    # L6
    casos.append(
        caso(
            "L6",
            arq,
            {
                "AreaDoTerreno": pinfo["AreaDoTerreno"]["value"],
                "AreaUtil": pinfo["AreaUtil"]["value"],
            },
            "site.processed_info AreaDoTerreno.value e AreaUtil.value",
            (
                f"AreaDeMatricula={inputs['AreaDeMatricula']['value']} em site.inputs"
                if "AreaDeMatricula" in inputs
                else ""
            )
            + (
                f"; AreaDePreservacao={pinfo['AreaDePreservacao']['value']}"
                if "AreaDePreservacao" in pinfo
                else ""
            ),
        )
    )

    # L7
    layers = sorted({e.layer for e in model.entities if e.id.startswith("s")})
    meshes = sorted(
        {
            str((e.get("cad") or {}).get("layer"))
            for e in raw["site"]["elements"]
            if (e.get("cad") or {}).get("type") == "CadMesh"
        }
    )
    casos.append(
        caso(
            "L7",
            arq,
            layers,
            "layers normalizados das entidades s<i> (site.elements) do parser",
            f"fora do índice (CadMesh, topografia): {meshes}" if meshes else "",
        )
    )

    # L8
    ap = out("AfastamentoProjetado") or {}
    afs = [p.get("afastamento") for p in props.values()]
    dt_af = [
        d.get("afastamento")
        for d in outputs.get("DescritivoTorre", [])
        if str(d.get("label", "")).strip().upper() != "TOTAL"
    ]
    lib_entre = max(round(a * 2, 2) for a in afs)
    pares = [
        min_distance(_edge_prims(model, a), _edge_prims(model, b))
        for i, a in enumerate(towers)
        for b in towers[i + 1 :]
    ]
    chk["L8"] = {
        "entre_blocos": ap.get("entre_blocos"),
        "lateral": ap.get("lateral"),
        "2xmax_afastamento_familia": lib_entre,
        "afastamento_familias": sorted(set(afs)),
        "DescritivoTorre.afastamento": sorted(set(dt_af)),
        "AfastamentoAeracao": {
            k: v
            for k, v in (inputs.get("AfastamentoAeracao") or {}).items()
            if k != "type"
        },
        "InputsProcessados.afastamento": (out("InputsProcessados") or {}).get(
            "afastamento"
        ),
        "GabaritoNaoAfastado": {
            k: v
            for k, v in (inputs.get("GabaritoNaoAfastado") or {}).items()
            if k != "type"
        },
        "menor_par_desenhado": r3(min(pares)) if pares else None,
    }
    casos.append(
        caso(
            "L8",
            arq,
            ap.get("entre_blocos"),
            "solution.outputs AfastamentoProjetado.entre_blocos",
            f"lateral={ap.get('lateral')}; 2 x max(afastamento das famílias)="
            f"{lib_entre}; DescritivoTorre.afastamento={sorted(set(dt_af))}; "
            f"AfastamentoAeracao={chk['L8']['AfastamentoAeracao']}; "
            f"menor distância entre torres desenhadas="
            f"{chk['L8']['menor_par_desenhado']}",
        )
    )

    # A1: CAProjetado x base de cálculo = área computável projetada?
    base_in = (inputs.get("AreaBaseDeCalculo") or {}).get("value")
    if base_in == "AreaDeMatricula" and "AreaDeMatricula" in inputs:
        basis, basis_src = inputs["AreaDeMatricula"]["value"], "AreaDeMatricula"
    else:
        basis, basis_src = pinfo["AreaDoTerreno"]["value"], "AreaDoTerreno"
    atcc = out("AreaTotalConstruidaComputavel")["value"]
    aptc = out("AreaPrivativaTotalComputavel")["value"]
    vbc = out("ValorDeBaseParaCalculo")
    candidates = {
        "AreaDoTerreno": pinfo["AreaDoTerreno"]["value"],
        "AreaUtil": pinfo["AreaUtil"]["value"],
        **(
            {"AreaDeMatricula": inputs["AreaDeMatricula"]["value"]}
            if "AreaDeMatricula" in inputs
            else {}
        ),
    }
    closes = {
        f"{num}/{den}": trunc2(dec(numv) / dec(denv)) == dec(caproj)
        for num, numv in (("ATCC", atcc), ("APTC", aptc))
        for den, denv in candidates.items()
    }
    ca_ok = trunc2(dec(atcc) / dec(basis)) == dec(caproj)
    typologies = list(upt)
    archprog = {
        a["hid"]: a["value"]
        for a in model.indicators["archprog"]
        if a.get("type") == "FamilyProportion" and a.get("value")
    }
    chk["A1"] = {
        "base": basis_src,
        "base_valor": basis,
        "ValorDeBaseParaCalculo": vbc and {"area": vbc["area"], "label": vbc["label"]},
        "CAProjetado": caproj,
        "ATCC": atcc,
        "APTC": aptc,
        "ATCC/base": float(dec(atcc) / dec(basis)),
        "fecha_ATCC_base": ca_ok,
        "fechamentos": closes,
        "tipologias_solucao": len(typologies),
        "archprog_proporcoes": archprog,
    }
    per_unit = dec(atcc) / dec(tu)
    estimate = dec(basis) * dec(camax) / per_unit
    if not ca_ok:
        casos.append(
            caso(
                "A1",
                arq,
                None,
                "CAProjetado, AreaTotalConstruidaComputavel, base de cálculo",
                f"definição pendente: trunc(ATCC/{basis_src}) != CAProjetado "
                f"({closes})",
                "pendente",
            )
        )
    else:
        # Decisão do PRD (D2, A1): área por unidade pelo mix da própria solução,
        # que inclui o comum computável; vale com uma tipologia ou várias.
        casos.append(
            caso(
                "A1",
                arq,
                int(estimate.to_integral_value(rounding=ROUND_FLOOR)),
                f"floor({basis_src} x CAMaximoExigido / (AreaTotalConstruidaComputavel"
                " / TotalDeUnidades))",
                f"{basis_src}={basis}; CAMaximoExigido={camax}; "
                f"área computável por unidade={float(per_unit):.4f} "
                f"(ATCC={atcc} / {tu} unidades, inclui o comum computável); "
                f"valor antes do piso={float(estimate):.4f}; mix da solução "
                f"{upt}; archprog={archprog or 'sem FamilyProportion'}",
            )
        )

    # B2
    via = out("ViarioProjetado")
    vag = out("VagasProjetadas")
    est = out("EstacionamentoProjetado")
    proj = out("ProjecaoTorres")
    pick = lambda o: o and {"area": o["area"], "percentual": o["percentual"]}  # noqa: E731
    # Exato na versão atual do buildings.metrics; exportadores antigos truncam a
    # soma bruta e erram o último centavo.
    diffs = (
        [dec(est[k]) - dec(via[k]) - dec(vag[k]) for k in ("area", "percentual")]
        if via and vag and est
        else []
    )
    soma_ok = bool(diffs) and all(abs(d) <= Decimal("0.01") for d in diffs)
    soma_exata = bool(diffs) and all(d == 0 for d in diffs)
    chk["B2"] = {
        "Viario": pick(via),
        "Vagas": pick(vag),
        "Estacionamento": pick(est),
        "ProjecaoTorres": pick(proj),
        "est=via+vag": soma_ok,
        "vagas_desenhadas": len(vagas),
    }
    if est is None:
        casos.append(
            caso(
                "B2",
                arq,
                None,
                "solution.outputs EstacionamentoProjetado / ViarioProjetado",
                "arquivo sem EstacionamentoProjetado"
                + ("" if via else " e sem ViarioProjetado")
                + f" ({len(vagas)} vagas desenhadas); ProjecaoTorres={pick(proj)}",
                "fora",
            )
        )
    else:
        casos.append(
            caso(
                "B2",
                arq,
                {
                    "EstacionamentoProjetado": pick(est),
                    "ViarioProjetado": pick(via),
                    "VagasProjetadas": pick(vag),
                    "ProjecaoTorres": pick(proj),
                },
                "solution.outputs EstacionamentoProjetado (= ViarioProjetado + "
                "VagasProjetadas), ProjecaoTorres",
                "resposta = EstacionamentoProjetado, que já inclui o viário "
                + (
                    "(soma exata)"
                    if soma_exata
                    else f"(soma difere em {[str(d) for d in diffs]}: truncamento)"
                )
                + "; não somar ViarioProjetado de novo; "
                f"percentual sobre {basis_src}; ProjecaoTorres só para comparação",
                "ok" if soma_ok else "pendente",
            )
        )

    # B5
    adm = ADMISSAO.get(arq)
    fonte = "caminho(estado, portaria, torre) na rede do teseu (data/benchmark/redes)"
    if adm is None or not adm["admitido"]:
        motivo = f"não admitido: {adm['motivo']}" if adm else "fora da admissão"
        casos.append(caso("B5", arq, None, fonte, motivo, "fora"))
    elif not (REDES / f"{Path(arq).stem}.json").exists():
        casos.append(
            caso("B5", arq, None, fonte, "sem etapa de estacionamento", "fora")
        )
    elif len(portarias) != 1:
        obs = "sem portaria desenhada" if not portarias else f"portarias {portarias}"
        casos.append(caso("B5", arq, None, fonte, obs, "fora"))
    else:
        rotas = {t: caminho(arq, portarias[0], t) for t in towers}
        chk["B5"] = rotas
        resposta = {t: r.get("distancia", r.get("erro")) for t, r in rotas.items()}
        obs = "; ".join(
            f"{t}: " + (r["motivo"] if "motivo" in r else r.get("erro", ""))
            if "distancia" not in r
            else f"{t}: acesso a {r['afastamento_destino']} m da rede"
            for t, r in rotas.items()
        )
        d_port = next(
            (r["afastamento_origem"] for r in rotas.values() if "distancia" in r), None
        )
        if d_port is not None:
            obs = f"acesso da portaria {portarias[0]} a {d_port} m da rede; {obs}"
        erros = [r for r in rotas.values() if "distancia" not in r]
        bad = [r for r in erros if r.get("erro") != "inalcançável"]
        casos.append(caso("B5", arq, resposta, fonte, obs, "pendente" if bad else "ok"))

    # B8
    strategy = raw["solution"].get("strategy")
    tower_strategy = [
        a.get("strategy")
        for a in model.indicators["archprog"]
        if a.get("type") == "TowerStrategy"
    ]
    casos.append(
        caso(
            "B8",
            arq,
            strategy,
            "solution.strategy",
            (
                "nenhuma tool do agente expõe solution.strategy"
                if strategy
                else "arquivo sem solution.strategy "
                f"(versão {raw.get('version')}); archprog TowerStrategy="
                f"{tower_strategy or 'ausente'}"
            ),
            "ok" if strategy else "fora",
        )
    )

    # B9
    vaga_prims = [prim for v in vagas for prim in _edge_prims(model, v)]
    if not vaga_prims:
        casos.append(
            caso(
                "B9",
                arq,
                None,
                "instâncias de Vaga",
                "nenhuma vaga desenhada: a pergunta não se aplica",
                "fora",
            )
        )
        chk["B9"] = None
    else:
        dists = {t: min_distance(_edge_prims(model, t), vaga_prims) for t in towers}
        far = sorted(t for t, d in dists.items() if d > RAIO_VAGA)
        border = [t for t, d in dists.items() if abs(d - RAIO_VAGA) < TIE]
        chk["B9"] = {t: r3(d) for t, d in dists.items()}
        casos.append(
            caso(
                "B9",
                arq,
                {"torres_sem_vaga_em_50m": far, "existe": bool(far)},
                "min_distance(pavimento-tipo de cada torre, /core de todas as vagas)",
                "distâncias por torre (m): "
                + json.dumps({t: r3(d) for t, d in dists.items()})
                + (
                    f"; ATENÇÃO: a menos de {TIE} m do raio: {border}" if border else ""
                ),
                "ok" if not border else "fora",
            )
        )

    # B11
    if not portarias:
        casos.append(
            caso(
                "B11", arq, None, "instância Portaria", "sem portaria desenhada", "fora"
            )
        )
    else:
        port = [prim for p in portarias for prim in _edge_prims(model, p)]
        rank = ranking(model, towers, port)
        d0, t0 = rank[0]
        pr = props[t0]
        units = tower_units(pr)
        n_unid = pr.get("n_pavimentos_unidades")
        fonte = (
            f"min_distance(pavimento-tipo, /core da portaria {portarias}); "
            "tower_units(properties da família da instância) x min(5, "
            "n_pavimentos_unidades)"
        )
        chk["B11"] = [(t, r3(d)) for d, t in rank[:3]]
        if len(rank) > 1 and rank[1][0] - d0 < TIE:
            tied = [t for d, t in rank if d - d0 < TIE]
            vals = {
                tower_units(props[t])[0] * min(5, props[t].get("n_pavimentos_unidades"))
                for t in tied
            }
            casos.append(
                caso(
                    "B11",
                    arq,
                    None,
                    fonte,
                    f"AMBÍGUO: empate < {TIE} m entre {tied} a {r3(d0)} m; "
                    + (
                        f"resposta seria a mesma ({vals.pop()})"
                        if len(vals) == 1
                        else f"respostas diferentes {sorted(vals)}"
                    ),
                    "fora",
                )
            )
        else:
            per_floor = units[0]
            n_tipo = (pr.get("pav_tipo") or {}).get("n", n_unid)
            terreo_units = (
                sum(((pr.get("terreo") or {}).get("tipologias") or {}).values())
                if pr.get("type") == "Tower"
                else 0
            )
            lost = per_floor * min(5, n_unid)
            obs = (
                f"torre {t0} ({model.instances[t0].family}) a {r3(d0)} m da portaria; "
                f"2ª: {rank[1][1]} a {r3(rank[1][0])} m; unidades_por_pavimento="
                f"{per_floor}; n_pavimentos_unidades={n_unid}"
                if len(rank) > 1
                else f"torre única {t0}; unidades_por_pavimento={per_floor}"
            )
            status = "ok"
            if n_unid <= 5:
                obs += (
                    f"; com {n_unid} pavimentos com unidades (total_pavimentos="
                    f"{pr.get('total_pavimentos')}), a torre perde todas as unidades"
                )
            # Tirar 5 pavimentos de uma torre com menos de 5 tipos come o terreo;
            # so fecha se o terreo tem as mesmas unidades por pavimento.
            if terreo_units and n_tipo < 5 and terreo_units != per_floor:
                status = "pendente"
                obs += f"; térreo com {terreo_units} unidades != {per_floor} do tipo"
            casos.append(caso("B11", arq, lost, fonte, obs, status))

    return casos, chk


def main() -> None:
    casos: list[dict] = []
    checks: list[dict] = []
    for path in FILES:
        c, k = run_file(path)
        casos.extend(c)
        checks.append(k)
        print(path, "ok", flush=True)
    order = list(PERGUNTAS)
    casos.sort(key=lambda c: (order.index(c["tarefa"]), c["arquivo"]))
    (OUT / "casos.json").write_text(json.dumps(casos, ensure_ascii=False, indent=1))
    (OUT / "checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=1))
    assert len(casos) == len(FILES) * len(PERGUNTAS)


if __name__ == "__main__":
    main()
