"""O indice: transforma um DXF em estrutura consultavel sem reabrir o arquivo.

Este modulo e a unica fonte de verdade sobre "o que existe no desenho". As tools
do agente e o payload de render do frontend derivam os dois daqui, o que garante
que o id que a IA cita e o id que o canvas destaca sao o mesmo.

Divisao de trabalho com o ezdxf — nao reimplemente nada disto:
- `recursive_decompose` resolve INSERT aninhado, arrays MINSERT, DIMENSION via
  bloco anonimo, LEADER e MLINE.
- `make_path().flattening()` amostra ARC/CIRCLE/ELLIPSE, converte bulge em arco
  e avalia SPLINE (de Boor).
- `RenderContext.resolve_all()` resolve BYLAYER/BYBLOCK/true_color para hex.
- `mtext.plain_text()` limpa os escapes de formatacao.
"""

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import ezdxf.bbox
from ezdxf import colors as ezcolors
from ezdxf.addons.drawing.properties import RenderContext
from ezdxf.disassemble import recursive_decompose
from ezdxf.document import Drawing
from ezdxf.entities import DXFEntity
from ezdxf.path import make_path

from src.cad.geometry import (
    BBox,
    PointPrim,
    PolylinePrim,
    Prim,
    TextPrim,
    Vec2,
    bbox_of_prims,
    normalize_closed,
    polygon_area,
    polyline_length,
    union_bbox,
)

DEFAULT_COLOR = "#d6d6d6"
MAX_WARNINGS = 20

# Tipos que `make_path` nao suporta e que tratamos explicitamente.
_TEXT_TYPES = frozenset({"TEXT", "MTEXT", "ATTRIB", "ATTDEF"})
_POINT_TYPES = frozenset({"POINT"})

# Nomes de unidade em pt-BR, indexados pelo codigo $INSUNITS.
_UNIT_NAMES: dict[int, str] = {
    0: "sem unidade",
    1: "polegadas",
    2: "pes",
    3: "milhas",
    4: "milimetros",
    5: "centimetros",
    6: "metros",
    7: "quilometros",
    8: "micropolegadas",
    9: "mils",
    10: "jardas",
    11: "angstroms",
    12: "nanometros",
    13: "microns",
    14: "decimetros",
    15: "decametros",
    16: "hectometros",
    17: "gigametros",
    18: "unidades astronomicas",
    19: "anos-luz",
    20: "parsecs",
}

# Variaveis de cabecalho expostas para consulta pelo agente.
_HEADER_WHITELIST = (
    "$ACADVER",
    "$INSUNITS",
    "$MEASUREMENT",
    "$LUNITS",
    "$LUPREC",
    "$AUNITS",
    "$AUPREC",
    "$DIMSCALE",
    "$LTSCALE",
    "$EXTMIN",
    "$EXTMAX",
    "$LIMMIN",
    "$LIMMAX",
    "$DWGCODEPAGE",
    "$CLAYER",
)


@dataclass(slots=True)
class CadEntity:
    """Uma entidade de modelspace, com a geometria ja achatada.

    `id` e o handle DXF da entidade de topo — o unico identificador que o LLM
    ve. Sub-entidades geradas por decomposicao tem `handle` None no ezdxf e por
    isso nunca sao enderecaveis.
    """

    id: str
    type: str
    layer: str
    color: str
    prims: list[Prim]
    bbox: BBox | None
    closed: bool
    length: float | None
    area: float | None
    text: str | None
    block: str | None


@dataclass(slots=True)
class CadLayer:
    name: str
    color: str
    count: int
    by_type: dict[str, int]
    bbox: BBox | None
    frozen: bool
    on: bool


@dataclass(slots=True)
class CadModel:
    filename: str
    entities: list[CadEntity]
    by_id: dict[str, CadEntity]
    layers: list[CadLayer]
    by_type: dict[str, int]
    insert_counts: dict[str, int]
    block_names: list[str]
    bbox: BBox | None
    units: str
    acad_version: str
    header: dict[str, Any]
    warnings: list[str]
    doc: Drawing = field(repr=False)

    @property
    def layer_names(self) -> list[str]:
        return [layer.name for layer in self.layers]

    def layer(self, name: str) -> CadLayer | None:
        lowered = name.lower()
        for layer in self.layers:
            if layer.name.lower() == lowered:
                return layer
        return None


def build_model(
    doc: Drawing, filename: str, warnings: list[str] | None = None
) -> CadModel:
    """Constroi o indice a partir de um documento ezdxf ja aberto."""
    msp = doc.modelspace()
    collected: list[str] = list(warnings or [])

    _render_dimensions(msp, collected)

    flatten_distance = _flatten_distance(msp)
    ctx = RenderContext(doc)

    entities: list[CadEntity] = []
    insert_counts: Counter[str] = Counter()

    for raw in msp:
        entity = _build_entity(raw, ctx, flatten_distance, collected)
        if entity is None:
            continue

        entities.append(entity)
        if entity.block:
            insert_counts[entity.block] += 1

    by_id = {entity.id: entity for entity in entities}
    by_type = dict(
        sorted(
            Counter(entity.type for entity in entities).items(),
            key=lambda item: (-item[1], item[0]),
        )
    )

    return CadModel(
        filename=filename,
        entities=entities,
        by_id=by_id,
        layers=_build_layers(doc, entities),
        by_type=by_type,
        insert_counts=dict(insert_counts.most_common()),
        block_names=sorted(
            block.name for block in doc.blocks if not block.name.startswith("*")
        ),
        bbox=_document_bbox(entities),
        units=_UNIT_NAMES.get(_units_code(doc), "unidades de desenho"),
        acad_version=str(doc.header.get("$ACADVER", doc.dxfversion)),
        header=_header_vars(doc),
        warnings=_dedupe(collected),
        doc=doc,
    )


def _build_entity(
    raw: DXFEntity,
    ctx: RenderContext,
    flatten_distance: float,
    warnings: list[str],
) -> CadEntity | None:
    handle = raw.dxf.get("handle", None)
    if not handle:
        # Sem handle nao ha como a IA se referir a entidade nem o canvas
        # destaca-la. Ignorar em silencio geraria um desenho incompleto, por
        # isso registramos.
        warnings.append(f"entidade {raw.dxftype()} sem handle foi ignorada")
        return None

    prims: list[Prim] = []
    for sub in _decompose(raw, warnings):
        prims.extend(_prims_of(sub, flatten_distance, warnings))

    try:
        props = ctx.resolve_all(raw)
        color = _normalize_hex(props.color)
        layer_name = props.layer or raw.dxf.get("layer", "0")
    except Exception as exc:
        warnings.append(f"nao foi possivel resolver cor de {raw.dxftype()}: {exc}")
        color = DEFAULT_COLOR
        layer_name = str(raw.dxf.get("layer", "0"))

    closed = any(isinstance(prim, PolylinePrim) and prim.closed for prim in prims)

    return CadEntity(
        id=str(handle),
        type=raw.dxftype(),
        layer=str(layer_name),
        color=color,
        prims=prims,
        bbox=bbox_of_prims(prims),
        closed=closed,
        length=_length_of(prims),
        area=_area_of(prims) if closed else None,
        text=_text_of(prims),
        block=_block_name(raw),
    )


def _decompose(raw: DXFEntity, warnings: list[str]):
    """Achata entidades compostas.

    Sempre `recursive_decompose` — `virtual_entities()` nao expande arrays
    MINSERT (devolveu 2 de 12 num array 3x2).
    """
    try:
        return list(recursive_decompose([raw]))
    except Exception as exc:
        warnings.append(f"falha ao decompor {raw.dxftype()}: {exc}")
        return [raw]


def _prims_of(
    sub: DXFEntity, flatten_distance: float, warnings: list[str]
) -> list[Prim]:
    dxftype = sub.dxftype()

    if dxftype in _TEXT_TYPES:
        prim = _text_prim(sub, warnings)
        return [prim] if prim else []

    if dxftype in _POINT_TYPES:
        location = sub.dxf.get("location", None)
        if location is None:
            return []
        return [PointPrim(p=(float(location.x), float(location.y)))]

    try:
        path = make_path(sub)
    except TypeError:
        # HATCH, LEADER e afins entram na contagem mas nao ganham geometria —
        # mesma limitacao da implementacao de referencia.
        return []
    except Exception as exc:
        warnings.append(f"falha ao achatar {dxftype}: {exc}")
        return []

    pts = [(float(v.x), float(v.y)) for v in path.flattening(flatten_distance)]
    if len(pts) < 2:
        return [PointPrim(p=pts[0])] if pts else []

    return [
        PolylinePrim(pts=normalize_closed(pts, path.is_closed), closed=path.is_closed)
    ]


def _text_prim(sub: DXFEntity, warnings: list[str]) -> TextPrim | None:
    try:
        content = sub.plain_text()
    except Exception as exc:
        warnings.append(f"falha ao extrair texto de {sub.dxftype()}: {exc}")
        return None

    if not content:
        return None

    insert = sub.dxf.get("insert", None)
    if insert is None:
        return None

    # `DXFNamespace.get` levanta DXFAttributeError quando o atributo nao existe
    # no tipo — nao devolve o default. Por isso escolhemos a chave pelo tipo em
    # vez de tentar as duas: MTEXT usa `char_height`, TEXT/ATTRIB usam `height`.
    key = "char_height" if sub.dxftype() == "MTEXT" else "height"
    height = sub.dxf.get(key, 1.0)

    return TextPrim(
        p=(float(insert.x), float(insert.y)),
        text=content,
        height=float(height or 1.0),
        rotation=float(sub.dxf.get("rotation", 0.0) or 0.0),
    )


def _length_of(prims: list[Prim]) -> float | None:
    lengths = [
        polyline_length(prim.pts, prim.closed)
        for prim in prims
        if isinstance(prim, PolylinePrim)
    ]
    return sum(lengths) if lengths else None


def _area_of(prims: list[Prim]) -> float | None:
    areas = [
        polygon_area(prim.pts)
        for prim in prims
        if isinstance(prim, PolylinePrim) and prim.closed
    ]
    return sum(areas) if areas else None


def _text_of(prims: list[Prim]) -> str | None:
    texts = [prim.text for prim in prims if isinstance(prim, TextPrim)]
    return "\n".join(texts) if texts else None


def _block_name(raw: DXFEntity) -> str | None:
    if raw.dxftype() != "INSERT":
        return None
    name = raw.dxf.get("name", None)
    return str(name) if name else None


def _render_dimensions(msp, warnings: list[str]) -> None:
    """Garante que cada DIMENSION tenha seu bloco anonimo de geometria.

    Arquivos reais ja vem com o bloco `*D<n>`. Documentos gerados
    programaticamente podem nao ter, e sem ele a cota fica invisivel.
    """
    doc = msp.doc
    for dim in msp.query("DIMENSION"):
        geometry = dim.dxf.get("geometry", None)
        if geometry and geometry in doc.blocks:
            continue
        try:
            dim.render()
        except Exception as exc:
            warnings.append(f"falha ao renderizar cota {dim.dxf.get('handle')}: {exc}")


def _flatten_distance(msp) -> float:
    """Tolerancia de achatamento proporcional ao tamanho do desenho.

    Um valor fixo produziria curvas facetadas em desenhos grandes e milhoes de
    vertices em desenhos pequenos. `fast=True` usa bbox de primitiva, o que e
    barato — a bbox definitiva vem depois, das proprias primitivas achatadas.
    """
    try:
        extents = ezdxf.bbox.extents(msp, fast=True)
    except Exception:
        return 0.01

    if not extents.has_data:
        return 0.01

    size = max(extents.size.x, extents.size.y)
    if not math.isfinite(size) or size <= 0:
        return 0.01

    return max(size * 5e-4, 1e-9)


def _units_code(doc: Drawing) -> int:
    try:
        return int(doc.header.get("$INSUNITS", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _header_vars(doc: Drawing) -> dict[str, Any]:
    header: dict[str, Any] = {}
    for name in _HEADER_WHITELIST:
        if name not in doc.header:
            continue
        header[name] = _jsonable(doc.header.get(name))
    return header


def _jsonable(value: Any) -> Any:
    if hasattr(value, "x") and hasattr(value, "y"):
        return [round(float(value.x), 6), round(float(value.y), 6)]
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    return str(value)


def _build_layers(doc: Drawing, entities: list[CadEntity]) -> list[CadLayer]:
    """Layers = uniao da tabela LAYER com os layers realmente usados.

    Um DXF pode referenciar um layer que nao esta na tabela, e a tabela pode
    listar layers sem nenhuma entidade. As duas situacoes importam para o painel.
    """
    counts: Counter[str] = Counter()
    per_type: dict[str, Counter[str]] = {}
    boxes: dict[str, BBox | None] = {}

    for entity in entities:
        counts[entity.layer] += 1
        per_type.setdefault(entity.layer, Counter())[entity.type] += 1
        boxes[entity.layer] = union_bbox(boxes.get(entity.layer), entity.bbox)

    table: dict[str, Any] = {}
    for layer in doc.layers:
        table[layer.dxf.name] = layer

    layers: list[CadLayer] = []
    for name in sorted(set(table) | set(counts), key=str.lower):
        record = table.get(name)
        rgb = getattr(record, "rgb", None) if record else None
        aci = int(record.dxf.color) if record else 7

        layers.append(
            CadLayer(
                name=name,
                color=_rgb_to_hex(rgb) if rgb else _aci_to_hex(aci),
                count=counts.get(name, 0),
                by_type=dict(per_type.get(name, Counter()).most_common()),
                bbox=boxes.get(name),
                frozen=bool(record.is_frozen()) if record else False,
                on=bool(record.is_on()) if record else True,
            )
        )

    return layers


def _document_bbox(entities: list[CadEntity]) -> BBox | None:
    """Bbox do desenho a partir das primitivas.

    Nao ler `$EXTMIN`/`$EXTMAX`: em documentos novos vem com as sentinelas
    +-1e20, que arruinariam qualquer enquadramento.
    """
    result: BBox | None = None
    for entity in entities:
        result = union_bbox(result, entity.bbox)
    return result


def _aci_to_hex(aci: int) -> str:
    try:
        r, g, b = ezcolors.aci2rgb(aci)
    except Exception:
        return DEFAULT_COLOR
    return f"#{r:02x}{g:02x}{b:02x}"


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def _normalize_hex(color: str | None) -> str:
    """`RenderContext` devolve `#RRGGBB` ou `#RRGGBBAA` — descartamos o alfa."""
    if not color or not color.startswith("#"):
        return DEFAULT_COLOR
    return color[:7]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
        if len(result) >= MAX_WARNINGS:
            result.append("... avisos adicionais suprimidos")
            break
    return result


def entity_raw_props(model: CadModel, entity_id: str) -> dict[str, Any] | None:
    """Atributos DXF crus de uma entidade, para o painel de detalhes."""
    entity = model.by_id.get(entity_id)
    if entity is None:
        return None

    raw = model.doc.entitydb.get(entity_id)
    if raw is None:
        return {}

    props: dict[str, Any] = {}
    for key, value in raw.dxfattribs().items():
        props[key] = _jsonable(value)

    if raw.dxftype() in ("LWPOLYLINE", "POLYLINE"):
        try:
            props["vertices"] = [
                [round(float(x), 4), round(float(y), 4)]
                for x, y in raw.get_points("xy")
            ]
        except Exception:
            pass

    return props


def describe_model(model: CadModel) -> str:
    """Resumo textual do desenho, em pt-BR, para o system prompt.

    Fora das tools, este texto e a UNICA visao que o modelo tem do desenho —
    por isso ele lista o que existe sem nunca afirmar medidas que so uma tool
    poderia calcular.
    """
    lines: list[str] = [
        f"Arquivo: {model.filename}",
        f"Versao AutoCAD: {model.acad_version}",
        f"Unidade de insercao: {model.units}",
    ]

    if model.bbox:
        min_x, min_y, max_x, max_y = model.bbox
        lines.append(
            f"Extensao: ({min_x:.3f}, {min_y:.3f}) a ({max_x:.3f}, {max_y:.3f})"
            f" — largura {max_x - min_x:.3f}, altura {max_y - min_y:.3f}"
        )
    else:
        lines.append("Extensao: indisponivel (nenhuma geometria com bbox)")

    text_count = sum(1 for e in model.entities if e.text)
    dimension_count = model.by_type.get("DIMENSION", 0)
    lines += [
        "",
        f"Total de entidades indexadas: {len(model.entities)}",
        f"Layers: {len(model.layers)}",
        f"Definicoes de bloco: {len(model.block_names)}",
        f"Insercoes de bloco: {sum(model.insert_counts.values())}",
        f"Entidades com texto: {text_count}",
        f"Cotas: {dimension_count}",
        "",
        "Entidades por tipo:",
    ]
    lines += [f"  {name}: {count}" for name, count in model.by_type.items()]

    ranked = sorted(model.layers, key=lambda layer: (-layer.count, layer.name.lower()))
    lines += ["", f"Layers (top {min(25, len(ranked))} por contagem):"]
    for layer in ranked[:25]:
        top_types = ", ".join(
            f"{name} {count}" for name, count in list(layer.by_type.items())[:4]
        )
        frozen = " [congelada]" if layer.frozen else ""
        detail = f" — {top_types}" if top_types else ""
        lines.append(f"  {layer.name}: {layer.count}{detail}{frozen}")

    if model.insert_counts:
        top_blocks = list(model.insert_counts.items())[:15]
        lines += ["", f"Blocos mais inseridos (top {len(top_blocks)}):"]
        lines += [f"  {name}: {count}" for name, count in top_blocks]

    if model.warnings:
        lines += ["", "Avisos do parser:"]
        lines += [f"  {warning}" for warning in model.warnings]

    return "\n".join(lines)


def prims_payload(model: CadModel) -> list[dict[str, Any]]:
    """Serializa as entidades para o canvas do frontend.

    Coordenadas arredondadas em 4 casas — o payload de um DXF grande e dominado
    por digitos que nenhum pixel consegue distinguir.
    """
    payload: list[dict[str, Any]] = []

    for entity in model.entities:
        if not entity.prims:
            continue

        shapes: list[dict[str, Any]] = []
        for prim in entity.prims:
            if isinstance(prim, PolylinePrim):
                shapes.append(
                    {
                        "k": "p",
                        "pts": [_round_pair(pt) for pt in prim.pts],
                        "c": prim.closed,
                    }
                )
            elif isinstance(prim, PointPrim):
                shapes.append({"k": "d", "p": _round_pair(prim.p)})
            else:
                shapes.append(
                    {
                        "k": "t",
                        "p": _round_pair(prim.p),
                        "s": prim.text,
                        "h": round(prim.height, 4),
                        "r": round(prim.rotation, 3),
                    }
                )

        payload.append(
            {
                "id": entity.id,
                "type": entity.type,
                "layer": entity.layer,
                "color": entity.color,
                "bbox": [round(v, 4) for v in entity.bbox] if entity.bbox else None,
                "shapes": shapes,
            }
        )

    return payload


def _round_pair(pt: Vec2) -> list[float]:
    return [round(pt[0], 4), round(pt[1], 4)]
