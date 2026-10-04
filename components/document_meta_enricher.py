"""Обогащение чанков Docling метаданными пользователя и файла."""

from __future__ import annotations

import json
import uuid
from typing import Any

from haystack import Document, component


def _page_from_meta(meta: dict[str, Any]) -> int | None:
    if "page_number" in meta and meta["page_number"] is not None:
        try:
            return int(meta["page_number"])
        except (TypeError, ValueError):
            pass
    dl_meta = meta.get("dl_meta")
    if isinstance(dl_meta, dict):
        page = dl_meta.get("page_number")
        if page is not None:
            try:
                return int(page)
            except (TypeError, ValueError):
                pass
    return None


def _sanitize_meta_for_pinecone(meta: dict[str, Any]) -> dict[str, Any]:
    """Pinecone принимает только str, int, bool и list[str] — вложенные dict отбрасываются."""
    safe: dict[str, Any] = {}
    for key, value in meta.items():
        if key == "dl_meta":
            if value is not None:
                try:
                    blob = json.dumps(value, ensure_ascii=False)
                    if len(blob) > 30_000:
                        blob = blob[:30_000]
                    safe["dl_meta_json"] = blob
                except (TypeError, ValueError):
                    pass
            continue
        if isinstance(value, bool):
            safe[key] = value
        elif isinstance(value, int):
            safe[key] = value
        elif isinstance(value, str):
            safe[key] = value
        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
            safe[key] = value
        elif value is not None:
            safe[key] = str(value)
    return safe


@component
class DocumentMetaEnricher:
    """Добавляет user_id, kind, file_name, chunk_index и стабильные id для Pinecone."""

    @component.output_types(documents=list[Document])
    def run(
        self,
        documents: list[Document],
        *,
        user_id: str,
        file_name: str,
        chat_id: str = "",
        extra_meta: dict[str, Any] | None = None,
    ) -> dict[str, list[Document]]:
        extra = dict(extra_meta or {})
        enriched: list[Document] = []

        for index, doc in enumerate(documents):
            meta = dict(doc.meta or {})
            split_id = meta.get("split_id", index)
            try:
                chunk_index = int(split_id)
            except (TypeError, ValueError):
                chunk_index = index

            page_number = _page_from_meta(meta)

            meta.update(extra)
            meta["user_id"] = str(user_id)
            meta["kind"] = "document_chunk"
            meta["file_name"] = file_name
            meta["chunk_index"] = chunk_index
            if chat_id:
                meta["chat_id"] = str(chat_id)
            if page_number is not None:
                meta["page_number"] = page_number
            meta.setdefault("text", (doc.content or "").strip())
            meta = _sanitize_meta_for_pinecone(meta)

            doc_id = f"doc-{user_id}-{uuid.uuid4().hex}"
            enriched.append(
                Document(
                    id=doc_id,
                    content=doc.content,
                    meta=meta,
                )
            )

        return {"documents": enriched}
