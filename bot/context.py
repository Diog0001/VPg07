"""Общие зависимости бота (singletons на процесс)."""

from __future__ import annotations

import os

from components.memory_service import HaystackUserMemory
from config import load_project_env
from services.assistant import PersonalAssistant
from services.ingestion_service import IngestionService

load_project_env()

MEMORY_NAMESPACE = os.getenv("PINECONE_MEMORY_NAMESPACE", "telegram-users")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
MEMORY_RETRIEVAL_TOP_K = int(os.getenv("MEMORY_RETRIEVAL_TOP_K", "6"))
DOCUMENT_RETRIEVAL_TOP_K = int(os.getenv("DOCUMENT_RETRIEVAL_TOP_K", "5"))
MAX_SESSION_MESSAGES = int(os.getenv("CHAT_SESSION_MAX_MESSAGES", "20"))

MEMORY_KINDS_TO_STORE = frozenset({"user_message", "assistant_message", "profile"})
MEMORY_KINDS_FOR_CONTEXT = frozenset({"user_message", "assistant_message", "profile"})

memory = HaystackUserMemory(namespace=MEMORY_NAMESPACE)
assistant = PersonalAssistant(
    memory,
    chat_model=OPENAI_CHAT_MODEL,
    document_top_k=DOCUMENT_RETRIEVAL_TOP_K,
)
ingestion_service = IngestionService(memory)
