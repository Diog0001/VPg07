"""
Долговременная память пользователей через Haystack PineconeDocumentStore (metric=cosine).
"""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass
from typing import Any, Literal, Mapping

from haystack import Document
from haystack.components.embedders import OpenAIDocumentEmbedder, OpenAITextEmbedder
from haystack.document_stores.types import DuplicatePolicy
from haystack_integrations.components.retrievers.pinecone import PineconeEmbeddingRetriever
from haystack_integrations.document_stores.pinecone import PineconeDocumentStore

from components.document_store_factory import create_pinecone_document_store
from components.retrieval_filters import memory_kinds_filter, user_only_filter
from config import load_project_env

logger = logging.getLogger(__name__)

MEMORY_COSINE_SIMILARITY_THRESHOLD: float = 0.74

DuplicatePolicyAction = Literal["skip", "update"]
MemoryAction = Literal["inserted", "updated", "skipped"]


@dataclass
class MemoryStoreResult:
    action: MemoryAction
    memory_id: str | None
    similarity: float | None
    matched_id: str | None = None
    is_duplicate: bool = False


class HaystackUserMemory:
    """Память чата: запись и семантический поиск в Pinecone через Haystack."""

    def __init__(
        self,
        *,
        document_store: PineconeDocumentStore | None = None,
        namespace: str | None = None,
        embedding_model: str | None = None,
        embedding_dimensions: int | None = None,
        load_env: bool = True,
    ) -> None:
        if load_env:
            load_project_env()

        self.namespace = namespace or os.getenv("PINECONE_MEMORY_NAMESPACE", "telegram-users")
        self.embedding_model = embedding_model or os.getenv(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
        )
        self.embedding_dimensions = self._resolve_dimensions(embedding_dimensions)

        self.document_store = document_store or create_pinecone_document_store(
            namespace=self.namespace,
            load_env=False,
        )

        embedder_kwargs: dict[str, Any] = {"model": self.embedding_model}
        if self.embedding_dimensions is not None:
            embedder_kwargs["dimensions"] = self.embedding_dimensions

        self._document_embedder = OpenAIDocumentEmbedder(**embedder_kwargs)
        self._text_embedder = OpenAITextEmbedder(**embedder_kwargs)
        self._retriever = PineconeEmbeddingRetriever(
            document_store=self.document_store,
            top_k=10,
        )

    def _search_by_embedding(
        self,
        embedding: list[float],
        *,
        filters: dict[str, Any],
        top_k: int,
    ) -> list[Document]:
        result = self._retriever.run(
            query_embedding=embedding,
            filters=filters,
            top_k=top_k,
        )
        return list(result.get("documents") or [])

    def retrieve_relevant(
        self,
        user_id: int,
        query_text: str,
        *,
        top_k: int = 6,
        kinds: frozenset[str],
    ) -> list[Document]:
        embedding = self._text_embedder.run(text=query_text)["embedding"]
        return self._search_by_embedding(
            embedding,
            filters=memory_kinds_filter(user_id, kinds),
            top_k=top_k,
        )

    def remember_message(
        self,
        text: str,
        *,
        metadata: Mapping[str, Any],
        user_id: int,
        memory_id: str | None = None,
        similarity_threshold: float | None = None,
        on_duplicate: DuplicatePolicyAction = "update",
    ) -> MemoryStoreResult:
        threshold = (
            MEMORY_COSINE_SIMILARITY_THRESHOLD
            if similarity_threshold is None
            else similarity_threshold
        )
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Порог косинусного сходства должен быть в [0, 1].")

        cleaned = text.strip()
        if not cleaned:
            return MemoryStoreResult(
                action="skipped",
                memory_id=None,
                similarity=None,
                is_duplicate=False,
            )

        embedding = self._text_embedder.run(text=cleaned)["embedding"]
        documents = self._search_by_embedding(
            embedding,
            filters=user_only_filter(user_id),
            top_k=1,
        )

        if not documents:
            new_id = memory_id or f"mem-{uuid.uuid4().hex}"
            self._write_document(new_id, cleaned, dict(metadata))
            return MemoryStoreResult(
                action="inserted",
                memory_id=new_id,
                similarity=None,
                is_duplicate=False,
            )

        best = documents[0]
        similarity = float(best.score if best.score is not None else 0.0)
        matched_id = str(best.id)

        if similarity < threshold:
            new_id = memory_id or f"mem-{uuid.uuid4().hex}"
            self._write_document(new_id, cleaned, dict(metadata))
            return MemoryStoreResult(
                action="inserted",
                memory_id=new_id,
                similarity=similarity,
                matched_id=matched_id,
                is_duplicate=False,
            )

        if on_duplicate == "skip":
            return MemoryStoreResult(
                action="skipped",
                memory_id=matched_id,
                similarity=similarity,
                matched_id=matched_id,
                is_duplicate=True,
            )

        merged_meta = dict(best.meta or {})
        merged_meta.update(dict(metadata))
        self._write_document(matched_id, cleaned, merged_meta, embedding=embedding)
        return MemoryStoreResult(
            action="updated",
            memory_id=matched_id,
            similarity=similarity,
            matched_id=matched_id,
            is_duplicate=True,
        )

    def delete_user_memory(self, user_id: int) -> None:
        self.document_store.delete_by_filter(filters=user_only_filter(user_id))

    def count_user_documents(self, user_id: int) -> int:
        return int(
            self.document_store.count_documents_by_filter(
                filters=user_only_filter(user_id)
            )
        )

    def count_document_chunks(self, user_id: int) -> int:
        from components.retrieval_filters import document_chunks_filter

        return int(
            self.document_store.count_documents_by_filter(
                filters=document_chunks_filter(user_id)
            )
        )

    def _write_document(
        self,
        doc_id: str,
        content: str,
        meta: dict[str, Any],
        *,
        embedding: list[float] | None = None,
    ) -> None:
        meta = dict(meta)
        meta.setdefault("text", content)
        document = Document(id=doc_id, content=content, meta=meta)
        if embedding is not None:
            document.embedding = embedding
            self.document_store.write_documents(
                [document],
                policy=DuplicatePolicy.OVERWRITE,
            )
            return

        embedded = self._document_embedder.run(documents=[document])["documents"]
        self.document_store.write_documents(
            embedded,
            policy=DuplicatePolicy.OVERWRITE,
        )

    def _resolve_dimensions(self, embedding_dimensions: int | None) -> int | None:
        if embedding_dimensions is not None:
            return embedding_dimensions
        env_value = os.getenv("OPENAI_EMBEDDING_DIMENSIONS")
        if env_value:
            return int(env_value)
        return 1536
