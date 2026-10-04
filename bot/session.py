"""Краткосрочная история диалога в памяти процесса."""

from __future__ import annotations

from collections import defaultdict

from haystack.dataclasses import ChatMessage

from bot.context import MAX_SESSION_MESSAGES

_chat_sessions: dict[int, list[ChatMessage]] = defaultdict(list)


def get_session(user_id: int) -> list[ChatMessage]:
    return list(_chat_sessions[user_id])


def append_session(user_id: int, user_text: str, assistant_text: str) -> None:
    session = _chat_sessions[user_id]
    session.append(ChatMessage.from_user(user_text))
    session.append(ChatMessage.from_assistant(assistant_text))
    if len(session) > MAX_SESSION_MESSAGES:
        _chat_sessions[user_id] = session[-MAX_SESSION_MESSAGES:]


def reset_session(user_id: int) -> None:
    _chat_sessions.pop(user_id, None)
