"""Преобразование текстового prompt в ChatMessage для OpenAIChatGenerator."""

from __future__ import annotations

from haystack import component
from haystack.dataclasses import ChatMessage


@component
class PromptToChatMessages:
    @component.output_types(messages=list[ChatMessage])
    def run(self, prompt: str) -> dict[str, list[ChatMessage]]:
        return {"messages": [ChatMessage.from_user(prompt.strip())]}
