"""Gera o DXF sintetico usado pelos testes.

O desenho e proposital: cada entidade existe para exercitar um caminho do
indexador, e as medidas sao numeros redondos para que os testes possam afirmar
valores EXATOS. Assertiva aproximada aqui nao serve — na implementacao de
referencia um `>= 18` esconderia um bug de indexacao por muito tempo.
"""

from pathlib import Path

import ezdxf
from ezdxf.document import Drawing

# Retangulo 20 x 14 -> perimetro 68, area 280.
CONTOUR = [(0.0, 0.0), (20.0, 0.0), (20.0, 14.0), (0.0, 14.0)]


def build_sample_doc() -> Drawing:
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 6  # metros
    msp = doc.modelspace()

    doc.layers.add("CONTORNO", color=1)
    doc.layers.add("PAREDES", color=2)
    doc.layers.add("TEXTOS", color=3)
    doc.layers.add("MOBILIARIO", color=4)
    doc.layers.add("COTAS", color=5)
    congelada = doc.layers.add("AUXILIAR", color=8)
    congelada.freeze()

    # 1 LWPOLYLINE fechada — o contorno cujo perimetro/area os testes fixam.
    msp.add_lwpolyline(CONTOUR, close=True, dxfattribs={"layer": "CONTORNO"})

    # 2 LINE
    msp.add_line((0, 7), (20, 7), dxfattribs={"layer": "PAREDES"})
    msp.add_line((10, 0), (10, 14), dxfattribs={"layer": "PAREDES"})

    # 1 LWPOLYLINE com bulge — verifica conversao bulge -> arco.
    msp.add_lwpolyline(
        [(2.0, 2.0, 0.0, 0.0, 0.5), (8.0, 2.0, 0.0, 0.0, 0.0)],
        format="xyseb",
        dxfattribs={"layer": "PAREDES"},
    )

    # 1 CIRCLE + 1 ARC — amostragem de curva.
    msp.add_circle((5, 10), 2, dxfattribs={"layer": "MOBILIARIO"})
    msp.add_arc((15, 10), 3, 0, 90, dxfattribs={"layer": "MOBILIARIO"})

    # 1 SPLINE — verifica avaliacao de spline.
    msp.add_spline(
        [(12, 2), (14, 5), (16, 2), (18, 5)], dxfattribs={"layer": "MOBILIARIO"}
    )

    # 1 POINT
    msp.add_point((1, 1), dxfattribs={"layer": "AUXILIAR"})

    # 1 TEXT + 1 MTEXT — o MTEXT carrega escapes de formatacao a limpar.
    msp.add_text("PLAIN", height=1.0, dxfattribs={"layer": "TEXTOS"}).set_placement(
        (1, 15)
    )
    msp.add_mtext(
        "{\\fArial|b1;PLANTA BAIXA}\\PESCALA 1:50",
        dxfattribs={"layer": "TEXTOS", "char_height": 1.0},
    ).set_location((1, 17))

    # 1 bloco PORTA com 3 insercoes — verifica INSERT e contagem de blocos.
    porta = doc.blocks.new("PORTA")
    porta.add_line((0, 0), (0.9, 0))
    porta.add_arc((0, 0), 0.9, 0, 90)
    for index in range(3):
        msp.add_blockref(
            "PORTA", (2 + index * 5, 4), dxfattribs={"layer": "MOBILIARIO"}
        )

    # 1 DIMENSION — geometria vive num bloco anonimo.
    msp.add_linear_dim(
        base=(0, -2), p1=(0, 0), p2=(20, 0), dxfattribs={"layer": "COTAS"}
    ).render()

    return doc


def write_sample(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    build_sample_doc().saveas(path)
    return path


if __name__ == "__main__":
    # `__file__` e confiavel aqui porque este script nao e empacotado.
    target = Path(__file__).parent / "fixtures" / "sample.dxf"
    print(write_sample(target))
