"""Primitivas geometricas — a abstracao que unifica a camada.

Cerca de 15 tipos de entidade DXF colapsam em 3 primitivas. Por causa disso,
bbox, comprimento, area e hit-test derivam de um lugar so, sem `match` por tipo
espalhado pelo codigo.
"""

import math
from dataclasses import dataclass
from typing import Union

Vec2 = tuple[float, float]

# (min_x, min_y, max_x, max_y)
BBox = tuple[float, float, float, float]

# Fator de largura media de glifo usado para aproximar a bbox de texto.
_TEXT_WIDTH_FACTOR = 0.6


@dataclass(slots=True)
class PolylinePrim:
    """Sequencia de segmentos retos. Curvas chegam aqui ja achatadas.

    Quando `closed` e True, os pontos NAO repetem o primeiro no fim — o
    segmento de fechamento e implicito (ver `polyline_length`).
    """

    pts: list[Vec2]
    closed: bool


@dataclass(slots=True)
class PointPrim:
    p: Vec2


@dataclass(slots=True)
class TextPrim:
    p: Vec2
    text: str
    height: float
    rotation: float  # graus


Prim = Union[PolylinePrim, PointPrim, TextPrim]


def normalize_closed(pts: list[Vec2], closed: bool) -> list[Vec2]:
    """Remove o vertice de fechamento duplicado.

    `ezdxf.path.Path.flattening()` devolve o primeiro ponto repetido no fim de
    um caminho fechado. Manter a duplicata contaria o segmento de fechamento
    duas vezes no comprimento e distorceria a area.
    """
    if closed and len(pts) > 1 and _same_point(pts[0], pts[-1]):
        return pts[:-1]
    return pts


def _same_point(a: Vec2, b: Vec2, tol: float = 1e-9) -> bool:
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def polyline_length(pts: list[Vec2], closed: bool) -> float:
    """Comprimento total, incluindo o segmento de fechamento quando fechada."""
    if len(pts) < 2:
        return 0.0

    total = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:], strict=False):
        total += math.hypot(x2 - x1, y2 - y1)

    if closed:
        total += math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1])

    return total


def polygon_area(pts: list[Vec2]) -> float:
    """Area por shoelace, em valor absoluto. So faz sentido em poligono fechado."""
    if len(pts) < 3:
        return 0.0

    acc = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1], strict=True):
        acc += x1 * y2 - x2 * y1

    return abs(acc) / 2.0


def text_corners(prim: TextPrim) -> list[Vec2]:
    """Quatro cantos aproximados da caixa de um texto, ja rotacionados."""
    width = len(prim.text) * prim.height * _TEXT_WIDTH_FACTOR
    height = prim.height
    rad = math.radians(prim.rotation)
    cos_r, sin_r = math.cos(rad), math.sin(rad)
    ox, oy = prim.p

    corners: list[Vec2] = []
    for dx, dy in ((0.0, 0.0), (width, 0.0), (width, height), (0.0, height)):
        corners.append((ox + dx * cos_r - dy * sin_r, oy + dx * sin_r + dy * cos_r))

    return corners


def bbox_of_prims(prims: list[Prim]) -> BBox | None:
    """Bbox que envolve todas as primitivas, ou None se nao houver geometria."""
    min_x = min_y = math.inf
    max_x = max_y = -math.inf

    for prim in prims:
        if isinstance(prim, PolylinePrim):
            points: list[Vec2] = prim.pts
        elif isinstance(prim, PointPrim):
            points = [prim.p]
        else:
            points = text_corners(prim)

        for x, y in points:
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)

    if min_x is math.inf or min_x > max_x:
        return None

    return (min_x, min_y, max_x, max_y)


def union_bbox(a: BBox | None, b: BBox | None) -> BBox | None:
    if a is None:
        return b
    if b is None:
        return a
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def bbox_intersects(a: BBox, b: BBox) -> bool:
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def bbox_contains(outer: BBox, inner: BBox) -> bool:
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and outer[2] >= inner[2]
        and outer[3] >= inner[3]
    )


def distance_point_segment(p: Vec2, a: Vec2, b: Vec2) -> float:
    """Menor distancia de um ponto a um segmento. Base do hit-test por clique."""
    px, py = p
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay

    if dx == 0.0 and dy == 0.0:
        return math.hypot(px - ax, py - ay)

    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))

    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))
