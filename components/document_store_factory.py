"""Фабрика Pinecone DocumentStore для пайплайнов и сервисов."""

from __future__ import annotations

import os
from typing import Any

from haystack_integrations.document_stores.pinecone import PineconeDocumentStore

from config import load_project_env


def create_pinecone_document_store(
    *,
    namespace: str | None = None,
    load_env: bool = True,
) -> PineconeDocumentStore:
    if load_env:
        load_project_env()

    index_name = os.getenv("PINECONE_INDEX_NAME", "default")
    ns = namespace if namespace is not None else os.getenv("PINECONE_MEMORY_NAMESPACE", "telegram-users")

    pinecone_cloud = os.getenv("PINECONE_CLOUD", "aws")
    pinecone_region = os.getenv("PINECONE_REGION", "us-east-1")

    store_kwargs: dict[str, Any] = {
        "index": index_name,
        "namespace": ns or "default",
        "metric": "cosine",
        "spec": {
            "serverless": {"region": pinecone_region, "cloud": pinecone_cloud}
        },
    }

    env_dims = os.getenv("OPENAI_EMBEDDING_DIMENSIONS")
    if env_dims:
        store_kwargs["dimension"] = int(env_dims)
    else:
        store_kwargs["dimension"] = 1536

    return PineconeDocumentStore(**store_kwargs)
