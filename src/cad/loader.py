"""Leitura de arquivo DXF.

`ezdxf.readfile` ja autodetecta encoding legado (cp1252 em DXF antigos de
AutoCAD brasileiro) lendo `$DWGCODEPAGE`/`$ACADVER` antes de reabrir o arquivo.
Nao ha nada a fazer sobre encoding aqui.
"""

from io import BytesIO, TextIOWrapper

import ezdxf
import ezdxf.filemanagement
import ezdxf.recover
from ezdxf.document import Drawing

from src.api.logger import logger


class DxfLoadError(Exception):
    """Arquivo nao e um DXF legivel, nem apos tentativa de recuperacao."""


def load_dxf(data: bytes) -> tuple[Drawing, list[str]]:
    """Le um DXF em memoria. Devolve o documento e os avisos de recuperacao.

    Tenta o caminho rapido primeiro; so cai no `ezdxf.recover` se o arquivo
    estiver estruturalmente danificado.
    """
    try:
        return ezdxf.read(_as_text_stream(data)), []
    except Exception as exc:
        logger.warning("leitura direta do DXF falhou (%s) — tentando recover", exc)

    try:
        doc, auditor = ezdxf.recover.read(BytesIO(data))
    except Exception as exc:
        raise DxfLoadError(f"nao foi possivel ler o arquivo DXF: {exc}") from exc

    warnings = [str(error.message) for error in auditor.errors]
    warnings += [str(error.message) for error in auditor.fixes]

    return doc, warnings


def _as_text_stream(data: bytes) -> TextIOWrapper:
    """Envolve os bytes num stream de texto com o encoding declarado no arquivo.

    `ezdxf.read` espera texto. Reproduzimos a deteccao que `readfile` faz para
    arquivo em disco: ler o cabecalho para descobrir o encoding, depois reabrir.
    Cada `TextIOWrapper` recebe seu proprio `BytesIO` porque o wrapper fecha o
    buffer subjacente ao ser coletado.
    """
    head = TextIOWrapper(BytesIO(data), encoding="utf-8", errors="ignore")
    info = ezdxf.filemanagement.dxf_stream_info(head)

    return TextIOWrapper(BytesIO(data), encoding=info.encoding, errors="replace")
