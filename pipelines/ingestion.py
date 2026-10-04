"""Пайплайн индексации: Docling → метаданные → эмбеддинги → Pinecone."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from haystack import Pipeline
from haystack.components.embedders import OpenAIDocumentEmbedder
from haystack.components.writers import DocumentWriter
from haystack.document_stores.types import DuplicatePolicy
from haystack_integrations.document_stores.pinecone import PineconeDocumentStore

from components.docling_factory import create_document_converter, write_upload_temp_file
from components.document_meta_enricher import DocumentMetaEnricher
from config import load_project_env


@dataclass
class IngestionResult:
    documents_written: int
    enriched_documents: list
    file_name: str


class IngestionPipeline:
    def __init__(
        self,
        document_store: PineconeDocumentStore,
        *,
        embedding_model: str | None = None,
        embedding_dimensions: int | None = None,
    ) -> None:
        load_project_env()
        self._embedding_model = embedding_model or os.getenv(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
        )
        dims = embedding_dimensions
        if dims is None and os.getenv("OPENAI_EMBEDDING_DIMENSIONS"):
            dims = int(os.getenv("OPENAI_EMBEDDING_DIMENSIONS", "1536"))

        embedder_kwargs: dict[str, Any] = {"model": self._embedding_model}
        if dims is not None:
            embedder_kwargs["dimensions"] = dims

        try:
            from docling.chunking import HybridChunker
            from haystack_integrations.components.converters.docling import (
                DoclingConverter,
                ExportType,
            )
        except ImportError as exc:
            raise ImportError(
                "Для обработки файлов установите зависимости: "
                "pip install docling-haystack docling"
            ) from exc

        chunk_tokenizer = os.getenv(
            "DOC_CHUNK_TOKENIZER",
            "sentence-transformers/all-MiniLM-L6-v2",
        )
        converter = DoclingConverter(
            converter=create_document_converter(),
            export_type=ExportType.DOC_CHUNKS,
            chunker=HybridChunker(tokenizer=chunk_tokenizer),
        )

        self._pipeline = Pipeline()
        self._pipeline.add_component("converter", converter)
        self._pipeline.add_component("enricher", DocumentMetaEnricher())
        self._pipeline.add_component("embedder", OpenAIDocumentEmbedder(**embedder_kwargs))
        self._pipeline.add_component(
            "writer",
            DocumentWriter(document_store=document_store, policy=DuplicatePolicy.OVERWRITE),
        )

        self._pipeline.connect("converter.documents", "enricher.documents")
        self._pipeline.connect("enricher.documents", "embedder.documents")
        self._pipeline.connect("embedder.documents", "writer.documents")

    def run(
        self,
        *,
        file_bytes: bytes,
        file_name: str,
        user_id: int,
        chat_id: int,
        extra_meta: dict[str, Any] | None = None,
    ) -> IngestionResult:
        temp_path = write_upload_temp_file(file_bytes, file_name)
        try:
            result = self._pipeline.run(
                {
                    "converter": {"sources": [str(temp_path)]},
                    "enricher": {
                        "user_id": str(user_id),
                        "file_name": file_name,
                        "chat_id": str(chat_id),
                        "extra_meta": extra_meta or {},
                    },
                }
            )
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

        written = int(result.get("writer", {}).get("documents_written") or 0)
        enriched = list(result.get("enricher", {}).get("documents") or [])
        return IngestionResult(
            documents_written=written,
            enriched_documents=enriched,
            file_name=file_name,
        )
