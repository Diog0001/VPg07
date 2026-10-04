"""Оркестрация загрузки файла: ingestion + резюме."""

from __future__ import annotations

from typing import Any

from components.memory_service import HaystackUserMemory
from pipelines.ingestion import IngestionPipeline, IngestionResult
from pipelines.summarization import SummarizationPipeline


class IngestionService:
    def __init__(self, memory: HaystackUserMemory) -> None:
        self._memory = memory
        self._ingestion: IngestionPipeline | None = None
        self._summarizer = SummarizationPipeline()

    def _get_ingestion(self) -> IngestionPipeline:
        if self._ingestion is None:
            self._ingestion = IngestionPipeline(self._memory.document_store)
        return self._ingestion

    def ingest_file(
        self,
        *,
        file_bytes: bytes,
        file_name: str,
        user_id: int,
        chat_id: int,
        extra_meta: dict[str, Any] | None = None,
    ) -> tuple[IngestionResult, str]:
        result = self._get_ingestion().run(
            file_bytes=file_bytes,
            file_name=file_name,
            user_id=user_id,
            chat_id=chat_id,
            extra_meta=extra_meta,
        )
        summary = self._summarizer.summarize_chunks(result.enriched_documents)
        return result, summary
