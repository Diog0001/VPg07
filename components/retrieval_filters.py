"""Фильтры Pinecone для памяти диалога и чанков документов."""

from __future__ import annotations

from typing import Any


def memory_kinds_filter(user_id: int, kinds: frozenset[str]) -> dict[str, Any]:
    return {
        "operator": "AND",
        "conditions": [
            {"field": "meta.user_id", "operator": "==", "value": str(user_id)},
            {"field": "meta.kind", "operator": "in", "value": sorted(kinds)},
        ],
    }


def document_chunks_filter(user_id: int) -> dict[str, Any]:
    return {
        "operator": "AND",
        "conditions": [
            {"field": "meta.user_id", "operator": "==", "value": str(user_id)},
            {"field": "meta.kind", "operator": "==", "value": "document_chunk"},
        ],
    }


def user_only_filter(user_id: int) -> dict[str, Any]:
    return {
        "field": "meta.user_id",
        "operator": "==",
        "value": str(user_id),
    }
