"""Запись сообщений в долговременную память Pinecone."""

from __future__ import annotations

import logging

from telebot import types

from bot.context import MEMORY_KINDS_TO_STORE, memory
from bot.messaging import base_user_metadata

logger = logging.getLogger(__name__)


def save_to_memory(message: types.Message, text: str, kind: str) -> None:
    if kind not in MEMORY_KINDS_TO_STORE:
        return

    cleaned = text.strip()
    if not cleaned:
        return

    meta = base_user_metadata(message)
    meta["kind"] = kind
    result = memory.remember_message(
        cleaned,
        metadata=meta,
        user_id=message.from_user.id,
        on_duplicate="update",
    )
    logger.info(
        "memory store user_id=%s kind=%s action=%s similarity=%s memory_id=%s",
        message.from_user.id,
        kind,
        result.action,
        result.similarity,
        result.memory_id,
    )
