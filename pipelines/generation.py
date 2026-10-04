"""Пайплайн RAG: эмбеддинг запроса → retriever → prompt → LLM."""

from __future__ import annotations

import os
from typing import Any

from haystack import Pipeline
from haystack.components.builders import PromptBuilder
from haystack.components.embedders import OpenAITextEmbedder
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack_integrations.components.retrievers.pinecone import PineconeEmbeddingRetriever
from haystack_integrations.document_stores.pinecone import PineconeDocumentStore

from components.prompt_to_messages import PromptToChatMessages
from components.retrieval_filters import document_chunks_filter
from config import load_project_env

RAG_PROMPT_TEMPLATE = """\
Используй фрагменты загруженных документов пользователя и ответь на вопрос по-русски.
Если в документах нет ответа — честно скажи об этом, не выдумывай.

Документы:
{% for doc in documents %}
---
Файл: {{ doc.meta.file_name | default('неизвестно') }}
{% if doc.meta.page_number is defined %}Страница: {{ doc.meta.page_number }}
{% endif %}Фрагмент: {{ doc.content }}
{% endfor %}
---
Вопрос: {{ query }}
Ответ:"""


class GenerationPipeline:
    def __init__(
        self,
        document_store: PineconeDocumentStore,
        *,
        embedding_model: str | None = None,
        chat_model: str | None = None,
        top_k: int = 5,
    ) -> None:
        load_project_env()
        self._top_k = top_k
        self._chat_model = chat_model or os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        embed_model = embedding_model or os.getenv(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
        )

        embedder_kwargs: dict[str, Any] = {"model": embed_model}
        if os.getenv("OPENAI_EMBEDDING_DIMENSIONS"):
            embedder_kwargs["dimensions"] = int(os.getenv("OPENAI_EMBEDDING_DIMENSIONS", "1536"))

        self._text_embedder = OpenAITextEmbedder(**embedder_kwargs)
        self._retriever = PineconeEmbeddingRetriever(
            document_store=document_store,
            top_k=top_k,
        )

        self._pipeline = Pipeline()
        self._pipeline.add_component("text_embedder", self._text_embedder)
        self._pipeline.add_component("retriever", self._retriever)
        self._pipeline.add_component("prompt_builder", PromptBuilder(template=RAG_PROMPT_TEMPLATE))
        self._pipeline.add_component("prompt_to_messages", PromptToChatMessages())
        self._pipeline.add_component(
            "llm",
            OpenAIChatGenerator(model=self._chat_model),
        )

        self._pipeline.connect("text_embedder.embedding", "retriever.query_embedding")
        self._pipeline.connect("retriever.documents", "prompt_builder.documents")
        self._pipeline.connect("prompt_builder.prompt", "prompt_to_messages.prompt")
        self._pipeline.connect("prompt_to_messages.messages", "llm.messages")

    def run(self, *, user_id: int, query: str, top_k: int | None = None) -> dict[str, Any]:
        k = top_k if top_k is not None else self._top_k
        filters = document_chunks_filter(user_id)
        return self._pipeline.run(
            {
                "text_embedder": {"text": query},
                "prompt_builder": {"query": query},
                "retriever": {"filters": filters, "top_k": k},
            }
        )

    def retrieve_documents(
        self,
        *,
        user_id: int,
        query: str,
        top_k: int | None = None,
        file_name: str | None = None,
    ) -> list:
        k = top_k if top_k is not None else self._top_k
        embedding = self._text_embedder.run(text=query)["embedding"]
        result = self._retriever.run(
            query_embedding=embedding,
            filters=document_chunks_filter(user_id, file_name=file_name),
            top_k=k,
        )
        return list(result.get("documents") or [])

    def generate_answer(self, *, user_id: int, query: str, top_k: int | None = None) -> str:
        result = self.run(user_id=user_id, query=query, top_k=top_k)
        replies = result.get("llm", {}).get("replies") or []
        if not replies:
            return ""
        first = replies[0]
        if isinstance(first, str):
            return first.strip()
        return (first.text or "").strip()
