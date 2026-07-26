import httpx
from agno.media import File
from agno.tools import tool
from agno.tools.function import ToolResult

from src.api.logger import logger

MAX_PDF_BYTES = 20 * 1024 * 1024  # limite prático da OpenAI é ~32 MB pós-base64
DOWNLOAD_TIMEOUT_SECONDS = 30.0


def _filename_from_url(url: str) -> str:
    name = url.split("?")[0].rstrip("/").split("/")[-1] or "document.pdf"
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name


@tool(
    name="fetch_pdf",
    description=(
        "Baixa um arquivo PDF de uma URL pública e o anexa ao contexto para "
        "que o agente possa ler o conteúdo diretamente (texto e tabelas)."
        "Use quando a informação necessária estiver dentro de um PDF — anexos de"
        "lei, tabelas de parâmetros urbanísticos, normas, memoriais. "
    ),
    instructions=(
        "Baixe um PDF por vez e leia o conteúdo anexado antes de decidir buscar "
        "outro documento."
    ),
)
async def fetch_pdf(url: str) -> ToolResult:
    """Baixa um arquivo PDF de uma URL pública e o anexa ao contexto para
    você ler o conteúdo diretamente (texto e tabelas).

    Use quando a informação necessária estiver dentro de um PDF — anexos de
    lei, tabelas de parâmetros urbanísticos, normas, memoriais — já que o
    `web_scrape` só extrai páginas HTML. Baixe um PDF por vez e leia o
    conteúdo anexado antes de decidir buscar outro documento.

    Args:
        url: string contendo a URL pública do arquivo PDF.

    Returns:
        ToolResult: com o PDF anexado como mídia em caso de sucesso, ou uma
        mensagem de erro descritiva se o download falhar, o conteúdo não for
        um PDF ou o arquivo exceder o limite de tamanho.
    """
    try:
        async with httpx.AsyncClient(
            timeout=DOWNLOAD_TIMEOUT_SECONDS, follow_redirects=True
        ) as client:
            response = await client.get(url)
    except httpx.HTTPError as exc:
        logger.warning(f"fetch_pdf: falha ao baixar {url}: {exc}")
        return ToolResult(content=f"Erro ao baixar o PDF de {url}: {exc}")

    if response.status_code != 200:
        return ToolResult(
            content=f"Erro ao baixar o PDF de {url}: HTTP {response.status_code}."
        )

    pdf_bytes = response.content
    if not pdf_bytes.startswith(b"%PDF"):
        return ToolResult(
            content=(
                f"O conteúdo de {url} não é um PDF. "
                "Se for uma página HTML, use `web_scrape`."
            )
        )

    if len(pdf_bytes) > MAX_PDF_BYTES:
        size_mb = len(pdf_bytes) / (1024 * 1024)
        return ToolResult(
            content=(
                f"O PDF de {url} tem {size_mb:.1f} MB e excede o limite de "
                f"{MAX_PDF_BYTES // (1024 * 1024)} MB. Procure uma versão "
                "menor ou uma fonte alternativa (ex: página HTML da lei)."
            )
        )

    logger.debug(f"fetch_pdf: {url} baixado ({len(pdf_bytes)} bytes)")
    return ToolResult(
        content=f"PDF de {url} anexado ao contexto para leitura.",
        files=[
            File(
                content=pdf_bytes,
                mime_type="application/pdf",
                filename=_filename_from_url(url),
            )
        ],
    )
