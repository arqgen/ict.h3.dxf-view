import math

from src.cad.geometry import (
    PolylinePrim,
    TextPrim,
    bbox_contains,
    bbox_intersects,
    bbox_of_prims,
    distance_point_segment,
    normalize_closed,
    polygon_area,
    polyline_length,
)

RECT = [(0.0, 0.0), (20.0, 0.0), (20.0, 14.0), (0.0, 14.0)]


def test_polyline_length_open():
    assert polyline_length([(0.0, 0.0), (3.0, 4.0)], closed=False) == 5.0


def test_polyline_length_closed_adds_closing_segment():
    assert polyline_length(RECT, closed=True) == 68.0


def test_polyline_length_open_rectangle_omits_closing_segment():
    assert polyline_length(RECT, closed=False) == 54.0


def test_polygon_area_shoelace():
    assert polygon_area(RECT) == 280.0


def test_polygon_area_is_orientation_independent():
    assert polygon_area(list(reversed(RECT))) == 280.0


def test_polygon_area_needs_three_points():
    assert polygon_area([(0.0, 0.0), (1.0, 1.0)]) == 0.0


def test_normalize_closed_drops_duplicate_vertex():
    with_closing = RECT + [(0.0, 0.0)]
    assert normalize_closed(with_closing, closed=True) == RECT


def test_normalize_closed_leaves_open_path_untouched():
    with_closing = RECT + [(0.0, 0.0)]
    assert normalize_closed(with_closing, closed=False) == with_closing


def test_bbox_of_prims():
    prims = [PolylinePrim(pts=RECT, closed=True)]
    assert bbox_of_prims(prims) == (0.0, 0.0, 20.0, 14.0)


def test_bbox_of_prims_empty_is_none():
    assert bbox_of_prims([]) is None


def test_bbox_of_text_prim_uses_rotated_corners():
    prim = TextPrim(p=(0.0, 0.0), text="AB", height=2.0, rotation=90.0)
    min_x, min_y, max_x, max_y = bbox_of_prims([prim])
    # Largura aproximada 2 * 2.0 * 0.6 = 2.4, rotacionada 90 graus.
    assert math.isclose(max_y, 2.4, abs_tol=1e-9)
    assert math.isclose(min_x, -2.0, abs_tol=1e-9)
    assert math.isclose(min_y, 0.0, abs_tol=1e-9)
    assert math.isclose(max_x, 0.0, abs_tol=1e-9)


def test_bbox_intersects_and_contains():
    outer = (0.0, 0.0, 10.0, 10.0)
    inner = (2.0, 2.0, 4.0, 4.0)
    outside = (20.0, 20.0, 30.0, 30.0)

    assert bbox_intersects(outer, inner)
    assert bbox_contains(outer, inner)
    assert not bbox_intersects(outer, outside)
    assert not bbox_contains(inner, outer)


def test_distance_point_segment_perpendicular():
    assert distance_point_segment((5.0, 3.0), (0.0, 0.0), (10.0, 0.0)) == 3.0


def test_distance_point_segment_clamps_to_endpoints():
    assert distance_point_segment((-4.0, 0.0), (0.0, 0.0), (10.0, 0.0)) == 4.0


def test_distance_point_segment_degenerate_segment():
    assert distance_point_segment((3.0, 4.0), (0.0, 0.0), (0.0, 0.0)) == 5.0
