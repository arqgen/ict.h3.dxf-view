"""Store de documentos em memoria — o unico estado do servidor.

Nao ha banco por decisao de escopo: um documento vive enquanto a aba do usuario
estiver aberta. O limite de itens e o TTL existem para que uma sessao esquecida
nao segure o indice de um DXF grande na RAM indefinidamente.
"""

import time
import uuid
from dataclasses import dataclass

from src.api.core.config import get_app_settings
from src.api.logger import logger
from src.cad.model import CadModel


@dataclass(slots=True)
class StoredDocument:
    id: str
    model: CadModel
    created_at: float
    last_used_at: float


class DocumentStore:
    def __init__(self, max_documents: int, ttl_seconds: int) -> None:
        self._documents: dict[str, StoredDocument] = {}
        self._max_documents = max_documents
        self._ttl_seconds = ttl_seconds

    def put(self, model: CadModel) -> str:
        self._evict_expired()

        document_id = uuid.uuid4().hex
        now = time.monotonic()
        self._documents[document_id] = StoredDocument(
            id=document_id, model=model, created_at=now, last_used_at=now
        )

        self._evict_overflow()
        logger.info(
            "documento %s indexado (%s entidades) — %s em memoria",
            document_id,
            len(model.entities),
            len(self._documents),
        )
        return document_id

    def get(self, document_id: str) -> CadModel | None:
        self._evict_expired()

        stored = self._documents.get(document_id)
        if stored is None:
            return None

        stored.last_used_at = time.monotonic()
        return stored.model

    def _evict_expired(self) -> None:
        cutoff = time.monotonic() - self._ttl_seconds
        expired = [
            key for key, doc in self._documents.items() if doc.last_used_at < cutoff
        ]
        for key in expired:
            del self._documents[key]
            logger.info("documento %s expirado e removido do store", key)

    def _evict_overflow(self) -> None:
        while len(self._documents) > self._max_documents:
            oldest = min(self._documents.values(), key=lambda doc: doc.last_used_at)
            del self._documents[oldest.id]
            logger.info("documento %s removido por limite de store", oldest.id)


_store: DocumentStore | None = None


def get_document_store() -> DocumentStore:
    """Dependency do FastAPI. Um store por processo."""
    global _store
    if _store is None:
        settings = get_app_settings()
        _store = DocumentStore(
            max_documents=settings.MAX_DOCUMENTS,
            ttl_seconds=settings.DOCUMENT_TTL_SECONDS,
        )
    return _store
