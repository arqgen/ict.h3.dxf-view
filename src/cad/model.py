"""O indice: transforma um AQG em estrutura consultavel sem reabrir o arquivo.

Este modulo e a unica fonte de verdade sobre "o que existe no desenho". As tools
do agente e o payload de render do frontend derivam os dois daqui, o que garante
que o id que a IA cita e o id que o canvas destaca sao o mesmo.

Ids (posicao 0-based no arquivo, contada antes de qualquer exclusao):
- `s<i>`: `site.elements[i]`;
- `p<i>`: instancia de familia (`PlacedFamily`) ou elemento posicionado;
- `p<i>.<j>`: parte `volume[j]` da familia da instancia `p<i>`.
"""

import json
import math
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.cad.geometry import (
    BBox,
    PointPrim,
    PolylinePrim,
    Prim,
    Vec2,
    bbox_of_prims,
    normalize_closed,
    polygon_area,
    polyline_length,
    union_bbox,
)

DEFAULT_COLOR = "#d6d6d6"
MAX_WARNINGS = 20

_EXCLUDED_TOWER = ("/reference", "/road_access", "/access")
_EXCLUDED_OTHER = (*_EXCLUDED_TOWER, "/road_network", "/core/zito")

# (prefixo, layer, type ou None para o padrao, rotulo e tipologia, cor)
_TOWER_PARTS: tuple[tuple[str, str, str | None, bool, str], ...] = (
    ("/area/apartamento", "pav_tipo", "apartamento", True, "#BDD9E7"),
    ("/area/varanda", "pav_tipo", "varanda", True, "#BDD9E7"),
    ("/area/circ_vertical", "pav_tipo", None, False, "#F0F0F0"),
    ("/area/circ_horizontal", "pav_tipo", None, False, "#F0F0F0"),
    ("/area/shaft", "shaft", "shaft", False, "#E8E8E8"),
    ("/core", "pav_tipo", "core", False, "#D0D0CF"),
    ("/building_pad", "projecao_plato", "building_pad", False, "#DEDEDC"),
    ("/afastamento", "afastamento", "afastamento", False, "#FE8484"),
)

_SITE_COLORS = {
    "AQG_PERIMETRO": DEFAULT_COLOR,
    "AQG_OFFSET": "#FE8484",
    "AQG_FRENTE": "#9AA5B1",
    "AQG_FUNDOS": "#9AA5B1",
    "AQG_ACESSO": "#009961",
    "AQG_RUA": "#7C8798",
}

# (layer, type, text, color)
PartSpec = tuple[str, str, str | None, str]
Place = Callable[[Vec2], Vec2]


class AqgLoadError(Exception):
    """Bytes que não são JSON, ou JSON que não é um Project AQG."""


@dataclass(slots=True)
class CadEntity:
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
    instance: str | None
    family: str | None


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
class CadFamily:
    class_path: str
    label: str
    type: str
    properties: dict[str, Any]


@dataclass(slots=True)
class CadInstance:
    id: str
    hid: str
    family: str
    family_type: str
    family_index: int  # posicao em model.families; o label pode se repetir
    x: float
    y: float
    angle: float
    entity_ids: list[str]


@dataclass(slots=True)
class CadModel:
    filename: str
    entities: list[CadEntity]
    by_id: dict[str, CadEntity]
    layers: list[CadLayer]
    by_type: dict[str, int]
    instances: dict[str, CadInstance]
    families: list[CadFamily]
    indicators: dict[str, Any]
    bbox: BBox | None
    units: str
    warnings: list[str]

    @property
    def layer_names(self) -> list[str]:
        return [layer.name for layer in self.layers]

    def layer(self, name: str) -> CadLayer | None:
        lowered = name.lower()
        for layer in self.layers:
            if layer.name.lower() == lowered:
                return layer
        return None


def load_aqg(data: bytes, filename: str) -> CadModel:
    """Le os bytes de um AQG e constroi o indice."""
    try:
        project = json.loads(data)
    except (UnicodeDecodeError, ValueError) as exc:
        raise AqgLoadError(f"o arquivo não é um JSON válido: {exc}") from exc

    if not isinstance(project, dict):
        raise AqgLoadError("o arquivo não parece um Project AQG: não é um objeto")
    if not isinstance(project.get("families"), list):
        raise AqgLoadError(
            "o arquivo não parece um Project AQG: falta a lista families"
        )
    solution = project.get("solution")
    if not isinstance(solution, dict) or not isinstance(
        solution.get("placed_objects"), list
    ):
        raise AqgLoadError(
            "o arquivo não parece um Project AQG: falta a lista solution.placed_objects"
        )

    # build_model so transforma em aviso o que reconhece como dado ruim; um tipo
    # inesperado em lugar que ele nao confere (position.x = "abc", site lista)
    # ainda estoura aqui, e isso e arquivo invalido, nao erro do servidor.
    try:
        return build_model(project, filename)
    except (TypeError, ValueError, AttributeError) as exc:
        raise AqgLoadError(
            f"o arquivo AQG tem um campo em formato inesperado: {exc}"
        ) from exc


def build_model(project: dict, filename: str) -> CadModel:
    """Constroi o indice. Problemas de dado viram avisos, nunca excecao."""
    site = project.get("site") or {}
    solution = project.get("solution") or {}
    raw_families = [f for f in project.get("families") or [] if isinstance(f, dict)]
    families = [_family(raw) for raw in raw_families]

    warnings: list[str] = []
    entities: list[CadEntity] = []
    instances: dict[str, CadInstance] = {}

    for i, element in enumerate(site.get("elements") or []):
        entity = _site_entity(f"s{i}", element, None, warnings)
        if entity:
            entities.append(entity)

    for i, obj in enumerate(solution.get("placed_objects") or []):
        if not isinstance(obj, dict):
            continue
        pid = f"p{i}"
        kind = obj.get("type")

        if kind in ("PlacedElement", "PlacedAuxiliaryArea"):
            entity = _site_entity(pid, obj, obj.get("label"), warnings)
            if entity:
                entities.append(entity)
            continue

        if kind != "PlacedFamily":
            warnings.append(f"objeto {pid} de tipo {kind} não suportado — ignorado")
            continue

        hid = str(obj.get("hid") or "")
        k = _find_family(hid, families)
        if k is None:
            warnings.append(f"instância {pid} ({hid}) sem família — ignorada")
            continue

        instance, parts = _place_family(
            pid, hid, obj, k, families[k], raw_families[k], warnings
        )
        instances[pid] = instance
        entities.extend(parts)

    by_type = dict(
        sorted(
            Counter(entity.type for entity in entities).items(),
            key=lambda item: (-item[1], item[0]),
        )
    )

    bbox: BBox | None = None
    for entity in entities:
        bbox = union_bbox(bbox, entity.bbox)

    return CadModel(
        filename=filename,
        entities=entities,
        by_id={entity.id: entity for entity in entities},
        layers=_build_layers(entities),
        by_type=by_type,
        instances=instances,
        families=families,
        indicators={
            "outputs": _or_default(solution.get("outputs"), []),
            "inputs": _or_default(site.get("inputs"), []),
            "processed_info": _or_default(site.get("processed_info"), []),
            "scores": _or_default(solution.get("scores"), {}),
        },
        bbox=bbox,
        units="metros",
        warnings=_dedupe(warnings),
    )


def _or_default(value: Any, default: Any) -> Any:
    return default if value is None else value


def _matches(a: str, b: str) -> bool:
    return a == b or a.startswith(b.rstrip("/") + "/")


def _find_family(hid: str, families: list[CadFamily]) -> int | None:
    # Nos dois sentidos: ha vagas com hid mais curto que o class_path da familia.
    for k, family in enumerate(families):
        if _matches(hid, family.class_path) or _matches(family.class_path, hid):
            return k
    return None


def _family(raw: dict) -> CadFamily:
    class_path = str(raw.get("class_path") or "")
    properties = raw.get("properties") or {}
    family_type = str(properties.get("type") or "")
    return CadFamily(
        class_path=class_path,
        label=_family_label(raw.get("label"), class_path, family_type),
        type=family_type,
        properties=properties,
    )


def _family_label(label: Any, class_path: str, family_type: str) -> str:
    text = str(label or "").strip()
    if not text:
        text = class_path.strip("/").split("/")[-1]
    if text.isdigit():
        return f"{family_type} {text}".strip()
    return text


def _category(family_type: str) -> str:
    lowered = family_type.lower()
    if lowered in ("tower", "dynamictower3d"):
        return "torre"
    if lowered in ("vaga", "portaria"):
        return lowered
    return "outra"


def _part_spec(family: CadFamily, class_path: str) -> PartSpec | None:
    """Layer, type, rotulo e cor de uma parte, ou None se ela nao e desenhada."""
    segs = class_path.strip("/").split("/")
    default_type = segs[1] if segs[0] == "area" and len(segs) > 1 else segs[0]
    label = family.label
    category = _category(family.type)

    if category == "vaga":
        return (
            ("viario_vaga", "vaga", label, "#E1E1E1") if class_path == "/core" else None
        )
    if category == "portaria":
        return (
            ("portaria", "portaria", label, "#E6DCC8")
            if class_path == "/core"
            else None
        )

    if category == "outra":
        if any(_matches(class_path, p) for p in _EXCLUDED_OTHER):
            return None
        layer = f"familia:{family.type.lower()}"
        if _matches(class_path, "/core"):
            return (layer, "core", label, "#E6DCC8")
        return (layer, default_type, label, "#C9DCCB")

    if any(_matches(class_path, p) for p in _EXCLUDED_TOWER):
        return None
    for prefix, layer, part_type, typology, color in _TOWER_PARTS:
        if not _matches(class_path, prefix):
            continue
        text = segs[2] if typology and len(segs) > 2 else label
        return (layer, part_type or default_type, text, color)
    return ("pav_tipo", default_type, label, "#C9DCCB")


def _normalize_layer(name: Any) -> str:
    upper = str(name or "").upper()
    return upper if upper.startswith("AQG_") else f"AQG_{upper}"


def _site_entity(
    eid: str, element: Any, text: Any, warnings: list[str]
) -> CadEntity | None:
    """Entidade de terreno ou viario: ja vem em coordenadas do terreno."""
    if not isinstance(element, dict):
        return None
    cad = element.get("cad") or {}
    cad_type = str(cad.get("type") or "")
    if cad_type == "CadMesh":
        return None

    layer = _normalize_layer(cad.get("layer"))
    color = _SITE_COLORS.get(layer, "#B7C3D0")
    if str(element.get("hid") or "").startswith("/road_network"):
        color = "#7C8798"

    return _entity(
        eid,
        cad.get("geometry"),
        lambda pt: pt,
        (layer, cad_type, str(text) if text else None, color),
        None,
        None,
        warnings,
    )


def _place_family(
    pid: str,
    hid: str,
    obj: dict,
    family_index: int,
    family: CadFamily,
    raw_family: dict,
    warnings: list[str],
) -> tuple[CadInstance, list[CadEntity]]:
    position = obj.get("position") or {}
    x = float(position.get("x") or 0.0)
    y = float(position.get("y") or 0.0)
    angle = float(position.get("angle") or 0.0)
    cos_t, sin_t = math.cos(math.radians(angle)), math.sin(math.radians(angle))

    def place(pt: Vec2) -> Vec2:
        px, py = pt
        return (x + px * cos_t - py * sin_t, y + px * sin_t + py * cos_t)

    parts: list[CadEntity] = []
    for j, volume in enumerate(raw_family.get("volume") or []):
        if not isinstance(volume, dict):
            continue
        spec = _part_spec(family, str(volume.get("class_path") or ""))
        if spec is None:
            continue
        entity = _entity(
            f"{pid}.{j}",
            volume.get("geometry"),
            place,
            spec,
            pid,
            family.label,
            warnings,
        )
        if entity:
            parts.append(entity)

    instance = CadInstance(
        id=pid,
        hid=hid,
        family=family.label,
        family_type=family.type,
        family_index=family_index,
        x=x,
        y=y,
        angle=angle,
        entity_ids=[part.id for part in parts],
    )
    return instance, parts


def _entity(
    eid: str,
    geometry: Any,
    place: Place,
    spec: PartSpec,
    instance: str | None,
    family: str | None,
    warnings: list[str],
) -> CadEntity | None:
    try:
        built = _geometry(geometry, place)
    except (TypeError, ValueError, IndexError, KeyError):
        warnings.append(f"entidade {eid} com geometria inválida — ignorada")
        return None

    if built is None:
        kind = geometry.get("type") if isinstance(geometry, dict) else None
        warnings.append(f"entidade {eid} sem geometria suportada ({kind}) — ignorada")
        return None

    prims, closed, area = built
    lengths = [
        polyline_length(prim.pts, prim.closed)
        for prim in prims
        if isinstance(prim, PolylinePrim)
    ]
    layer, entity_type, text, color = spec
    return CadEntity(
        id=eid,
        type=entity_type,
        layer=layer,
        color=color,
        prims=prims,
        bbox=bbox_of_prims(prims),
        closed=closed,
        length=sum(lengths) if lengths else None,
        area=area,
        text=text,
        instance=instance,
        family=family,
    )


def _geometry(
    geometry: Any, place: Place
) -> tuple[list[Prim], bool, float | None] | None:
    """GeoJSON -> (primitivas, fechada, area). None se o tipo nao e suportado."""
    if not isinstance(geometry, dict):
        return None
    kind = geometry.get("type")
    coords = geometry.get("coordinates")

    def line(raw: list) -> list[Vec2]:
        return [place((float(c[0]), float(c[1]))) for c in raw]

    def ring(raw: list) -> list[Vec2]:
        return normalize_closed(line(raw), True)

    if kind in ("Polygon", "MultiPolygon"):
        polygons = [coords] if kind == "Polygon" else coords
        prims: list[Prim] = []
        area = 0.0
        for polygon in polygons:
            rings = [ring(raw) for raw in polygon]
            prims.extend(PolylinePrim(pts=pts, closed=True) for pts in rings)
            if rings:
                # Aneis seguintes ao primeiro sao furos: subtraem.
                area += polygon_area(rings[0]) - sum(map(polygon_area, rings[1:]))
        return prims, True, area
    if kind == "LinearRing":
        return [PolylinePrim(pts=ring(coords), closed=True)], True, None
    if kind == "LineString":
        return [PolylinePrim(pts=line(coords), closed=False)], False, None
    if kind == "MultiLineString":
        return (
            [PolylinePrim(pts=line(raw), closed=False) for raw in coords],
            False,
            None,
        )
    if kind == "Point":
        return [PointPrim(p=line([coords])[0])], False, None
    return None


def _build_layers(entities: list[CadEntity]) -> list[CadLayer]:
    counts: Counter[str] = Counter()
    per_type: dict[str, Counter[str]] = {}
    boxes: dict[str, BBox | None] = {}
    colors: dict[str, str] = {}

    for entity in entities:
        counts[entity.layer] += 1
        per_type.setdefault(entity.layer, Counter())[entity.type] += 1
        boxes[entity.layer] = union_bbox(boxes.get(entity.layer), entity.bbox)
        colors.setdefault(entity.layer, entity.color)

    return [
        CadLayer(
            name=name,
            color=colors[name],
            count=counts[name],
            by_type=dict(per_type[name].most_common()),
            bbox=boxes[name],
            frozen=False,
            on=True,
        )
        for name in sorted(counts, key=str.lower)
    ]


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


def describe_model(model: CadModel) -> str:
    """Resumo textual do projeto, em pt-BR, para o system prompt.

    Fora das tools, este texto e a UNICA visao que o modelo tem do desenho. Por
    isso ele so lista o que existe: nenhuma contagem, medida, extensao ou valor
    de indicador. Um numero aqui seria um caminho para o modelo citar
    quantidade sem tool call, o que o projeto proibe.
    """
    families = list(
        dict.fromkeys(
            (inst.family, inst.family_type) for inst in model.instances.values()
        )
    )
    indicator_types = list(
        dict.fromkeys(
            str(item["type"])
            for item in [*model.indicators["outputs"], *model.indicators["inputs"]]
            if isinstance(item, dict) and item.get("type")
        )
    )

    lines = [
        f"Arquivo: {model.filename}",
        f"Unidade: {model.units}",
        "",
        "Ids: p<i> e uma instancia de familia (torre, vaga, portaria...), "
        "p<i>.<j> e uma parte desenhada dessa instancia e s<i> e um elemento "
        "do terreno. Elementos posicionados (viario, taludes) tambem usam p<i>.",
        "",
        "Layers:",
        *[f"  {name}" for name in model.layer_names],
        "",
        "Familias instanciadas:",
        *[f"  {label} ({family_type})" for label, family_type in families],
        "",
        "Tipos de indicador disponiveis:",
        *[f"  {name}" for name in indicator_types],
    ]

    if model.warnings:
        lines += ["", "Avisos do parser:", *[f"  {w}" for w in model.warnings]]

    return "\n".join(lines)


def prims_payload(model: CadModel) -> list[dict[str, Any]]:
    """Serializa as entidades para o canvas do frontend.

    Coordenadas arredondadas em 4 casas — o payload de um projeto grande e
    dominado por digitos que nenhum pixel consegue distinguir.
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
