from typing import Any

from pydantic import BaseModel, Field

from src.cad.model import CadModel, prims_payload


class LayerInfo(BaseModel):
    name: str
    color: str
    count: int
    by_type: dict[str, int]
    bbox: list[float] | None
    frozen: bool
    on: bool


class DocumentResponse(BaseModel):
    """Metadados do documento indexado — o que o painel lateral mostra."""

    document_id: str
    filename: str
    units: str
    acad_version: str
    bbox: list[float] | None
    entity_count: int
    layer_count: int
    block_count: int
    insert_count: int
    by_type: dict[str, int]
    layers: list[LayerInfo]
    warnings: list[str]


class PrimsResponse(BaseModel):
    """Geometria achatada para o canvas desenhar."""

    document_id: str
    bbox: list[float] | None
    entities: list[dict[str, Any]]


class EntityDetailsResponse(BaseModel):
    id: str
    type: str
    layer: str
    color: str
    bbox: list[float] | None
    closed: bool
    length: float | None
    area: float | None
    text: str | None
    block: str | None
    raw: dict[str, Any] = Field(default_factory=dict)


def to_document_response(document_id: str, model: CadModel) -> DocumentResponse:
    return DocumentResponse(
        document_id=document_id,
        filename=model.filename,
        units=model.units,
        acad_version=model.acad_version,
        bbox=list(model.bbox) if model.bbox else None,
        entity_count=len(model.entities),
        layer_count=len(model.layers),
        block_count=len(model.block_names),
        insert_count=sum(model.insert_counts.values()),
        by_type=model.by_type,
        layers=[
            LayerInfo(
                name=layer.name,
                color=layer.color,
                count=layer.count,
                by_type=layer.by_type,
                bbox=list(layer.bbox) if layer.bbox else None,
                frozen=layer.frozen,
                on=layer.on,
            )
            for layer in model.layers
        ],
        warnings=model.warnings,
    )


def to_prims_response(document_id: str, model: CadModel) -> PrimsResponse:
    return PrimsResponse(
        document_id=document_id,
        bbox=list(model.bbox) if model.bbox else None,
        entities=prims_payload(model),
    )
