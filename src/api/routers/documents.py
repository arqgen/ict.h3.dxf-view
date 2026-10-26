from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from src.api.core.config import Settings, get_app_settings
from src.api.logger import logger
from src.api.models.document import (
    DocumentResponse,
    EntityDetailsResponse,
    PrimsResponse,
    to_document_response,
    to_prims_response,
)
from src.api.store import DocumentStore, get_document_store
from src.cad.model import AqgLoadError, load_aqg

router = APIRouter(prefix="/api/documents", tags=["documents"])

StoreDep = Annotated[DocumentStore, Depends(get_document_store)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    store: StoreDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File(description="Arquivo AQG (.json)")],
) -> DocumentResponse:
    """Indexa um AQG e devolve seus metadados."""
    data = await file.read()

    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"arquivo maior que o limite de {settings.MAX_UPLOAD_MB} MB",
        )

    filename = file.filename or "projeto.json"
    try:
        model = load_aqg(data, filename)
    except AqgLoadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    # Um projeto sem geometria nao tem nada a mostrar nem a consultar —
    # aceitar geraria um viewer vazio e um agente sem dados.
    if not model.entities:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="o arquivo não contém geometria desenhável",
        )

    document_id = store.put(model)
    logger.info("documento %s: %s", document_id, filename)

    return to_document_response(document_id, model)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, store: StoreDep) -> DocumentResponse:
    model = _require(store, document_id)
    return to_document_response(document_id, model)


@router.get("/{document_id}/prims", response_model=PrimsResponse)
async def get_document_prims(document_id: str, store: StoreDep) -> PrimsResponse:
    """Geometria achatada para o canvas. Substitui o parse no browser."""
    model = _require(store, document_id)
    return to_prims_response(document_id, model)


@router.get("/{document_id}/entities/{entity_id}", response_model=EntityDetailsResponse)
async def get_entity(
    document_id: str, entity_id: str, store: StoreDep
) -> EntityDetailsResponse:
    model = _require(store, document_id)

    entity = model.by_id.get(entity_id)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"entidade {entity_id} nao existe neste documento",
        )

    instance = model.instances.get(entity.instance) if entity.instance else None
    family = next(
        (f for f in model.families if instance and f.label == instance.family), None
    )

    return EntityDetailsResponse(
        id=entity.id,
        type=entity.type,
        layer=entity.layer,
        color=entity.color,
        bbox=list(entity.bbox) if entity.bbox else None,
        closed=entity.closed,
        length=entity.length,
        area=entity.area,
        text=entity.text,
        instance=entity.instance,
        family=entity.family,
        hid=instance.hid if instance else None,
        properties=family.properties if family else {},
    )


def _require(store: DocumentStore, document_id: str):
    model = store.get(document_id)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="documento nao encontrado ou expirado — envie o arquivo novamente",
        )
    return model
