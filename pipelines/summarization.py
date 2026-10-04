"""Одно предложение-резюме после индексации файла."""

from __future__ import annotations

import os

from haystack import Document, Pipeline
from haystack.components.builders import PromptBuilder
from haystack.components.generators.chat import OpenAIChatGenerator

from components.prompt_to_messages import PromptToChatMessages
from config import load_project_env

SUMMARY_TEMPLATE = """\
Ниже фрагменты одного документа пользователя.
Напиши ровно одно законченное предложение по-русски: о чём этот файл (суть, тема).
Без списков, без кавычек вокруг всего ответа, без «Этот файл…» в начале — сразу по существу.

Фрагменты:
{% for doc in documents %}
- {{ doc.content }}
{% endfor %}
"""


class SummarizationPipeline:
    def __init__(self, *, chat_model: str | None = None) -> None:
        load_project_env()
        model = chat_model or os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

        self._pipeline = Pipeline()
        self._pipeline.add_component("prompt_builder", PromptBuilder(template=SUMMARY_TEMPLATE))
        self._pipeline.add_component("prompt_to_messages", PromptToChatMessages())
        self._pipeline.add_component("llm", OpenAIChatGenerator(model=model))
        self._pipeline.connect("prompt_builder.prompt", "prompt_to_messages.prompt")
        self._pipeline.connect("prompt_to_messages.messages", "llm.messages")

    def summarize_chunks(self, documents: list[Document], *, max_chunks: int = 5) -> str:
        if not documents:
            return "Не удалось выделить содержание файла."

        sample: list[Document] = []
        for doc in documents[:max_chunks]:
            content = (doc.content or "")[:1200]
            sample.append(Document(content=content, meta=doc.meta))

        result = self._pipeline.run({"prompt_builder": {"documents": sample}})
        replies = result.get("llm", {}).get("replies") or []
        if not replies:
            return "Файл сохранён, краткое резюме сформировать не удалось."
        first = replies[0]
        text = first if isinstance(first, str) else (first.text or "")
        return text.strip().split("\n")[0].strip() or text.strip()
