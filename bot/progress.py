"""Полоса прогресса в одном сообщении Telegram (редактирование текста)."""

from __future__ import annotations

import logging

import telebot

logger = logging.getLogger(__name__)


def render_progress_bar(ratio: float, label: str) -> str:
    ratio = max(0.0, min(1.0, ratio))
    width = 10
    filled = int(ratio * width)
    bar = "█" * filled + "░" * (width - filled)
    pct = int(ratio * 100)
    return f"{label}\n\n[{bar}] {pct}%"


def edit_progress(
    bot: telebot.TeleBot,
    chat_id: int,
    message_id: int,
    *,
    ratio: float,
    label: str,
    last_text: list[str],
) -> None:
    text = render_progress_bar(ratio, label)
    if text == last_text[0]:
        return
    try:
        bot.edit_message_text(text, chat_id, message_id)
        last_text[0] = text
    except telebot.apihelper.ApiTelegramException as exc:
        if "message is not modified" not in str(exc).lower():
            logger.debug("Не удалось обновить прогресс: %s", exc)
