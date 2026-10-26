"""Gera o Project AQG sintetico usado pelos testes.

Cada elemento existe para exercitar um caminho do indice, e as medidas sao
numeros redondos para que os testes possam afirmar valores EXATOS.
"""

from typing import Any


def rect(x0: float, y0: float, x1: float, y1: float) -> list:
    return [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]


def _polygon(coords: list) -> dict[str, Any]:
    return {"type": "Polygon", "coordinates": coords}


def _volume(class_path: str, geometry: dict[str, Any]) -> dict[str, Any]:
    return {"class_path": class_path, "height": None, "geometry": geometry}


def _site_element(layer: str, cad_type: str, geometry: dict) -> dict[str, Any]:
    return {"cad": {"layer": layer, "type": cad_type, "geometry": geometry}}


def _placed_family(hid: str, x: float, y: float, angle: float) -> dict[str, Any]:
    return {
        "type": "PlacedFamily",
        "hid": hid,
        "position": {"x": x, "y": y, "z": 0, "angle": angle},
    }


def _placed_element(
    label: str, hid: str, layer: str, cad_type: str, geometry: dict
) -> dict[str, Any]:
    return {
        "type": "PlacedElement",
        "label": label,
        "hid": hid,
        "cad": {"layer": layer, "type": cad_type, "geometry": geometry},
    }


def build_sample_project() -> dict[str, Any]:
    tower = {
        "class_path": "/building/torre/T/4/0i/2f",
        "label": "T/4",
        "properties": {"type": "Tower", "total_pavimentos": 2},
        "drawing_elements": [],
        "volume": [
            _volume("/area/apartamento/2 Quartos/aaaa", _polygon(rect(0, 0, 5, 10))),
            _volume("/area/apartamento/2 Quartos/aaaa", _polygon(rect(5, 0, 10, 10))),
            _volume("/area/varanda/2 Quartos", _polygon(rect(0, 10, 10, 11))),
            _volume("/area/shaft/privativo", _polygon(rect(0, 11, 1, 12))),
            _volume("/core", _polygon(rect(0, 0, 10, 20))),
            _volume("/reference/envelope", _polygon(rect(0, 0, 10, 20))),
            _volume(
                "/road_access/Endline",
                {"type": "LineString", "coordinates": [[0, 0], [10, 0]]},
            ),
            _volume("/access/mandatory", _polygon(rect(0, -1, 10, 0))),
        ],
    }
    parking = {
        "class_path": "/equipment/vaga/simples/front_access/P/0",
        "label": "0",
        "properties": {"type": "Vaga", "unidades": 1},
        "drawing_elements": [],
        "volume": [
            _volume("/core", _polygon(rect(0, 0, 2.5, 5))),
            _volume("/core/zito", _polygon(rect(0, 0, 2.5, 0.5))),
            _volume("/access/mandatory", _polygon(rect(0, 5, 2.5, 6))),
        ],
    }

    talude = {
        "type": "MultiPolygon",
        "coordinates": [
            [
                rect(60, 50, 80, 64)[0],
                [[65, 55], [67, 55], [67, 57], [65, 57], [65, 55]],
            ]
        ],
    }

    return {
        "version": "18.0.0",
        "archprog": [],
        "families": [tower, parking],
        "site": {
            "elements": [
                _site_element(
                    "AQG_PERIMETRO", "CadPolygon", _polygon(rect(0, 0, 100, 80))
                ),
                _site_element(
                    "AQG_FRENTE",
                    "CadPolyline",
                    {"type": "LineString", "coordinates": [[0, 0], [100, 0]]},
                ),
                _site_element(
                    "AQG_CURVA_DE_NIVEL_MESTRA",
                    "CadPolyline",
                    {
                        "type": "LinearRing",
                        "coordinates": [
                            [10, 60],
                            [30, 60],
                            [30, 70],
                            [10, 70],
                            [10, 60],
                        ],
                    },
                ),
                _site_element(
                    "AQG_PORTARIA",
                    "CadBlock",
                    {"type": "Point", "coordinates": [50, 75]},
                ),
                _site_element(
                    "topografia",
                    "CadMesh",
                    {"type": "MultiPoint", "coordinates": [[0, 0, 1], [1, 1, 2]]},
                ),
            ],
            "inputs": [
                {"type": "CAMaximoExigido", "value": 2.9},
                {"type": "Municipio", "value": "Florianópolis"},
            ],
            "processed_info": [{"type": "AreaDoTerreno", "value": 8000}],
        },
        "solution": {
            "road_network": None,
            "annotations": [],
            "placed_objects": [
                _placed_family("/building/torre/T/4/0i/2f/11111111", 20, 10, 0),
                _placed_family("/building/torre/T/4/0i/2f/22222222", 60, 10, 90),
                _placed_family("/equipment/vaga/simples/front_access", 5, 40, 0),
                _placed_family("/equipment/vaga/simples/front_access", 8, 40, 0),
                _placed_element(
                    "talude", "/talude/t1", "talude", "CadMultiPolygon", talude
                ),
                _placed_element(
                    "rua",
                    "/road_network/r1",
                    "AQG_RUA",
                    "CadPolygon",
                    _polygon(rect(0, 70, 100, 75)),
                ),
                _placed_family("/building/inexistente/x", 0, 0, 0),
            ],
            "outputs": [
                {"type": "TotalDeTorres", "value": 2},
                {"type": "TotalDeUnidades", "value": 37},
                {"type": "AreaTotalConstruida", "value": 1234.5},
                {"type": "CAProjetado", "value": 1.78},
                {
                    "type": "DescritivoTorre",
                    "label": "01",
                    "order_index": 0,
                    "unidades": 20,
                },
                {
                    "type": "DescritivoTorre",
                    "label": "02",
                    "order_index": 1,
                    "unidades": 17,
                },
            ],
            "scores": {"total": 0.65, "alignment": 0.94},
        },
    }
