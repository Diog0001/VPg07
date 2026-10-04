"""Отправка сообщений и вспомогательные форматеры Telegram."""

from __future__ import annotations

import logging
import re
from typing import Any

import telebot
from telebot import types

logger = logging.getLogger(__name__)

_DOG_CEO_URL_RE = re.compile(r"https://images\.dog\.ceo/[^\s<]+")


def display_user_name(user: types.User) -> str:
    parts = [part for part in (user.first_name, user.last_name) if part]
    if parts:
        return " ".join(parts)
    if user.username:
        return f"@{user.username}"
    return f"user_{user.id}"


def base_user_metadata(message: types.Message) -> dict[str, Any]:
    user = message.from_user
    if user is None:
        raise ValueError("Сообщение без from_user нельзя сохранить в память.")

    meta: dict[str, Any] = {
        "user_id": str(user.id),
        "chat_id": str(message.chat.id),
        "display_name": display_user_name(user),
    }
    if user.username:
        meta["username"] = user.username
    if user.first_name:
        meta["first_name"] = user.first_name
    if user.last_name:
        meta["last_name"] = user.last_name
    return meta


def send_long_message(bot: telebot.TeleBot, chat_id: int, text: str) -> None:
    limit = 4000
    if len(text) <= limit:
        bot.send_message(chat_id, text)
        return
    for i in range(0, len(text), limit):
        bot.send_message(chat_id, text[i : i + limit])


def maybe_send_dog_photo(bot: telebot.TeleBot, chat_id: int, reply_text: str) -> None:
    match = _DOG_CEO_URL_RE.search(reply_text)
    if not match:
        return
    url = match.group(0).rstrip(").,")
    try:
        bot.send_photo(chat_id, url, caption="Случайная собака с dog.ceo")
    except Exception:
        logger.exception("Не удалось отправить фото dog.ceo в chat_id=%s", chat_id)
